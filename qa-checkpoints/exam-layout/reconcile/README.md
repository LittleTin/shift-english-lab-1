# Stage-side verified-evidence reconciliation gate

Files: `reconcile.py` and `test_reconcile.py`. This is an isolated release
tool prototype, not a ready site, no branch mutation. Run from the workspace
parent, using a consistent snapshot of the three JSON packs, assets and
evidence at an explicitly pinned checkpoint. Do not use mutable FETCH_HEAD as
provenance or turn missing approvals into passes.

```sh
D=shift-media-migration/reconcile
python3 "$D/reconcile.py" --site /path/to/isolated-candidate \
  --ledger /path/to/qa-checkpoints/verified-items --report /new/reconciliation.json
```

Exit 2 means incomplete/held/conflicting/unmatched; exit 1 invalid input or
failed tooling. A negative run creates no candidate output. `releaseReady`
is always false. `evidenceComplete` only means this mechanical gate has
checked all 600 approved input records and there are no blockers. It does not
assert English/Chinese correctness, native-speech rendering, old-session
compatibility, browser acceptance, site capacity, or publication.

- The only positive input status is `verified-item-not-published`, with
  actual item body, scope, source/key and positive check fields. No status
  inferral from draft folders. One file per numbered current item; held items
  or missing records are listed, never assembled. Distinguish same-number
  stable or revisioned IDs from historical copies; changed key cannot reuse
  the baseline ID, and changed ID needs the matching prior ID and later
  revision. Explicitly staging from the consistent prior/site version remains
  necessary; this tool does not infer which prior user histories are runnable.
- Shared group records must be identical across approved members. A conflict
  returns full SHA-256 values and affected numbers. Prefer updating reviewed
  ledger files to the same exact group after actual review. An optional
  `--decisions` JSON object lets the operator supply an explicit, auditable
  decision keyed by `test-NN/group-id`: fields `canonicalSha256`,
  exact `seenSha256` list, exact `reverifiedQuestionNumbers` list for members
  whose group SHA differs, and nonempty `reason`. Only use this after real
  re-verification and version selection. Invalid, extra or unused decisions
  fail closed. A decision cannot waive source media/Q hashes.
- Each referenced picture must match the item's documented SHA-256. Audio
  rows require correct per-item source SHA and the actual formal passage,
  practice interval, and (Parts 3–4) separately spoken question interval.
  Supports matched `start/end` or `from/to` schemas; legacy modeless rows must
  uniquely match one actual role/range.
- Once complete, `--out` plus `--validator shift-qa/tools/validate_exam.py`
  and `--layout-script shift-layout-stage/layout.py` can create a fresh output
  directory containing assembled current JSON+JS and split per-item
  `authoring/` records; archives are not counted or materialized in the active
  pack. If a same-number active identity changed, only active formal references
  are updated. Existing older audio plans remain unchanged. Do not copy both
  authoring and compiled asset trees into Pages by mistake. This is not the
  completed retired-session compatibility overlay.
- For complete records only, add `--overlays /path/to/parent` containing
  separate `test-01`, `test-02`, `test-03` migration overlays and reports.
  Audit rejects rewritten question, group text, plan order/timing, and fallback
  plan/asset drift. It compares existing source audio hash and actual decoded
  PCM slices with each relocated WAV, requiring original sample boundaries,
  sample/channels/width checks and each report hash. Figure copies must be
  byte-identical. The audit runs against canonical evidence-built packs,
  not against self-reported migration manifests alone. It cannot certify
  audible quality or browser results. `--out` writes the reconciled
  **pre-migration** staging draft; overlay auditing doesn't substitute a new
  publish workflow.

## Checked on immutable fixture e04107bb42f77980db0114749c0394930a1189fc

Create fixture directories first: extract that exact commit's
`qa-checkpoints/verified-items` into `evidence/`; copy a matching candidate
`data/`, `assets/`, `audio/` under `inputs/` and include the actual
Test02 t02-r-p7-05/11/12 figures from the graphical draft. These three files
are not in the baseline copy; their SHA-256s were verified against the
recorded approvals. Keep fixture trees, reports and generated assets local.

Gate on the pinned fixture: Test01 153 accepted, 43 missing, Q135–138
incompatible shared group snapshots (`t01-r-p6-02`); Test02 100 reading
accepted, 100 listening missing; Test03 75 accepted, 125 missing.
The shared text disagreement is a meaningful Traditional Chinese divergence:
Q135–137 use the source-appropriate 服務單 and an inclusive 最遲於六月五日;
Q138's attached older group snapshot uses 申請 and 六月五日前. No automatic
source selection or evidence rewrite was done. No assembly or release.

`cd "$D" && python3 -m unittest -v test_reconcile.py` passes five tests with
the above fixture, including verified audio schema differences, invalid
migration decision, and incorrect audio digest refusal. This fixture is not
claimed to be the latest remote branch or all 600 reviewed items.

The post-move auditor was separately smoke-tested on unedited Test02 and
Test03 source packs plus their real audio migration fixtures: all 238 clip
paths per exam passed independent full PCM comparisons with the original
sources. Those checks exercise the relocation mechanism, not verification of
all items or compatibility of those draft packs.
