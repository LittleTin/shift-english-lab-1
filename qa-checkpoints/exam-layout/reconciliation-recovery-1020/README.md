# Complete present-ledger reconciliation, offline only

This checkpoint replays immutable Git evidence through the current reconciliation code. Requires Python 3.12+ (safe tar data filter), Git, and an exact output of the pinned audio composer. It does not authenticate spoken content itself, alter the repository, change the input audio stage, or perform the browser and release gates.

1. Have local Git objects for: work evidence `92bf2a621452ac8e54db87eb50f4f0cd9456c379`, raw reading baseline `8ab882d065cd33550ab8e694cc035c5135f1b146`, audio composer source `fa6e3f8fa86a6b8f701dc4574db32bdbdc35cb01`, and the eight exact frozen refs in `recover.py` (including deployed 1.4.1). Fetch exact commits where absent; no checkout is needed. FFprobe is required only by the audio-composer preparation.
2. Extract the committed composer and create a separate audio stage, or use an existing exact one:

       git -C "$REPO" show 92bf2a621452ac8e54db87eb50f4f0cd9456c379:qa-checkpoints/approved-overlays/composition-proof-0950/compose.py > "$SCRATCH/compose_audio.py"
       python3 "$SCRATCH/compose_audio.py" --repo "$REPO" --out "$SCRATCH/audio-stage"

3. Run the recovery in an absent output outside the repository and input stage and on the same filesystem as the stage (scratch media use hardlinks, not copies):

       python3 recover.py --repo "$REPO" --audio-stage "$SCRATCH/audio-stage" --out "$SCRATCH/reconciliation"
       cmp "$SCRATCH/reconciliation/proof-summary.json" proof-summary.json

The audio receipt and all three assembled input pack hashes must match. It restores original graphic bytes only from recorded Git artifacts: archived Q001/Q003 patch, T02/T03 visuals checkpoint, and Cedar’s approved reading reserve. It SHA-checks all present image associations, verifies exact Git-backed original and replacement identities, and applies only approved reading splices to the listening-composed packs; previous and alternate plans, legacy questions and active listening plan stay unchanged. The structural audit needs no browser and makes no HTTP calls.

Keep only this recipe, helper and reduced proof, not the extracted ledger, media tree or output data. Current proof: 542 present rows accepted with zero conflicts, 58 absent listening rows, difficulty/release incomplete. Historical snapshot uses immutable deployed 1.4.1 content evidence, not any guessed release timing. Re-run on a new reviewed scope if baseline files change; don't replace receipt or pack hashes to skip a mismatch.
