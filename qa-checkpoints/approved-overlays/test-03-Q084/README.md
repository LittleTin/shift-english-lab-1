# Test03 Q084 formal-stem-only overlay

Use on top of the independently reviewed Test03 Q095–097 compact
overlay (predecessor plan digest d15464d8ee3bfdb21eae5f8487c4a10908d8d40e964f95cf3bdf57088c054528).
The only edited question text and audio is the spoken Q084 paraphrase.
Q084's key, ID, evidence and options stay unchanged. The unchanged g049
audio uses the exact sibling Q083/Q085 approved group metadata; the sole
difference to the predecessor group is accepted Traditional Chinese
wording. Old numbered cue, talk, practice audio and all sibling audio
paths and exact source ranges are preserved.

Replay in a scratch pack with the old and new media hydrated:

```sh
python3 qa-checkpoints/approved-overlays/test-03-Q084/apply.py \
  --input scratch/data/test-03.prior.json \
  --output scratch/data/test-03.next.json --assets scratch
```

Replacement is 5.13750 seconds, 1.43588 more than the old stem.
The 29 ordinary Part4 pauses each lose at most 0.04952 s (min 6.45418 s).
Protected Q087 chart pause remains exactly 9.82898 s. Parts 1–3 are
unchanged. Total is 2,700 s, 100 scored answer frames, 284 frames.
Original old audio bank files and immutable previous publication
snapshot must be retained. Do not trim spoken media to fit.

Standard isolated validator passed 200 items/54 groups/284 frames/2700 s
and 58 distinct ranged assets. Reconciled Q083/084/085 exact audio
associations as well as matching g049 approved bilingual metadata.
This does not establish native browser playback, in-progress legacy
session restore or overall website acceptance.
