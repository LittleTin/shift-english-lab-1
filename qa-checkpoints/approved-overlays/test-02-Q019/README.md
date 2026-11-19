# Test02 Q019 exact cumulative overlay (not a release)

Apply **after** the approved Q013/Q014/Q016 overlay, not against the raw
Test02 pack. The predecessor overlay is present in 43087f63, and the
required assembled predecessor plan digest is
`b6633ba0a0da5e797e9fc00b25f3965c7f041e4ddfc3a62658870c4cf0b1c00b`.
The new overlay verifies that digest and individual original Q019
group/question and predecessor frames. It does not overwrite any prior
record, WAV or history snapshot.

```sh
python3 qa-checkpoints/approved-overlays/test-02-Q019/apply.py \
  --input scratch/data/test-02.predecessor.json \
  --output scratch/data/test-02.next.json --assets scratch --select 19
```

Only Q019 is revised, with new v2 group/question identity, unchanged key B,
and different verified audio assets for formal and practice. The standard
Part2 question-card instructions stay generic; the actual spoken question
is in group passage/transcript and evidence. Q013/Q014/Q016 records and
both mode source ranges/hashes still match, and original numbered cue audio
remains in place. The new timeline digest is
`e93ef9fe0d1ebd66f94bcdd0a262488f5f4bbb27800b51a7590c6e6856cdafff`,
Part3 starts at its original 851.82597 seconds, and Part2 pause minimum
is 7.46105 seconds after reabsorbing the shorter replacement's 2.394 s.
There are 100 answer windows and 284 formal frames totaling 2,700 seconds.
No browser, old-session continuity or release gate is waived by this receipt.
