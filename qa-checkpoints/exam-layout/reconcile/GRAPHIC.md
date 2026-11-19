# Single verified SVG in a whole Part 7 reading rotation

Use only when one exact already verified Test03 article figure is kept in a
new reading-group revision and the locked deployed baseline had no such
figure. The production snapshot is archived byte-for-byte; do not insert the
new figure into a prior session. The reviewed older work item and its figure
are separately recoverable. Reusing an item ID when the shared reading changes
is disallowed, even when the answer and stem happen to stay identical.

Reserve format `complete-single-svg-reading-group` adds one `media` object
`{runtimePath, checkpointPath, sha256}`. Lock exact old five question records,
their common group and the chart by immutable Git object, just as for text
groups. The new recipe is `replace-whole-graphic-reading-group-by-exact-old-scope`,
with `preservedGraphic` matching the reserve and `retiredLegacyHistory`
linking the exact deployed no-image group, all deployed questions in that
scope and the raw prior deployed pack hash. Every old/new item record carries
the same image SHA. The runtime path addition must be absent from every base
pack and be unique; no other media, navigation or historical plan can change.

Re-run `PYTHONPATH=qa-checkpoints/exam-layout/reconcile python3 -m unittest -v
test_rotation test_standalone_rotation test_graphic` from a workspace that
has a local clone named `shift-qa` and the immutable fixture Git objects.
The tests construct temporary proposed verification rows for Cedar;
synthetic proof is not content adoption, deployment, or browser acceptance.
The offline replay exports new candidate media and historical snapshots in
separate trees. Do not deploy either offline replay directory wholesale.
