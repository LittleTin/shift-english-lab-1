# Local whole-exam lock candidate: SHIFT §§7.1 and 8

Authority: review of `SHIFT-SPEC.md` on the work-branch snapshot at
`3bf8ab8619a22a5a6836f4ef372478b23903d79b`. This candidate installs no workflow,
changes no protection or Pages settings, and does not publish or certify approval.
The present integrated content has not passed every gate. **Do not generate or
install a real lock until the exact full release candidate has finished QA.**

## Trust and operations

- `snapshot` creates only a distinctly named scratch file with
  `status: draft-check-only`. It computes deterministic inventory facts for a
  true Opus-only release candidate without claiming a human or QA decision.
- `generate` is initial-only. Require the exact QA runner receipt bytes pinned
  independently in a trusted policy, and pass receipts plus all evidence
  artifacts from outside the active site. The QA receipt must identify the exact
  inventory hash, exam and release, with eight distinct gate artifact paths and
  content hashes. A trusted pipeline or release controller must verify the actual
  outcomes before creating its trust pin; a candidate's own string saying
  `pass` is not independent proof. The first lock needs no extra owner action
  once actual review is complete. The integrity SHA is a content seal, **not**
  a cryptographic human signature or approval attestation.
- `verify` checks one established exam and `check` checks all established
  exams in the externally pinned release inventory. They use the trusted
  previous exact lock file SHA-256; the current candidate cannot supply its own
  trust baseline. The candidate's newly rehashed/replaced lock is rejected even
  if its internal hash matches. `check` validates JSON/JS scope and built-in
  catalog path mapping without evaluating code. It pins each established exam,
  not the global catalog bytes, so a vetted new exam can be added without
  mutating earlier exams. No amendment/override option exists.
- In CI, source the verifier version, approved initial gate digest/policy digest
  and prior lock digest from a trusted immutable or permission-guarded context,
  **not** from candidate-branch variables or a mutable PR file. Rebuild and
  check in an isolated clean output; block when the checks, prior pin, catalog
  mapping or actual deployment differ. Human-owner major amendment approvals are
  a different workflow: capture the verified actor and exact affected exam,
  items, old digest, intended change and consequences before editing. Reverify
  and create a new independently approved baseline later. No exception is
  simulated here.

## Example commands

Requires Python 3.10+ and FFprobe. Use the existing layout splitter on the
active-only runtime site, preserving exactly 200 editable per-exam question files
and its active group/common media mapping. No historical preview archives belong
in the runtime.

    python exam_lock.py snapshot --source "$AUTHORING" --site "$SITE"       --exam test-01 --out "$SCRATCH/test01-draft-inventory.json"

After **all** QA is verified by the trusted gate runner, for an exam with no
prior lock (example only, not a current command to issue to this candidate):

    python exam_lock.py generate --source "$AUTHORING" --site "$SITE"       --exam test-01 --trusted-policy "$TRUSTED_INITIAL_POLICY"       --trusted-policy-sha "$TRUSTED_INITIAL_POLICY_SHA256"       --gates "$EXACT_QA_RECEIPT" --evidence-root "$EVIDENCE_ROOT"       --out "$SCRATCH/test-01/exam-lock.json"

Compare and install the exact generated lock only in the approved per-exam
source stage. Re-run with the independently pinned approved lock baseline:

    python exam_lock.py check --source "$AUTHORING" --site "$SITE"       --trusted-policy "$TRUSTED_ESTABLISHED_POLICY"       --trusted-policy-sha "$TRUSTED_ESTABLISHED_POLICY_SHA256"

The trusted policy format is `shift-externally-trusted-lock-policy-v1`, with
`release`, exact `expectedExams`, and disjoint `baselineLocks` (exam → prior
lock byte SHA) and `initialExams` (exam → trusted QA receipt byte SHA);
together they must cover the expected set exactly. Before release,
`baselineLocks` must pin all expected exams and `initialExams` must be empty.

The QA receipt format is `shift-post-qa-receipt-v1`, with `examId`, `release`,
`inventorySha256`, and all gate names exported by `GATES` in the script. Each
gate object has `status: pass`, `artifact` (relative path rooted at the
separate evidence directory), and `sha256`.
No usable policy pins, actual lock manifests, or gate receipts are shipped here.

## Covered data and testing

The inventory hashes editable text/options/options order/answer/explanations,
all translations, vocabulary, difficulty, group passages, voice/media/ranges,
full formal schedule, exact files and actual Ogg Opus containers/physical
bounds, and both delivered JSON and canonical data-only JS. It checks the
expected shared formal-example SVG and all media references without symlinks,
URLs, traversal, percent-encoded aliases, colliding cases or missing bytes.
Approved static scoring/UI/browser verification remains explicit evidence.
Practice usability and browser fail-closed formal behavior are a separate
runtime implementation: a local lock checker alone is not an app-side guard.

Run `python -m unittest -v test_exam_lock`. The synthetic fixture is contained
in automatically deleted temporary directories; it is not a usable exam or a
real trusted receipt. Separate actual HQ tests are deliberately draft inventory
only before all content, difficulty, browser and release gates pass.
