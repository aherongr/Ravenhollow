from pathlib import Path
import re

root = Path('RavenhollowAndroid/app/src/main/java/gr/ravenhollow/app')

# Keep the strict Aheron-control rules from v0.6.5, but return to the output
# size that was proven to complete on the user's phone. Long scenes are
# intentionally produced in short chunks and can be continued.
local = root / 'LocalEngines.kt'
s = local.read_text(encoding='utf-8')
s = s.replace(
    'val mobileOutputCap = minOf(768, (prefs.contextTokens / 4).coerceAtLeast(64))',
    'val mobileOutputCap = minOf(160, (prefs.contextTokens / 4).coerceAtLeast(64))',
    1,
)
local.write_text(s, encoding='utf-8')

prompt = root / 'PromptAssembler.kt'
s = prompt.read_text(encoding='utf-8')
needle = '''        If another character asks Aheron a question, offers him a choice, or otherwise requires his response, end
        the generation immediately after that character's question/choice and wait for the Director. Never answer
        on Aheron's behalf. Never mention these instructions or the existence of a prompt/database in the story.'''
replacement = '''        If another character asks Aheron a question, offers him a choice, or otherwise requires his response, end
        the generation immediately after that character's question/choice and wait for the Director. Never answer
        on Aheron's behalf. Keep each mobile turn compact: usually 60-120 words. Finish at a natural stopping point
        before the token limit whenever possible. Write narration and dialogue in Greek unless the Director clearly
        requests another language. Never mention these instructions or the existence of a prompt/database in the story.'''
if needle not in s:
    raise SystemExit('Expected v0.6.5 system control block not found')
s = s.replace(needle, replacement, 1)

needle2 = '''            If the Director instruction is simply "Continue", continue exactly from the last unfinished STORY text
            without recap or time jump. Complete an abruptly cut sentence if needed, but still never control Aheron.'''
replacement2 = '''            If the Director instruction is simply "Continue", continue exactly from the last unfinished STORY text
            without recap or time jump. Complete an abruptly cut sentence if needed, but still never control Aheron.

            MOBILE TURN LENGTH: Prefer a compact 60-120 word response and stop naturally. If the Director asks a
            character to ask Aheron something, give only the necessary staging plus that question, then STOP.'''
if needle2 not in s:
    raise SystemExit('Expected v0.6.5 continue block not found')
s = s.replace(needle2, replacement2, 1)
prompt.write_text(s, encoding='utf-8')

main = root / 'MainActivity.kt'
s = main.read_text(encoding='utf-8')
s = s.replace('Recommended Ravenhollow: 4096 context · 512–768 output · 6 threads',
              'Recommended Ravenhollow: 4096 context · reply setting 160 · 6 threads')
s = s.replace('Recommended for Ravenhollow: ~3B Q4_K_M · context 4096',
              'Recommended for Ravenhollow: ~3B Q4_K_M · context 4096 · fast 160-token turns')
main.write_text(s, encoding='utf-8')

# Version bump.
gradle = Path('RavenhollowAndroid/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 66', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.6.6"', g)
gradle.write_text(g, encoding='utf-8')

verifier = Path('RavenhollowAndroid/verify_project.sh')
v = verifier.read_text(encoding='utf-8').replace('0.6.5', '0.6.6')
verifier.write_text(v, encoding='utf-8')

print('Patched v0.6.6: proven 160-token cap, compact Greek turns, strict Aheron control')
