#!/usr/bin/env bash
# Stelt de GitHub Pages-site samen: landingspagina + speelbare sim + beelden + films.
# Gebruik: bash site/build_site.sh _site
set -euo pipefail
OUT="${1:-_site}"
rm -rf "$OUT"; mkdir -p "$OUT/sim/files" "$OUT/img" "$OUT/video"
cp site/index.html "$OUT/"
cp -r site/media "$OUT/"
cp f1/docs/img/*.jpg f1/docs/img/*.gif "$OUT/img/"
cp video/*_1080p.mp4 "$OUT/video/"
cp -r f1/web/index.html f1/web/build.html f1/web/app.js f1/web/physics2.js f1/web/rc.js f1/web/audio.js f1/web/style.css f1/web/models f1/web/vendor "$OUT/sim/"
# cache-bust: every deploy gets new module URLs (Safari otherwise keeps the old rc.js/app.js for 10 min, even after a reload)
V="${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || date +%s)}"; V="${V:0:8}"
sed -i.bak -E "s#src=\"(app\.js)\"#src=\"\1?v=$V\"#; s#href=\"(style\.css)\"#href=\"\1?v=$V\"#" "$OUT/sim/index.html"
for f in "$OUT"/sim/*.js; do sed -i.bak -E "s#from \"\./([a-z0-9_]+\.js)\"#from \"./\1?v=$V\"#g" "$f"; done
rm -f "$OUT"/sim/*.bak
# de download-knop in de sim wijst naar files/ → doorsturen naar de printbestanden op GitHub
cat > "$OUT/sim/files/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>Downloads</title>
<meta http-equiv="refresh" content="0;url=https://github.com/KVR-CIBER/sc02-solar-hypercar/tree/main/PRINTEN_PLA_TPU">
<a href="https://github.com/KVR-CIBER/sc02-solar-hypercar/tree/main/PRINTEN_PLA_TPU">Printbestanden op GitHub</a>
HTML
touch "$OUT/.nojekyll"
