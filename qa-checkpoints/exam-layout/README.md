# Exam folders and retired-content migration (draft)

Owner requirement: keep only current questions in the new active packs, and give each exam and question a clear editing location. This checkpoint is not a release.

Proposed layout:

    assets/exams/test-01/
      questions/Q003/question.json
      questions/Q003/image.svg
      questions/Q003/practice.m4a
      questions/Q003/formal-passage.m4a
      groups/<group-id>/group.json
      groups/<group-id>/passage.m4a
      common/...

A multipart passage, talk, figure, or directions can be referenced from several questions; keep a single copy at its exam/group location and make the reference visible in the source JSON. Unique materials live with their question even when the runtime models them as a one-question group. Compile editable sources into the runtime `data/test-NN.js` files rather than making a browser load hundreds of files at startup.

The current question pack can stop shipping legacyQuestions. This does not delete the student's stored session, answers, or score. Apply `retired-results.patch` on the Test 01 candidate app, copy `test_retired_history.cjs` to `tools/`, and run `node --test tools/test_retired_history.cjs`. The result card shows saved answer and original answer key (if stored) without grading against a replacement. To restore any retired content for maintenance, use prior Git revisions. Old in-progress sessions containing retired IDs must not be silently mapped/regraded.

Test 01 Q003 audio experiment: range 40.596–59.868 seconds formal and 37.788–57.348 seconds practice. Decoded at native mono 24 kHz, took exact integer sample windows, wrote WAV and lossless ALAC/M4A, then decoded and compared PCM SHA-256. Both formats reproduced their corresponding sample windows exactly; direct MP3 frame copy did not. Test the chosen format and byte-range seeks in actual target browsers. Keep every formal timeline frame's order, duration, group, cue role and answer window unchanged; only point relocated clips to the equivalent range. Formal duration remains 2,700 seconds. Related groups, old audio editions still needed by resume, and asset size limits require complete validation before migration. Do not delete any still-referenced asset.

Merge nothing to production until all three exams and the content migration pass. Exclude this checkpoint directory from the release.
