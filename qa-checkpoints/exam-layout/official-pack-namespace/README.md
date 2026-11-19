# Official catalog namespace (local HQ candidate)

Run `python apply.py <scope-site>/assets/app.js <scratch>/app.js`. The input
is byte-pinned to the composed HQ runtime; apply after its Opus, resume,
backup and disclosure overlays. Recompose explicitly if the baseline changes.

Catalog entries always use the trusted catalog pack path/index, including
catalog additions. Custom packs with other IDs remain supported. Record
normalization filters reserved custom definitions rather than resetting
the backup. Scores, stored original answer keys, attempts, notes and stars
remain unchanged. If a conflicting definition was present for an unfinished
attempt, preserve that attempt and fail closed on resume rather than apply its
answers to different questions. Custom definitions with other globally
conflicting question/group IDs are excluded from the active index and kept
in data for export or correction. When customs are present, load official
indexes first; fail closed rather than letting custom definitions overwrite
official IDs while the official indexes are absent.

This patch does not implement authoring/Git signatures, navigation lockdown,
or a new historical snapshot. It neither opens nor modifies live browser
records. Local tests use fictional entries and the application's own functions.
`node test.cjs <scratch>/app.js` (four scenarios); existing refresh journal
suite 3/3 and backup readonly suite 8/8 also passed against the output.
