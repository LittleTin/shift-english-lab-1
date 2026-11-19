# Three-exam offline content reconciliation

**Content evidence only, not release approval.** All 600 active items reconcile against exact Git evidence at `1968b72a3eb23d84e718ed787bd239113e2f3791`; there are 200 accepted per exam, no missing, held or conflicting item. Existing timed audio spans and prior/alternate plans are unchanged. The final evidence may replace the active question ID on the matching current frame without changing playback; the exact frame indexes and before/after IDs are in `proof-summary.json`. The canonical authoring split and rebuild reproduce all three pack files byte for byte, including the legacy fields that existed in the listening inputs. Original retired readings/deployed source packs remain archived, not active practice content.

The 600 difficulty reviews exist, but the genuine per-exam distribution gate is still **open** (not a label-edit task). Native desktop/mobile playback, historical restore and scoring, media relocation/byte proof if relocating, and public deployment acceptance are separate. These scripts do not deploy, synthesize, contact websites, edit the original repository, or make a release decision.

## Reproduce

Requirements: Python 3.12+, Git, FFprobe and the frozen commits named in the historic recover script and `replay-chain.json`. Use an absent scratch output outside the repository; there is no requirement for a particular machine path.

1. Extract the existing historical composer and execute it into an absent audio stage. Its work and prior deployment object references are explicit and its output receipt and all three pack byte hashes are independently checked by the next step:

       git -C "$REPO" show 92bf2a621452ac8e54db87eb50f4f0cd9456c379:qa-checkpoints/approved-overlays/composition-proof-0950/compose.py > "$SCRATCH/compose.py"
       python3 "$SCRATCH/compose.py" --repo "$REPO" --out "$SCRATCH/audio"
       python3 recover-historical.py --repo "$REPO" --audio-stage "$SCRATCH/audio" --out "$SCRATCH/historic"

   The recovery reproduces the 542-item historical proof and writes only scratch copies plus the three reviewed reading-spliced input packs. Do not substitute externally produced graphics or patch historic baselines to avoid a guard.

2. Starting from the composer's three listening-only inputs, replay the post-composer steps listed in `replay-chain.json` in order. Each referenced overlay folder is from the exact work tree; follow its checked-in README or apply helper for arguments and exact assets, using a distinct absent output for each step. Supply authorized inputs/receipts when required by the overlay. T03 Q017 is practice-only and has identical before/after formal plan hash: it is still a required ordered step. Neither a hold nor a reserve draft is part of this replay. Do not treat raw branch packs, the historical recovery's reading-spliced pack files, or a browser preview as the final listening inputs.

3. Reconcile against the one exact 600-row Git tree, and rebuild authoring:

       python3 verify.py --repo "$REPO" --historical "$SCRATCH/historic"          --test-01 "$SCRATCH/replayed-test-01.json"          --test-02 "$SCRATCH/replayed-test-02.json"          --test-03 "$SCRATCH/replayed-test-03.json"          --out "$SCRATCH/canonical-proof"

   The verifier checks each referenced Git artifact, all final listening input byte hashes and canonical plan hashes, the historical proof, source reading identities, archived plan identity, all present evidence and SHA-bound images and audio, and each final canonical data file's byte hash. It invokes the exact Git-backed exam validator and authoring layout splitter/builder without omitting legacy questions. The only permitted active playback changes during final reconciliation are same-number question-ID rebindings from the reviewed item snapshots. All generated packs, asset copies, expanded ledgers and editable-source output remain in scratch and are not transferred by this checkpoint.
