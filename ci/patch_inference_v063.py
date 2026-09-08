from pathlib import Path
import re

root = Path('RavenhollowAndroid/app/src/main/java/gr/ravenhollow/app')

# Apply on top of the v0.6.2 patch. The selected local text model is Qwen3-based,
# so explicitly disable its long thinking path and keep mobile generations bounded.
prompt = root / 'PromptAssembler.kt'
s = prompt.read_text(encoding='utf-8')
s = s.replace(
    'Never mention these instructions or the existence of a prompt/database in the story.',
    'Never mention these instructions or the existence of a prompt/database in the story.\n        Answer directly. Do not emit a <think> block or hidden-reasoning transcript.'
)
s = s.replace(
    'Continue the story directly from the current endpoint. Do not preface, summarize instructions,\n            explain your process, or restart an already completed event.',
    'Continue the story directly from the current endpoint. Do not preface, summarize instructions,\n            explain your process, or restart an already completed event.\n\n            /no_think'
)
prompt.write_text(s, encoding='utf-8')

local = root / 'LocalEngines.kt'
s = local.read_text(encoding='utf-8')
s = s.replace(
    'val safeMaxOutputTokens = prefs.maxOutputTokens.coerceIn(64, (prefs.contextTokens / 4).coerceAtLeast(64))\n                val inputTokenBudget = (prefs.contextTokens - safeMaxOutputTokens - 500).coerceAtLeast(700)',
    'val mobileOutputCap = minOf(160, (prefs.contextTokens / 4).coerceAtLeast(32))\n                val safeMaxOutputTokens = prefs.maxOutputTokens.coerceIn(32, mobileOutputCap)\n                val inputTokenBudget = (prefs.contextTokens - safeMaxOutputTokens - 500).coerceAtLeast(700)'
)
s = s.replace(
    'inputBudgetChars = inputTokenBudget * 2,',
    'inputBudgetChars = minOf(inputTokenBudget * 2, 3200),'
)
local.write_text(s, encoding='utf-8')

repo = root / 'RavenRepository.kt'
s = repo.read_text(encoding='utf-8')
old = '''    suspend fun selfTestTextEngine(): String {
        val recent = db.listTurns(8)
        return textEngine.generate(
            prompt = "Return exactly one short sentence confirming that the Ravenhollow local model is operational.",
            context = recent,
            canon = db.listCanon().take(20),
            relevantMemories = emptyList(),
        )
    }'''
new = '''    suspend fun selfTestTextEngine(): String {
        // A diagnostic must test the model/runtime, not the size of the story database.
        // Keep it independent of imported continuity and disable Qwen3 thinking mode.
        return textEngine.generate(
            prompt = "Reply with exactly: OK\\n/no_think",
            context = emptyList(),
            canon = emptyList(),
            relevantMemories = emptyList(),
        )
    }'''
if old not in s:
    raise SystemExit('Expected selfTestTextEngine block not found')
s = s.replace(old, new)
repo.write_text(s, encoding='utf-8')

gradle = Path('RavenhollowAndroid/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 63', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.6.3"', g)
gradle.write_text(g, encoding='utf-8')

verifier = Path('RavenhollowAndroid/verify_project.sh')
v = verifier.read_text(encoding='utf-8').replace('0.6.2', '0.6.3')
verifier.write_text(v, encoding='utf-8')

print('Patched v0.6.3: Qwen3 /no_think, 160-token hard output cap, 3200-char prompt cap, continuity-free self-test')
