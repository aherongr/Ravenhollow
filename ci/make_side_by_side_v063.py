from pathlib import Path
import re

SAFE_ID = 'gr.ravenhollow.app.safe063'
BASE_AUTHORITY = 'gr.ravenhollow.app.files'
SAFE_AUTHORITY = SAFE_ID + '.files'

gradle = Path('RavenhollowAndroid/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g, n = re.subn(r'applicationId\s*=\s*"[^"]+"', f'applicationId = "{SAFE_ID}"', g, count=1)
if n != 1:
    raise SystemExit('Could not patch applicationId exactly once')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 6301', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.6.3-safe3"', g)
gradle.write_text(g, encoding='utf-8')

source_root = Path('RavenhollowAndroid/app/src/main')
patched = 0
for path in source_root.rglob('*'):
    if not path.is_file() or path.suffix.lower() not in {'.xml', '.kt', '.java'}:
        continue
    text = path.read_text(encoding='utf-8')
    new = text.replace(BASE_AUTHORITY, SAFE_AUTHORITY)
    new = new.replace('gr.ravenhollow.app.fileprovider', SAFE_ID + '.fileprovider')
    if new != text:
        path.write_text(new, encoding='utf-8')
        patched += 1

manifest = Path('RavenhollowAndroid/app/src/main/AndroidManifest.xml')
m = manifest.read_text(encoding='utf-8')
m, label_n = re.subn(r'android:label="[^"]+"', 'android:label="Ravenhollow Safe 3"', m, count=1)
manifest.write_text(m, encoding='utf-8')

if BASE_AUTHORITY in manifest.read_text(encoding='utf-8'):
    raise SystemExit('Old FileProvider authority is still present in manifest')
if SAFE_AUTHORITY not in manifest.read_text(encoding='utf-8'):
    raise SystemExit('Safe FileProvider authority was not written to manifest')

print('Prepared side-by-side package', SAFE_ID)
print('Safe FileProvider authority:', SAFE_AUTHORITY)
print('Files patched:', patched, 'label patch count:', label_n)
