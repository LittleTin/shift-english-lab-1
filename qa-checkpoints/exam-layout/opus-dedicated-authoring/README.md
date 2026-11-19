# Provisional active-only SHIFT authoring replay

Do not treat this as a lock, complete difficulty review, or shipping artifact.
This proof covers the exact scoped HQ 600-question candidate; Test01/02
difficulty still needs completion. Do not rerun against your previous raw
fixture. Inputs are the chosen HQ runtime root and corresponding projection
`asset-report.json`.

Use the existing repository layout helper pinned at Git
`e6c2ce542efde185caec8ec118cf8321d7b0a92c`:
```sh
git show e6c2ce542efde185caec8ec118cf8321d7b0a92c:qa-checkpoints/exam-layout/layout.py > layout.py
# SHA256 3ace8f52b697366da34dbceda546c8676b6f400f72afaf275d6601cf08203f84
python replay.py --site /path/to/HQ/site --asset-report /path/to/HQ/asset-report.json --out /path/to/new/scoped-authoring
python build_only.py --source /path/to/new/scoped-authoring/source --out /path/to/empty/compiled
diff -qr /path/to/new/scoped-authoring/rebuilt /path/to/empty/compiled
```

Editable input is each test's `questions/QNNN/question.json` and linked
`groups/<id>/group.json`. Every question has its own `media.json`, including
empty sections, the exact group source when applicable, and relative media
ownership paths. The formal sidecar gives runtime frame index, semantic role,
timeline time, source start/end seconds and 48 kHz sample indexes from the
exact playback bounds. The canonical runtime plan is part of `exam.json`;
do not edit a derived role sidecar in place of its canonical timing.
`source/manifest.json` records one physical file per runtime media object;
shared use is by reference only. Dedicated objects are under the precise
question, single-group shared objects under that group, wider reuse under
the relevant exam common or cross-exam common. A hash-shared container can
have distinct bounded roles; it is not copied per question.

For example Test01 Q053 has its formal spoken stem under its own question
(frame 156, samples 0–302400), the G039-r2 shared illustration and passage in
the group (frame 155, samples 0–2304600), and the cue in exam common (frame
154, samples 220230–408526). `common/standalone` contains the 14 Opus sample
objects and the formal intro illustration, not duplicate pack content.

The standalone reverse build emits only authoritative compiled packs and
media. UI/catalog and other runtime shell files come from the separately
reviewed higher-level release composer. This prefix does not carry
archive data, WAV/MP3, intermediate masters, old snapshot, or user state.
