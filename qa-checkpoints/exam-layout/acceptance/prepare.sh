#!/usr/bin/env bash
# Run from the common parent; replace overlay paths with your finalized inputs.
set -euo pipefail
root="${1:?Supply a new output parent directory}"
retired_patch="$(pwd)/shift-layout-stage/retired-results.patch"
mkdir "$root" "$root/staged"
for n in index.html 使用說明.html 語音試聽.html assets data audio; do
  cp -a "shift-qa/$n" "$root/staged/"
done
for overlay in shift-media-migration/proof shift-media-migration/all-exams/proof-{02,03}; do
  for type in data audio assets; do
    cp -a "$overlay/$type/." "$root/staged/$type/"
  done
done
python3 shift-layout-stage/layout.py split --site "$root/staged" --source "$root/source" --omit-legacy-questions
python3 shift-layout-stage/layout.py build --source "$root/source" --site "$root/rebuilt"
python3 shift-qa/tools/validate_exam.py --site "$root/rebuilt"
# Assemble shell separately. Do not replace generated audio/assets directories
# with all old assets. Keep base ancillary runtime resources under their paths.
cp -a "$root/staged"/{index.html,使用說明.html,語音試聽.html} "$root/rebuilt/"
cp -a "$root/staged/data/catalog.js" "$root/rebuilt/data/"
for x in app.js favicon.svg style.css release-label.js; do cp -a "$root/staged/assets/$x" "$root/rebuilt/assets/"; done
# Include ancillary CSS/page assets and voice demo files after their references
# are audited; minimal shell above is for quiz smoke only.
(cd "$root/rebuilt" && patch --batch -p1 < "$retired_patch")
