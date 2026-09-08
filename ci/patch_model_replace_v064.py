from pathlib import Path
import re

root = Path('RavenhollowAndroid/app/src/main/java/gr/ravenhollow/app')

# --- ModelInstaller: atomic-ish replacement + original filename metadata ---
model = root / 'ModelInstaller.kt'
s = model.read_text(encoding='utf-8')
if 'import android.provider.OpenableColumns' not in s:
    s = s.replace('import android.net.Uri\n', 'import android.net.Uri\nimport android.provider.OpenableColumns\n')

old_block = '''    suspend fun installGguf(context: Context, uri: Uri): File = withContext(Dispatchers.IO) {
        val models = File(context.filesDir, "models").apply { mkdirs() }
        val temp = File(models, "story_model.gguf.part")
        val target = File(models, "story_model.gguf")
        context.contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "Unable to open selected model" }
            temp.outputStream().use { output -> input.copyTo(output, bufferSize = 1024 * 1024) }
        }
        require(temp.length() > 64L * 1024L * 1024L) { "Selected file is too small to be the intended GGUF model" }
        temp.inputStream().use { input ->
            val magic = ByteArray(4)
            require(input.read(magic) == 4 && magic.contentEquals(byteArrayOf('G'.code.toByte(), 'G'.code.toByte(), 'U'.code.toByte(), 'F'.code.toByte()))) {
                "Selected file is not a valid GGUF file"
            }
        }
        if (target.exists()) target.delete()
        check(temp.renameTo(target)) { "Unable to finalize model file" }
        target
    }'''

new_block = '''    suspend fun installGguf(context: Context, uri: Uri): File = withContext(Dispatchers.IO) {
        val models = File(context.filesDir, "models").apply { mkdirs() }
        val temp = File(models, "story_model.gguf.part")
        val target = File(models, "story_model.gguf")
        val backup = File(models, "story_model.gguf.bak")
        val nameFile = File(models, "story_model.name")

        val sourceName = context.contentResolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME),
            null,
            null,
            null,
        )?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        }?.takeIf { it.isNotBlank() }
            ?: uri.lastPathSegment?.substringAfterLast('/')
            ?: "Imported GGUF"

        if (temp.exists()) temp.delete()
        context.contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "Unable to open selected model" }
            temp.outputStream().use { output -> input.copyTo(output, bufferSize = 1024 * 1024) }
        }
        require(temp.length() > 64L * 1024L * 1024L) { "Selected file is too small to be the intended GGUF model" }
        temp.inputStream().use { input ->
            val magic = ByteArray(4)
            require(input.read(magic) == 4 && magic.contentEquals(byteArrayOf('G'.code.toByte(), 'G'.code.toByte(), 'U'.code.toByte(), 'F'.code.toByte()))) {
                "Selected file is not a valid GGUF file"
            }
        }

        if (backup.exists()) backup.delete()
        if (target.exists()) {
            check(target.renameTo(backup)) { "Unable to stage previous model for replacement" }
        }
        try {
            check(temp.renameTo(target)) { "Unable to finalize model file" }
            // Metadata is informational only; a metadata write failure must never invalidate a good model.
            runCatching { nameFile.writeText(sourceName) }
            if (backup.exists()) backup.delete()
            target
        } catch (t: Throwable) {
            if (temp.exists()) temp.delete()
            if (!target.exists() && backup.exists()) backup.renameTo(target)
            throw t
        }
    }'''

if old_block not in s:
    raise SystemExit('Expected installGguf block not found')
s = s.replace(old_block, new_block)

needle = '    fun installedGguf(context: Context): File = File(File(context.filesDir, "models"), "story_model.gguf")\n'
addition = '''    fun installedGguf(context: Context): File = File(File(context.filesDir, "models"), "story_model.gguf")

    fun installedGgufDisplayName(context: Context): String {
        val models = File(context.filesDir, "models")
        val recorded = File(models, "story_model.name")
            .takeIf { it.isFile }
            ?.let { runCatching { it.readText().trim() }.getOrNull() }
            .orEmpty()
        return recorded.ifBlank { installedGguf(context).name }
    }

    fun installedGgufInfo(context: Context): String {
        val file = installedGguf(context)
        if (!file.exists()) return "No GGUF installed"
        return "${installedGgufDisplayName(context)} · ${humanSize(file.length())}"
    }
'''
if needle not in s:
    raise SystemExit('installedGguf function not found')
s = s.replace(needle, addition, 1)
model.write_text(s, encoding='utf-8')

# --- LlamaTextEngine: detect changed contents even though internal path is constant ---
local = root / 'LocalEngines.kt'
s = local.read_text(encoding='utf-8')
s = s.replace(
    '    private var loadedContextSize: Int = -1\n    private var loadedThreads: Int = -1',
    '    private var loadedContextSize: Int = -1\n    private var loadedThreads: Int = -1\n    private var loadedLength: Long = -1L\n    private var loadedModified: Long = -1L'
)
s = s.replace(
    '            loadedContextSize == desiredContext && loadedThreads == desiredThreads\n        ) return current',
    '            loadedContextSize == desiredContext && loadedThreads == desiredThreads &&\n            loadedLength == file.length() && loadedModified == file.lastModified()\n        ) return current'
)
s = s.replace(
    '            loadedContextSize = desiredContext\n            loadedThreads = desiredThreads',
    '            loadedContextSize = desiredContext\n            loadedThreads = desiredThreads\n            loadedLength = file.length()\n            loadedModified = file.lastModified()'
)
s = s.replace(
    '        loadedModel = null\n        loadedPath = null\n    }',
    '        loadedModel = null\n        loadedPath = null\n        loadedLength = -1L\n        loadedModified = -1L\n    }',
    1,
)
local.write_text(s, encoding='utf-8')

# --- Settings UI: explicitly unload before replacing and show exact active model name/size ---
main = root / 'MainActivity.kt'
s = main.read_text(encoding='utf-8')
old_info = '''    var modelInfo by remember {
        val f = ModelInstaller.installedGguf(context)
        mutableStateOf(if (f.exists()) "Installed · ${ModelInstaller.humanSize(f.length())}" else "No GGUF installed")
    }'''
new_info = '''    var modelInfo by remember {
        mutableStateOf(ModelInstaller.installedGgufInfo(context))
    }'''
if old_info not in s:
    raise SystemExit('Expected modelInfo block not found')
s = s.replace(old_info, new_info)

old_import = '''                runCatching { ModelInstaller.installGguf(context, uri) }
                    .onSuccess { modelInfo = "Installed · ${ModelInstaller.humanSize(it.length())}" }
                    .onFailure { modelInfo = "Import failed: ${it.message ?: "unknown error"}" }'''
new_import = '''                runCatching {
                    withContext(Dispatchers.IO) {
                        // The installed file always has the same internal path. Release first so an
                        // already-loaded 8B model cannot stay alive after a 3B replacement.
                        LocalEngineRegistry.releaseText()
                        ModelInstaller.installGguf(context, uri)
                    }
                }
                    .onSuccess { modelInfo = "Active · ${ModelInstaller.installedGgufInfo(context)}" }
                    .onFailure { modelInfo = "Import failed: ${it.message ?: "unknown error"}" }'''
if old_import not in s:
    raise SystemExit('Expected model import UI block not found')
s = s.replace(old_import, new_import)

s = s.replace('Text("Target: GGUF Q4 7B/8B · context ~8K")', 'Text("Recommended for mobile: ~3B Q4_K_M · context 2048")')
s = s.replace('Text(if (installing) "Importing…" else "Import GGUF")', 'Text(if (installing) "Replacing…" else "Replace / import GGUF")')
main.write_text(s, encoding='utf-8')

# Qwen2.5 does not use Qwen3 thinking mode. Remove the v0.6.3 control token.
prompt = root / 'PromptAssembler.kt'
s = prompt.read_text(encoding='utf-8')
s = s.replace('\n\n            /no_think', '')
s = s.replace('Answer directly. Do not emit a <think> block or hidden-reasoning transcript.', 'Answer directly and keep mobile responses focused.')
prompt.write_text(s, encoding='utf-8')

repo = root / 'RavenRepository.kt'
s = repo.read_text(encoding='utf-8')
s = s.replace('prompt = "Reply with exactly: OK\\n/no_think",', 'prompt = "Reply with exactly: OK",')
s = s.replace('Keep it independent of imported continuity and disable Qwen3 thinking mode.', 'Keep it independent of imported continuity.')
repo.write_text(s, encoding='utf-8')

# Version bump.
gradle = Path('RavenhollowAndroid/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 64', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.6.4"', g)
gradle.write_text(g, encoding='utf-8')

verifier = Path('RavenhollowAndroid/verify_project.sh')
v = verifier.read_text(encoding='utf-8').replace('0.6.3', '0.6.4')
verifier.write_text(v, encoding='utf-8')

print('Patched v0.6.4: explicit model unload/replace, source filename metadata, file fingerprint reload guard, Qwen2.5 prompt mode')
