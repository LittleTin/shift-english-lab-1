# Test01 Q095–100 actual speech retriage: keep both shared groups held

No pack edits, no upload. In each case the exact original asset feeds
both practice and formal passage. All times below are on the full
original source, not relative to trimmed plan start. 
Unprompted Whisper base.en full original with initial silence preserved,
`-ml 1 -sow -ojf`, and overlapping isolated clips decoded locally.

## Q095–097 / t01-g053

- Source: `audio/azure-v1/test-01-33.mp3`, exact plan 0.500–34.364 s,
  SHA-256 `1cb122e5342163330fd1fb1c4c7394f6944de93c4ce1dd43b42b2960fbac75ec`.
- Full source recognizes `Harbour History Museum` (Harbour
  1.140–1.760 s, History 1.760–2.410 s), supporting Harbor in target
  manuscript. Earlier `Haba` is not a reason to keep the name held.
- Full source `Large` 24.600–24.780, `bugs` 24.780–25.030. The crop
  beginning 23.500 s repeated `large bugs` at 0.82×, 1× and 1.20×.
  No same-voice independently verified `bags` or same-phonetic-context
  `bugs` was found in the current 3 test packs. Do not promote the shared
  passage on the written semantic expectation. It is the only retained
  concern; it does not undermine the three keys by itself.
- Q095 regular admission includes the 2:30 guided tour, not the separately
  ticketed photography exhibition; Q096 photo ID is left with attendant,
  no fee; Q097 last photography admission 5, not closing time 6.
  This is not a change to the previous formal question evidence.

## Q098–100 / t01-g054

- Source: `audio/azure-v1/test-01-34.mp3`, exact plan 0.500–36.308 s,
  SHA-256 `98f429b1909be596dcbc815eccf9ebbc80ca4a4d8e98a0ba304c3d22303f2076`.
- Full word-level and targeted 0.82×/1×/1.20× around 3.500–9.000 still
  report `Internet` rather than `intranet` (full ASR source 6.530–8.000).
  This is not capitalization alone and has a different meaning.
- Full source recognizes `Regent requests`, early trials `Agenda`,
  0.82× targeted `Adjunct requests`, and 1×/1.20× targeted `Agent requests` rather than `Urgent` (full ASR source
  24.000–24.340). The same en-NG-EzinneNeural word in Test02 g049
  (`audio/azure-v1/test-02-26.mp3`, SHA
  `4597fce50a6581f52fcc8fb701c5070572754014d2703736162d64d19889d57a`)
  is also not independently recognized by the available model: `Agence`
  12.820–13.260 in the full phrase `only *** safety-related issues`.
  Time-scaled MFCC nearest-neighbor matching did not provide exclusive
  agreement with the disputed g054 word versus unrelated same-speaker
  windows, so it cannot clear `urgent`.
- Full source says `called` at 26.760–27.180, but target 0.82× and 1× unprompted
  context recognizes `call the purchasing team immediately`, as
  scripted, so that form is substantially corroborated. Full-source
  `sent` at 34.570–34.870 positively supports the script over early `send`.
- Rest remains intelligible: reduced delivery charges (Q098), noon
  Wednesday inclusive (Q099), immediate purchasing-team call (Q100,
  independent of the unresolved adjective spelling but question explicitly
  calls it urgent). Keep shared group hold pending an independent reader
  or qualified human listen for the two exact disputed terms.
