# Test02 Q013/Q014/Q016 exact scoped overlay (not a release)

The three single-item Part 2 groups replace scored options, so current
question and group IDs use `-r2`. Original keys A/A/B remain unchanged.
All old media files, legacy questions, previous/alternate plans, and
the old committed release snapshot stay intact. Do not use this item
checkpoint as evidence of native browser playback or old-session resume.

From an isolated candidate tree on exact source 7b3e6b7, with the six
SHA-bound final WAVs available under its root:

```sh
python3 qa-checkpoints/approved-overlays/test-02-Q013-Q014-Q016/apply.py \
  --input scratch/data/test-02.json --output scratch/data/test-02.next.json \
  --assets scratch --select 13 14 16
```

Compare the emitted timing receipt, adopt the resulting pack only inside
the isolated authoring tree, regenerate JS from its JSON via the canonical
layout builder, and run the native exam validator. The script also
supports a strict subset; use a fresh baseline for each run. It rejects
changed input audio, changed plan, changed selected content, collisions,
and a new Part 2 pause floor below the permitted old baseline. Applying
a later overlay in this same exam requires explicit composition/rebase,
not disabling the current-plan SHA guard.

Actual isolated `tools/validate_exam.py --site <candidate> test-02.json`
passed: 200 questions; 54 listening groups; 284 frames; 2,700.000s;
two existing archived IDs; 57 distinct ranged assets. Questions
Q013/Q014/Q016 keep exactly two distinct audio modes each, and their
upper-section retiming adjusts only Part 2, preserving the Part 3 start
and every answer window. Q019 is not part of this overlay.
