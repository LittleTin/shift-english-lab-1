# Exact content-bound difficulty reviews

Use current verified-item active questions and groups, never a stale
`data/test-NN.json` that has not been rebuilt from the work ledger. A separate
compact difficulty review records both immutable canonical hashes, question
identity, old and proposed labels, and the actual reasoning required. A label
fix does not change presentation, scoring, item identity, or historical data.
Acting on an authored replacement requires a new item review/version where
applicable; the change invalidates the old difficulty record. Archive and
resume compatibility still have their own release gates.

Use `--difficulty-ledger <difficulty-root>` when running the existing
reconciler. A final output directory is never built without both complete
content evidence and a qualifying difficulty review for every active item.
Ordinary progress checks can run without this option. The report separates
content holds, missing difficulty reviews, review integrity and distribution.
It does not treat absent siblings, or mixed-level groups, as eligible for
strict single-level practice. Entries for unverified content do not pass.
The report does not force quotas or elevate an item because a chart appears;
it detects levels with only a symbolic one or two items, absent complete
practice units and lack of a leading middle tier. The smallest UI target
(10) remains a useful planning metric, not a mandate to pad. Actual difficulty
judgment and browser acceptance are required even when metadata checks pass.

Run `python3 -m unittest discover -s shift-media-migration/difficulty -p 'test_*.py'`
from the workspace parent, and the existing reconcile tests. Five new tests
and six existing reconcile tests pass. Not production readiness; reports
always retain `releaseReady:false`.
