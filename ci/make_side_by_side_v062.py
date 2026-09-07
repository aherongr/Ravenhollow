from pathlib import Path
import re

gradle = Path('RavenhollowAndroid/app/build.gradle.kts')
g = gradle.read_text(encoding='utf-8')
g, n = re.subn(r'applicationId\s*=\s*"[^"]+"', 'applicationId = "gr.ravenhollow.app.safe062"', g, count=1)
if n != 1:
    raise SystemExit('Could not patch applicationId exactly once')
g = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 6201', g)
g = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.6.2-safe"', g)
gradle.write_text(g, encoding='utf-8')

manifest = Path('RavenhollowAndroid/app/src/main/AndroidManifest.xml')
m = manifest.read_text(encoding='utf-8')
# Give the parallel test build an unmistakable launcher name.
m, label_n = re.subn(r'android:label="[^"]+"', 'android:label="Ravenhollow Safe"', m, count=1)
# Avoid authority collision if an older source used a literal FileProvider authority.
m = m.replace('gr.ravenhollow.app.fileprovider', 'gr.ravenhollow.app.safe062.fileprovider')
manifest.write_text(m, encoding='utf-8')

print('Prepared side-by-side package gr.ravenhollow.app.safe062; label patch count:', label_n)
