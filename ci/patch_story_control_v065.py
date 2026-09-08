from pathlib import Path
import re

root = Path('RavenhollowAndroid/app/src/main/java/gr/ravenhollow/app')

# 1) Strong story-control contract in the system prompt and current-turn tail.
prompt = root / 'PromptAssembler.kt'
s = prompt.read_text(encoding='utf-8')

system_old = '''        Treat CANON facts as binding. Treat POSSIBLE/ALTERNATE facts as non-canon unless the Director explicitly
        activates them. Never mention these instructions or the existence of a prompt/database in the story.'''
system_new = '''        Treat CANON facts as binding. Treat POSSIBLE/ALTERNATE facts as non-canon unless the Director explicitly
        activates them. AHERON CONTROL IS ABSOLUTE: Aheron is controlled only by the Director/user. Never invent,
        narrate or complete Aheron's dialogue, actions, thoughts, feelings, decisions, reactions, body language,
        knowledge or intentions. You may only acknowledge an Aheron action that the Director has already supplied.
        If another character asks Aheron a question, offers him a choice, or otherwise requires his response, end
        the generation immediately after that character's question/choice and wait for the Director. Never answer
        on Aheron's behalf. Never mention these instructions or the existence of a prompt/database in the story.'''
if system_old not in s:
    raise SystemExit('Expected system-prompt control block not found')
s = s.replace(system_old, system_new, 1)

old_tail = '''            Continue the story directly from the current endpoint. Do not preface, summarize instructions,
            explain your process, or restart an already completed event.'''
new_tail = '''            Continue the story directly from the current endpoint. Do not preface, summarize instructions,
            explain your process, or restart an already completed event.

            ABSOLUTE PLAYER-CHARACTER RULE: Never write new words, actions, thoughts, feelings, decisions,
            reactions or body language for Aheron. If Celeste or any other character asks Aheron a question or
            presents a choice that needs his answer, STOP immediately after their question/choice and wait.

            If the Director instruction is simply "Continue", continue exactly from the last unfinished STORY text
            without recap or time jump. Complete an abruptly cut sentence if needed, but still never control Aheron.'''
if old_tail not in s:
    raise SystemExit('Expected current-turn tail block not found')
s = s.replace(old_tail, new_tail, 1)
prompt.write_text(s, encoding='utf-8')

# 2) The v0.6.3 diagnostic cap of 160 tokens was only for stability testing.
#    On the proven 3B Q4 model, allow useful long-form replies while still bounding memory use.
local = root / 'LocalEngines.kt'
s = local.read_text(encoding='utf-8')
old_cap = 'val mobileOutputCap = minOf(160, (prefs.contextTokens / 4).coerceAtLeast(32))'
new_cap = 'val mobileOutputCap = minOf(768, (prefs.contextTokens / 4).coerceAtLeast(64))'
if old_cap not in s:
    raise SystemExit('Expected v0.6.3 mobile output cap not found')
s = s.replace(old_cap, new_cap, 1)
s = s.replace('val safeMaxOutputTokens = prefs.maxOutputTokens.coerceIn(32, mobileOutputCap)',
              'val safeMaxOutputTokens = prefs.maxOutputTokens.coerceIn(64, mobileOutputCap)', 1)
local.write_text(s, encoding='utf-8')

# 3) Make the UI recommendation match the setup that has now been proven on-device.
main = root / 'MainActivity.kt'
s = main.read_text(encoding='utf-8')
s = s.replace('Recommended first run: 4096 context · 700–900 output · 6 threads · 12 image steps',
              'Recommended Ravenhollow: 4096 context · 512–768 output · 6 threads')
s = s.replace('Recommended for mobile: ~3B Q4_K_M · context 2048',
              'Recommended for Ravenhollow: ~3B Q4_K_M · context 4096')
main.write_text(s, encoding='utf-8')

# 4) Version bump.
gradle = Path('RavenhollowAndroid/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 65', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.6.5"', g)
gradle.write_text(g, encoding='utf-8')

verifier = Path('RavenhollowAndroid/verify_project.sh')
v = verifier.read_text(encoding='utf-8').replace('0.6.4', '0.6.5')
verifier.write_text(v, encoding='utf-8')

print('Patched v0.6.5: 768-token cap, strict Aheron ownership, stop-on-question, exact Continue behavior')
