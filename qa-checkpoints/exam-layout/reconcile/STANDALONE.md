# Immutable standalone Part 5 reserve and rotation (offline only)

Existing `question-reserve/index.json` must retain `groups`; an optional
`standalone` array contains unique entries with exactly
`{sourceTest, number, path, status}`. The only path for Test01 Q119 is
`test-01/Q119/manifest.json`, relative to the reserve root. Pending rows do
not change the active pack; adopted rows require an exact recipe.

Under `question-reserve/<test>/QNNN/`, store `question.json` (the complete
reviewed active question), `verification.json` (byte-exact copy of the prior
immutable verified item), and `manifest.json`. Manifest fields:

- `status`: either `saved-pending-replacement` or
  `reserved-inactive-in-work-candidate`; `sourceStillActive` must agree.
- `sourceTest`, `sourceQuestionNumber`, `sourceCommit` (full SHA),
  `sourceQuestionId`, `sourceQuestionRevision`, `sourceAnswer`, and
  `sourceEvidencePath` (numbered verified ledger path).
- `sourceEvidenceGitBlob`, `sourceEvidenceSha256`, `media: []`,
  `format: "standalone-text-only-part-5"`, `notActiveHere: true`.
- `replacementQuestionId` exists only for an adopted row; proposed/draft
  ideas are not recipes.

Adopted recipe `qa-checkpoints/reconstructions/<test>/QNNN.json` has
`kind: "replace-standalone-part-5-by-exact-old-scope"`, `notPublished: true`,
`questionNumber`, `sourceQuestionId`, `newQuestionId`,
`replacementEvidence`, `previousReserve`, and
`questionCanonicalSha256`. The ledger item must be independently marked
verified, embed the exact old question under `originalQuestion`, link
`retiredSourceReference` to reserve verification, and contain a genuinely
new, ungrouped, media-free Part 5 question with revision old plus one.
Canonical digest format stays the same as group replay.

Reject stale or ambiguous packs, malformed paths/statuses, duplicate rows,
orphan recipes, ambiguous history or media references, mismatched original
bytes/blob/digest, and ID collisions (including retained legacy IDs).
Replace the one exact numbered array element only. Group and listening
layouts are untouched; old historical versions remain in their own immutable
pack. This does not establish browser resume or authorize publishing.
