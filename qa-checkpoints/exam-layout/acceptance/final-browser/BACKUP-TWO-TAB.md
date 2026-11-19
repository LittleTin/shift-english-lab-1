# Final website acceptance supplement: stale-tab backup and media ranges

Run **alongside** the existing Cedar old/new-history smoke and final browser
runbook, not instead of either. The exact static output and manually reviewed
historical epoch are prerequisites to full acceptance. This supplement only
uses synthetic state and an isolated loopback origin; no real user backup.

| Target | Deterministic scenario | Required evidence |
| --- | --- | --- |
| Desktop real headed Chromium | B opens Data before A imports synthetic current Test01 state at Q098. A resumes native WAV, chooses an answer, switches to B; B exports without reloading. A reloads and resumes the same position. | Exact staged app SHA and pack, candidate WAV + prior MP3 HEAD/206/416 with exact bytes, native hidden/paused state, real downloaded JSON equal to newest index/answers/frame/offset/note, unchanged stored state, same-media nonzero offset after reload. Code: backup-two-tab.cjs. |
| iOS Safari on device | Repeat the actual backup export and inspect downloaded JSON in Files or a safe local reader. Switch apps/lock while playing at nonzero offset, return/reload, dismiss autoplay prompt if shown and explicitly resume. | Record iOS and Safari version/phone; native background pause, no replay, coherent frozen timer, exact downloaded state and resumed range. Note if two same-origin tabs are unsupported by chosen privacy mode, do not silently substitute. |
| Android Chrome on device | Same exercise; background using app switch and rotate or increase font size before returning. Inspect local downloaded JSON and reload original tab. | Same checks plus readable controls and no viewport overflow. Desktop mobile emulation is layout-only. |
| Storage fallback | On an intentionally isolated test profile, reproduce the two-tab sequence with app reporting fallback localStorage if available; check backup after background/reload. | Explicit storage backend and data parity; if unavailable record NOT RUN, never conflate VM doubles with the real browser. |

Run from repository setup with trusted existing Node and Playwright:

    node --test test-two-tab-transport.cjs
    node backup-two-tab.cjs http://127.0.0.1:PORT/PROJECT/ /path/to/exact/static-site SHA256

Use an approved same-computer loopback server that supports byte ranges and
serves the chosen project base. The script rejects public hosts, userinfo,
redirects and foreign browser requests. It needs a real headed window and
native tab visibility. Exit 2 means visibility not reproducible, not pass.
Do not relax the loopback check for a public preview; mobile validation on an
owner-approved isolated target is still manual. The exact candidate must
retain prior MP3 and current Q098 WAV. Record SHA, device/engine, backend,
sample ranges, exact offset, result and screenshots or console separately.
The transport unit uses a small local synthetic HTTP server and additionally
checks corrupt Range data fails closed. No browser result in that unit test.
