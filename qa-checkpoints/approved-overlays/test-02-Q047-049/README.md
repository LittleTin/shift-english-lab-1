# Test 02 Q047–049 cumulative work overlay (not released)

Compose the committed Q013/Q014/Q016, Q019, and Q044–046 overlays first.
The exact through-Q046 predecessor pack SHA-256 is
`9ec5c813dda01db241e4d21d81d3c025947d6f19a6c7f5a5007a9d8dfbb5c232`.
The predecessor formal plan canonical SHA-256 is
`f993b36948e7a37786348833f69a747778eb1c786d03908923160bb39c5f8461`.
Install only the new G037 WAV at its manifest path into the hydrated assets
root. Replay into a different absent file:

```sh
python3 qa-checkpoints/approved-overlays/test-02-Q047-049/apply.py \
  --input composed-through-q046.json --output q049-candidate.json --assets <site-root>
```

The exact scratch output SHA-256 is
`b5d0edf1d14ddf905fd4ac4293c02e56bfab19c5520b6d6023b21ad75c02fd9d`;
the new canonical listening plan hash is
`f2159b323f968a846d9ff993ecd7f033dec171e5d15ba14fe582eda26da8f533`.
If the old plan or exact binding has changed, recompose and remeasure;
do not bypass guards.

G037's original group boundaries, cue and numbered stems stayed fixed in
association. The new 29.575 s exact shared WAV is used by formal and
practice. Local pauses rose from 11.28411 s to 11.31378 / 11.31378 /
11.31377 s. All unrelated groups, existing G035 original, prior listening
plan variants and legacy question arrays stayed byte-equal in their
canonical objects. IDs and keys A/A/D stayed intact. Original G037 scope
and files remain recoverable for historical playback. Latest content
edition and exact old open-session compatibility must still be tested
before release.

Whisper small.en exactly transcribed all turns. Independent Vosk focused at
real playback speed corroborated the salient two-object conjunction,
previously misheard on old audio; full Vosk did not transcribe this phrase
verbatim. The exact old cue and stem windows are preserved. This is
source-bound offline model and structure verification, not human
listening or browser acceptance. Exam validator checked 200 questions,
54 listening groups, 284 frames, 2700.000 s and 60 distinct ranged assets.
G035 is explicitly not included or promoted in this bundle.
