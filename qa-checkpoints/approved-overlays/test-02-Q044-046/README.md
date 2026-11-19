# Test 02 Q044–046 offline working overlay

Do not deploy this unit. Reconstruct the predecessor by composing the raw
Test 02 pack plus the Q013/Q014/Q016 overlay and then the Q019 overlay. The
predecessor active listening plan's canonical SHA-256 is
`e93ef9fe0d1ebd66f94bcdd0a262488f5f4bbb27800b51a7590c6e6856cdafff`.
The exact independent local predecessor pack is SHA-256
`1e5f34ab02ec86dd86f7a1199dde9cca3d7a30b7776d3419c9ff38bc22f53788`.
Replay into a distinct absent output, with the source and candidate media
hydrated at exact runtime paths below the assets root:

```sh
python3 qa-checkpoints/approved-overlays/test-02-Q044-046/apply.py \
  --input composed-test-02-through-Q019.json \
  --output candidate-test-02-through-Q046.json --assets <site-root>
```

The expected scratch output SHA-256 on the pinned predecessor is
`9ec5c813dda01db241e4d21d81d3c025947d6f19a6c7f5a5007a9d8dfbb5c232`.
Stale input plan, question, scope or bytes must fail; do not bypass the guards.
The previous and alternate plans and current legacy array remain untouched.
Keep deployed old session/audio/key snapshots and `prior-scope.json`. Do
not publish until actual historical and current browser replay also passes.

One immutable 24 kHz mono 16-bit Azure dialogue supplies formal and practice
at [0,32.475]; one new Q045 en-US-JennyNeural numbered stem is [0,5.200].
Retain the exact old cue and the Q044 and Q046 stem ranges in the unchanged
cue bank. Do not overwrite existing shared bank bytes. The old turn-one
forecast is now explicitly monthly, and the recorded third turn explicitly
requests boxes without printing. Q044 and Q045 have successor IDs for the
revised evidence or scored option. Q046's deadline change is only zh-TW and
retains active ID and original key. Manual solution keys remain D/C/B.

The group boundaries remain [1183.15374,1261.73224]. Its answer windows
are 9.75051/9.75051/9.75052 seconds, versus 11.28411 each before. This is a
scoped pacing tradeoff, not a global floor. All unrelated timeline frames,
including other question audio, their answer windows, Part boundaries and
closing, remain exact. The resulting pack contains 200 questions, 54
listening groups, 284 frames, and 100 answer windows in exactly 2700.000 s.
Offline structural validation checked 60 distinct audio assets.

Unprompted Whisper small.en recovered the complete new dialogue and exact
new Q045 numbered wording. Vosk independently corroborated the passage's
monthly quantity, unprinted boxes and deadline, with unrelated word errors;
on Q045 it segmented “change does” as “changed as”, not a second verbatim
match. Both decoders independently recovered old generic cue and both
retained exact numbered stems from their tested old slices. This is documented
offline model corroboration, not a claimed human listening session or browser
test. A complete project build must use the ordinary evidence reconciliation
and all remaining release gates; this overlay alone is not a release.
