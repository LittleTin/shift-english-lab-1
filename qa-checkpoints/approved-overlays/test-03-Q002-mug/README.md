# Test03 Q002 mug, cumulative dual-mode overlay

Apply after Test03 Q084 and Q017 practice-only overlays. Requires exact
predecessor plan digest cf6ea649…898928c **and** unchanged approved Q017
question, group and media hashes. All files in this bundle are authoring
scope only; no release was performed.

```sh
python3 qa-checkpoints/approved-overlays/test-03-Q002-mug/apply.py \
  --input scratch/data/test-03.prior.json --output scratch/data/test-03.next.json \
  --assets scratch
```

Only Q002's English/Traditional Chinese choice D and matching explanation,
evidence, and vocal tracks change. Original A–C, visual evidence and key D
are unchanged. New scored wording uses r2 question/group identity; keep
old item, image, recording banks and previous deployment snapshots
immutable for history and prior-session resume.

Formal track shortens 3.83050 s; distribute this over all six Part1 answer
pauses (+0.63841–0.63842 s). Part2 starts unchanged at 205.84712 s.
Every Part2–4 frame is unchanged. 284 frames, 100 answers, 2700 s.
Validator passed 200 questions, 54 listening groups, and 61 distinct
ranged assets. Q017 and Q084 exact range/hash associations still verified.
Native browsers, old-session restore and release acceptance remain separate.
