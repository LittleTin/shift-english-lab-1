# Two independent Opus work overlays, not public release

This transfer contains 18 reviewed Test01 medium replacements and the three
reviewed Test02 G046 items only. The record overlays have exact encoded Ogg Opus
hashes and path/range association. Original pass records, included in
top-level question-reserve/ for replaced units, stay immutable and out of
practice/playback. Reviewed follow-up scope in Test02 outside G046 is not folded
into this transfer. Test02’s difficulty distribution remains incomplete.

The separate association-proof is a digest-only replay of all 600 contextual
content/review bindings, including approved earlier work. The 21 updated
delivery records are under
qa-checkpoints/exam-layout/opus-active-projection/scoped-rebound/, **not**
replacement files for the previously verified canonical raw ledger. Both use
exact readable roles. Retained cues are included with the scoped media for
playability; there is no raw-audio or full runtime copy. The four G046 Opus
files are copied byte-for-byte from their independently reviewed delivery files,
not transcoded again.

## Reproduce

Start from the exact previous active-only HQ stage pack recorded in overlay.json
for the selected exam (the earlier three-exam HQ scoped projection). If
reconstructing it, use that earlier proof's canonical input pack hashes and HQ
56/96 Opus projection, not the original public preview. Verify canonical
pre-projection source identities using canonical-replay-guards.json. The
installed work overlay is a recipe, not an instruction to overwrite an
existing authored directory. Apply into an absent scratch output:

    python apply.py --base-site "$EXACT_PRIOR_HQ_SITE"       --media "$THIS_TRANSFER_ROOT" --exam test-01 --out "$SCRATCH/t01"
    python apply.py --base-site "$EXACT_PRIOR_HQ_SITE"       --media "$THIS_TRANSFER_ROOT" --exam test-02 --out "$SCRATCH/t02"

The helper guards the exact base pack/plan and every patched slot/group/frame.
It resolves each successor active media file to the exact SHA in either the
base site or the transfer root, allowing the two local pack files to be placed
into a separate test site with those assets. New pack, JS wrapper, and plan
hashes must match. Both scripts were replayed locally and their outputs matched
the preserved candidate byte-for-byte. T02 replay asserts that only Q074–076,
G046 and its frames change, with no global label rewrite. T01 also materializes
its reviewed labels (only the difficulty field on otherwise unchanged items).

All whole-site gates, native target acceptance and prior owner lock policy
remain separate. This work did not retry Azure egress, synthesize, commit,
publish, or create formal locks.
