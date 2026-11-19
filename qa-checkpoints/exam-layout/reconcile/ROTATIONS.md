# Offline reading rotation replay (not a release)
 
The authoring work branch holds original verified records and replacement
records, not a deployable checkout. Some source runtime JSON is still older
than the versioned, individually verified evidence. Use the deterministic
replay before reconciling those packs. Never copy the work branch or the
offline-history output to a site.

The replay never changes Part counts, question numbering, active media route
sets, or listening frames. A published/archived old question is resolved
against its separate exact old Git pack, not the new passage or key. When a
legacy question's group is replaced, the helper accepts removing the orphan
legacy question from the local reconciliation input only after reproducing
that exact historical question and group from the prior immutable pack and
recording the prior pack byte-for-byte offline. This does not establish
browser resume or when the prior GitHub Pages version was live.

## Pinned proof and offline reproduction

From the workspace root, point `D` to the directory containing these files
and set `REPO` to a local clone with the objects present. Read-only tool;
no fetch, push, branch update, or browser/network call is made.

```sh
D=shift-media-migration/reconcile
REPO="$PWD/shift-qa"
BASE=8ab882d065cd33550ab8e694cc035c5135f1b146
REF=1183d26ee5a97ae050dec34ec6bb86c872adc058
SHIFT_TEST_REPO="$REPO" python3 "$D/test_rotation.py" -v
python3 "$D/rotation.py" --repo "$REPO" --base-commit "$BASE" \
  --reconstruction-commit "$REF" \
  --exact-old-overrides "$D/baseline-8ab882d-overrides.json" \
  --output "$(mktemp -d)/rotated"
```

The override file names eleven genuine baseline-versus-verified differences.
Use only with the pinned proof above. No automatic SHA fallback is allowed.
They are Q148 option rationale, Q149 translation/rationale, Q151 option
rationale, the Test01 repair notice zh passage, Test02 stock count zh passage,
Test02 Q162/Q164 r1-versus-r2 already verified revisions, Test02 Q163 options,
Test03 old market notice zh passage, and Test03 Q153 options/Q154 zh prompt.
The override does not assert equality: it enumerates exact old input and
reviewed-old values for narrowly scoped discrepancies. Those **11** keys cover eight questions plus three group passages.
All unrelated runtime content remains byte-for-byte recoverable in the
baseline archive. A changed input, changed replacement, missing history,
duplicate or unused override rejects the operation.

For integration place `rotation.py` next to `reconcile.py`; the existing
sibling `difficulty/` package remains needed for that gate. Reconcile accepts
the new topology only as an optional, pinned reading-overlay step:

```sh
python3 path/to/reconcile/reconcile.py \
  --site "$CANDIDATE_SITE_WITH_PINNED_BASE_PACKS_AND_REVIEWED_ASSETS" \
  --ledger "$VERIFIED_ITEMS" --difficulty-ledger "$DIFFICULTY_LEDGER" \
  --rotation-repo "$REPO" --rotation-base "$BASE" \
  --rotation-evidence "$REF" \
  --rotation-overrides "$D/baseline-8ab882d-overrides.json" \
  --report "$NEW_REPORT"
```

Site packs must byte-match the baseline Git pack; the text rotations are
applied in memory before strict numbered reconciliation, and every rotated
ledger entry must byte-match Git. Site media independently must match the
existing verification hashes. The pinned isolated proof extracted baseline
data/media using `git archive "$BASE" data assets audio`, overlaid only
previously reviewed candidate graphics/pictures into the isolated fixture
site, and exported the two ledgers with `git archive "$REF"
qa-checkpoints/verified-items qa-checkpoints/difficulty`. This proof admitted
all 15 reading replacements and 515 verified revisions, including 515
difficulty reviews, with zero evidence mismatches; the 85 audio gates
remained unmet (33/35/17). Its normal exit code was 2 and it generated no
release output. Real browser/mobile acceptance remains a separate gate.
