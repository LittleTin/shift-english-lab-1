# Three-exam local acceptance checkpoint (not a release pass)

- Spec: `SHIFT-SPEC.md` at `5ea0d1da79e5ccc3677ca73ee226df20b9eac6be`. Inputs are the existing media proof snapshots, not the latest repaired question drafts.
- Existing repository Node tests: seven passed, including unfinished old image/content, excluded legacy IDs in new active pool, tab-pause timers, autoplay-block retry, no replay after group completion, and normalized checkpoint behavior. These use test doubles; no browser or audio hardware claim.
- The separate retired-result Node fixture: two passed, proving stored grade/answer/note survival with retired content and no fabricated grade or answer for older thin records. That fixture covers completed sessions, not historical in-progress exams.
- Actual split into authoring folders and rebuild with `--omit-legacy-questions` passed for all three media overlays: 200 current questions, 54 formal groups, 284 frames, 2,700.000 seconds, zero legacy IDs per exam, 714 actual ranged WAV files. The validator probed media durations. 544,439,113 bytes in the rebuilt content/media tree (filesystem `du -sb`, before full site shell); 543,453,734 additional bytes in authoring. Do not publish both duplicate trees as the site root; together already ~1.088 GB. Audit the actual independently built output and repository accounting per spec.
- Real Chromium is installed, but both explicit writable-profile CLI and Playwright start failed on this executor (fatal `process_singleton_posix.cc ... socket() failed: Operation not permitted`). No page loaded and no real browser pass was recorded. `node --check browser-smoke.cjs` passed. Run that smoke harness on a supported Chromium environment; use headed browser for the tab-visibility case if headless does not report actual hiding. Also run real target mobile Safari/Chrome acceptance, checkout/asset URLs and version consistency, and verify complete answer-reveal/scoring and export behavior. A desktop viewport emulation is not a mobile hardware test.
- Known release blocker independent of browser availability: `resume()` rejects an unfinished session if any saved ID is absent from the active pack. Removing `legacyQuestions` from the new active pack currently makes a preexisting attempt with retired IDs fail to resume. The proposed `retired-results.patch` preserves completed results only. Need tested same-origin compatibility for previous in-progress sessions, retaining original IDs, answer order, audio timing and saved answers without counting retired IDs as current questions. The browser harness includes a deliberately failing gate until fixed.
- Neither source checkpoint nor overlays have been pushed by this work. The generated trees are scratch, not staging artifacts to commit. Rebuild from finalized reviewed items, not these proof snapshots.

## Commands

From the workspace parent, `bash shift-media-migration/acceptance/prepare.sh <fresh-output>` assembles a quiz-only smoke directory. It is not the full site (audit ancillary/demo references separately). Test via an authorized staging origin; e.g. where a local server is supported, serve `fresh-output/rebuilt` over HTTP. Then run:

```sh
HEADED=1 node shift-media-migration/acceptance/browser-smoke.cjs http://127.0.0.1:8123/ fresh-output/rebuilt
```

Set `CHROMIUM_BIN` if installed elsewhere and `RETIRED_TEST_ID` if the finalized candidate retires a different Test 01 key. The script uses isolated browser profiles and synthetic backup data only.
