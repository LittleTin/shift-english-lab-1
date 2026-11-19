# Test 02 Q041–043 explicit model-code overlay (work only)

Compose Q013/Q014/Q016, Q019, Q044–046, then Q047–049 before applying.
Exact through-Q049 predecessor pack SHA-256:
`b5d0edf1d14ddf905fd4ac4293c02e56bfab19c5520b6d6023b21ad75c02fd9d`.
Its canonical plan:
`f2159b323f968a846d9ff993ecd7f033dec171e5d15ba14fe582eda26da8f533`.

```sh
python3 qa-checkpoints/approved-overlays/test-02-Q041-043/apply.py \
 --input composed-through-q049.json --output q043-candidate.json --assets <site-root>
```

Exact scratch output SHA-256:
`bf4bbd9df5a47d2415778cf7ddc386bcdbfed2cdbfc65b5cc3c3cdd5e849b82c`.
Canonical active-plan SHA-256:
`e03f5d75aabfd86f16521316dee9ab464d5a2058a02d3cd3a876a457220d680f`.
The old group guard, original item hashes, old asset bindings and every
affected frame are checked; do not force replay on another plan.

The new exact 24 kHz mono PCM WAV is 28.6375 s; its SHA-256 is
`13da2bf68d9bf8fbcd3858fa3ceaeeaa4e16659b7b7cf719e777fb39965f59c8`.
Both modes use this same file. Group and item IDs, keys B/A/D, prompts,
choices, numbers, cue and stems remain unchanged. G035 anchors
[1107.12654,1183.15374] are fixed; its answer pauses increased from
11.28411 to 11.68228/11.68228/11.68227 s. G036, G037, all unrelated
frames, previous/alternate plans and legacy arrays stay unchanged.
Keep predecessor scope and source audio immutable for old in-progress
sessions. Offline validator checked 200 items, 54 listening groups, 284
frames, 2700.000 s and 61 distinct audio assets.

Unprompted Whisper small.en transcribed the explicit letter R, eight and
nine exactly. Independent Vosk small graph corroborated both prefaced
“the letter or” (phonetic R) with the correct distinct numbers. Vosk larger
graph independently supports other operational anchors but does not
transcribe both codes exactly. This is exact scoped offline evidence,
not human listening, browser/session acceptance, or publication.
