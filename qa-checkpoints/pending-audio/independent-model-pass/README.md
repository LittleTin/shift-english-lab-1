# Actual existing-audio cross-check, no listening item promoted

Pinned work evidence: `9047812299d67c6a69b4b5e7cb39c8544b180651`.
Read the current authority before continuing. Use `refresh_remaining.py` to
subtract verified numbered records from the pinned prior scope, preserving
all exact disputed-token/frame sources and preventing duplicate queued work.
The pinned index contains 33 / 35 / 17 pending items by test, not recordings
approved for replacement.

Three lanes probed 16 still-held questions on actual byte-verified source
MP3 windows, independently of earlier Whisper runs: T01 12/27/31/39/43/67/96;
T02 7/13/41/49/59/84; T03 2/4/84. Additional already verified items served
as positive controls and were not reopened or counted again. Independent
decoder outputs, prior disputed-source references and interpretation are
separate. Several controls also produced wrong words or option labels, so
these unprompted results cannot distinguish every disputed phone or approve
an item. No synthetic audio, upload, or user listening happened.

Test01 Q031: new recognizer rendered **team dinner** in both modes, but
only its formal output read “I will be able,” not the expected negative
as supported by the previous transcript. The secondary recognizer also
misheard ordinary known-good controls; this is not proof the recording is
wrong. Keep Q031 held. Reconfirm both negation and the noun before any
acceptance. Test01 Q039 and Q043 offer partial lexical corroboration, not
complete scoped audio proof. For all modes and rest of test see individual
review records. No verified or difficulty ledger changes in this checkpoint.

Local reproduction, using the installed FFmpeg `asr` filter and only data
from the official CMUSphinx PocketSphinx Git ref
`f20ff1b7a5db64c5e892a798479e20df86e79a35:model/en-us`. Pin and verify the
asset bytes and model's data hashes; no custom grammar or prompt:

```sh
python3 probe_existing_audio.py --repo "$REPO" --ref "$STAGE_SHA" \
  --asset-root "$EXACT_ASSETS" --model-dir "$MODEL_EN_US" \
  --test test-01 --out "$NEW_LOG" 10 11 12 27 31
python3 refresh_remaining.py --repo "$REPO" --ref "$STAGE_SHA" --out "$NEW_INDEX"
```

Use only as a cross-evidence tool. When control performance is inadequate
or engines disagree about negation, options, roles or names, use qualified
listening, independently valid acoustic evidence or an authorized F0 repair;
do not mark a guess as resolved. Do not repeat this same run without
additional evidence. Drafts under the neighboring test folders are separate
unapproved work and do not reduce the number of pending audio items.
