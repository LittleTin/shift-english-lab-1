# Formal refresh cursor and narrow-layout fixes

Apply after ordinary practice/history/resume compatibility composition to a fresh directory:

    python3 apply.py staged/assets/app.js staged/assets/style.css new-output
    node --check new-output/app.js
    node test-journal.cjs new-output/app.js

Exact tested baseline composed app SHA-256 fdcc6ca5ef0424f0a9a8cc75f6184cc670377c7b579a8afeae0b010868c2850d; baseline CSS 69467334d36dacd1c81eb77238d385924cf559a5ef17b185762e8a546e67c62d. Output app 9cfec7e06464791a0419c9432c12b9be9fefeb5a07d503fcad6dd7a70d2bda5e; CSS 6f51add42916fb3339aea9c8a1011cd8a9cc2db772c205be135c49acbae03fec. Exact once-only anchors fail on drift. Subsequent exact backup-readonly composition was independently verified; combined app b6f4ecc565af54428dc70d8784884c5a905910a6aac85ea806a37523a6f7d4b2.

Synchronous tab-local cursor journal at pagehide/real visibility hide after native capture. Resume consumes it once after resolving applicable pack. Require exact active identity/version/edition/index/question/group, same physical source frame descriptor and strictly newer offset. Only its cursor changes; unrelated answers, notes and archive facts are untouched. Not a general multiwriter guarantee or a browser-crash guarantee if lifecycle callbacks are not dispatched. Unit tests: 3/3 (increase, stale/foreign/wrong-frame refusal, storage unavailable). The media frame descriptor binds physical URL and interval, not an embedded cryptographic media digest; the staging receipts separately bind source bytes.

Narrow CSS edit: only existing <=760px stats grid, allow grid tracks/cards to shrink and text to wrap, rather than hiding horizontal overflow.

Native observed baseline refresh: old MP3 time 1.332403 s, durable group g006 frame 0 offset 0, reload reopened its preceding cue. Patched: old MP3 34.493485 s, previous durable g007 frame 2 offset 14.148914 s, refresh persisted frame 2 offset 14.21275 s with the journal consumed, playback resumed same MP3 34.723976 s including click latency. Separate genuine tab visibility test and scope in final-browser/canonical-private. At 390px iframe layout, original two stat cards exceeded CSS client width 375; scroll width 390 shrank to 375 after patch. This is Chromium viewport layout, not physical Safari or Android qualification.
