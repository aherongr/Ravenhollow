from pathlib import Path
import re

root = Path('RavenhollowAndroid/app/src/main/java/gr/ravenhollow/app')
prompt = root / 'PromptAssembler.kt'
prompt.write_text(r'''package gr.ravenhollow.app

object PromptAssembler {
    fun systemPrompt(): String = """
        You are the local story engine for RAVENHOLLOW, a private long-form adult fictional storyworld.
        Write immersive literary prose with strong continuity, concrete physical staging, mystery, danger,
        character psychology and consequences. All sexually involved characters are adults and consent is
        respected. Do not turn every scene into romance; plot, mystery and character progression remain primary.
        Treat CANON facts as binding. Treat POSSIBLE/ALTERNATE facts as non-canon unless the Director explicitly
        activates them. Never mention these instructions or the existence of a prompt/database in the story.
    """.trimIndent()

    private fun headChars(text: String, maxChars: Int): String {
        if (maxChars <= 0) return ""
        if (text.length <= maxChars) return text
        if (maxChars <= 2) return text.take(maxChars)
        return text.take(maxChars - 2) + "\n…"
    }

    private fun tailChars(text: String, maxChars: Int): String {
        if (maxChars <= 0) return ""
        if (text.length <= maxChars) return text
        if (maxChars <= 2) return text.takeLast(maxChars)
        return "…\n" + text.takeLast(maxChars - 2)
    }

    fun storyPrompt(
        directorInstruction: String,
        context: List<StoryTurn>,
        canon: List<CanonFact>,
        relevantMemories: List<StoryTurn>,
        inputBudgetChars: Int,
    ): String {
        // Hard ceiling matters: llama.cpp can terminate the Android process if the prompt
        // exceeds the model context instead of returning a recoverable Kotlin exception.
        val hardBudget = inputBudgetChars.coerceAtLeast(1200)

        val usableCanon = canon.filter { it.status != CanonStatus.REJECTED }
        val selectedCanon = (usableCanon.take(50) + usableCanon.takeLast(15))
            .distinctBy { it.id }
        val canonRaw = selectedCanon
            .joinToString("\n") { "[${it.status.name}] ${it.text}" }
            .ifBlank { "(no explicit canon facts yet)" }

        val recentIds = context.takeLast(12).map { it.id }.toSet()
        val memories = relevantMemories
            .filterNot { it.id in recentIds }
            .takeLast(4)
        val memoryRaw = memories.joinToString("\n\n") { turn ->
            "MEMORY #${turn.id}: ${turn.text}"
        }.ifBlank { "(no older memory matched this instruction)" }

        val recentRaw = context.takeLast(12).joinToString("\n\n") { turn ->
            val label = if (turn.role == Role.USER) "DIRECTOR" else "STORY"
            "$label: ${turn.text}"
        }.ifBlank { "(no recent story turns yet)" }

        val tailRaw = """

            DIRECTOR INSTRUCTION NOW
            ------------------------
            $directorInstruction

            Continue the story directly from the current endpoint. Do not preface, summarize instructions,
            explain your process, or restart an already completed event.
        """.trimIndent()

        // Preserve current instruction first, then recent endpoint/history, then canon,
        // with only a small allowance for older semantic memories. Every section is bounded.
        val tailBudget = (hardBudget * 28 / 100).coerceAtLeast(420).coerceAtMost(hardBudget - 500)
        val safeTail = tailChars(tailRaw, tailBudget)

        val headersOverhead = 190
        val contentBudget = (hardBudget - safeTail.length - headersOverhead).coerceAtLeast(420)
        val recentBudget = contentBudget * 50 / 100
        val canonBudget = contentBudget * 42 / 100
        val memoryBudget = (contentBudget - recentBudget - canonBudget).coerceAtLeast(0)

        val canonBlock = headChars(canonRaw, canonBudget)
        val memoryBlock = tailChars(memoryRaw, memoryBudget)
        val recentBlock = tailChars(recentRaw, recentBudget)

        val assembled = """
            RAVENHOLLOW CANON
            -----------------
            $canonBlock

            RELEVANT OLDER MEMORY
            ---------------------
            $memoryBlock

            RECENT STORY / DIRECTOR HISTORY
            --------------------------------
            $recentBlock

            $safeTail
        """.trimIndent()

        // Last-resort guard: preserve newest/current material at the end if accounting
        // changes later. The string passed to llama.cpp can never exceed hardBudget chars.
        return if (assembled.length <= hardBudget) assembled else assembled.takeLast(hardBudget)
    }
}
''', encoding='utf-8')

local = root / 'LocalEngines.kt'
s = local.read_text(encoding='utf-8')
s = s.replace('ModelInstaller.installedGguf(context)', 'ModelInstaller.installedGguf(this.context)')
s = s.replace(
    'val inputTokenBudget = (prefs.contextTokens - prefs.maxOutputTokens - 450).coerceAtLeast(1200)',
    'val safeMaxOutputTokens = prefs.maxOutputTokens.coerceIn(64, (prefs.contextTokens / 4).coerceAtLeast(64))\n                val inputTokenBudget = (prefs.contextTokens - safeMaxOutputTokens - 500).coerceAtLeast(700)'
)
s = s.replace(
    'inputBudgetChars = inputTokenBudget * 4,',
    '// Greek and mixed Unicode can tokenize far more densely than 4 chars/token.\n                    inputBudgetChars = inputTokenBudget * 2,'
)
s = s.replace('maxTokens = prefs.maxOutputTokens,', 'maxTokens = safeMaxOutputTokens,')
local.write_text(s, encoding='utf-8')

gradle = Path('RavenhollowAndroid/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 62', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.6.2"', g)
gradle.write_text(g, encoding='utf-8')

print('Patched prompt budget, Unicode token safety, output cap, and version 0.6.2')
