# SHIFT Test 01–03 media migration proof

These tools generalize the Test 01-only checkpoint without modifying it. They build an isolated overlay, not a deployable site. Use a current, consistent candidate checkout; migration does not reconcile concurrent edits or certify question answers.

```sh
for n in 01 02 03; do
  python3 migrate_exam.py --site ../../shift-qa --exam test-$n --out proof-$n
  python3 check_proof.py --site ../../shift-qa --exam test-$n --out proof-$n
  python3 ../../shift-qa/tools/validate_exam.py --site proof-$n test-$n.json
done
```

Paths are relative to where the command runs; adjust them for the checkout. `--out` must not exist and must be outside the input. Use a fresh location if a prior proof exists. Do not commit or upload rendered proof directories in a code-only checkpoint.

- Per-question audio/pictures live under `audio/exams/test-NN/questions/QNNN/` and `assets/exams/test-NN/questions/QNNN/`. Shared material stays under `groups/<id>/`, and narration under `common/`. The separate media URL roots are necessary for the existing validators and view code. These paths can be assigned to the corresponding authoring question/group manifests.
- Staged WAVs use actual source PCM at its native sample rate/channels, with no resampling. Every WAV is checked against the decoded source slice; the independent proof checker verifies every output, plus fresh FFmpeg comparison for four representative paths.
- These overlays preserve archived question IDs and historical audio fallback. The separate retirement migration is necessary before publication on the active-only bundle. Existing archived records, historical plans, and remaining referenced media are not rewritten or removed.
- The quiz site still needs desktop/mobile playback, resume and seek testing on the full bundle. Watch both GitHub Pages published size and repo growth before deployment. Neither is measured or guaranteed by this overlay.
