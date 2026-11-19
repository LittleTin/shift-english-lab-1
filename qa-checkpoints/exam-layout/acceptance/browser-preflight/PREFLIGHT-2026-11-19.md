# Isolated composed fixture, not a browser pass

Source: work `1112ffb97e63592b65c852f0ba5880b293f6e20d`; prior source main `043b91761f63062708d70f7cda3a6b2046cd4cf9`. The fixture uses a *synthetic* prior validity interval and a known verified Q001 replacement to exercise retired-ID compatibility. It does not restore all changes into a publishable version.

- Prior pack snapshot: 3 packs / 304 original assets, immutable from exact main. Composed retired results, version resume and practice filtering patches.
- Exact fixture receipt SHA-256 `398c8a4b5c43c17463294a781db0b790f6dc23c9a156102311205a03da006dce`; 1,078 files / 558,656,237 bytes.
- Per-exam media migration and source-layout split/rebuild completed (714 distinct exact PCM ranged assets). Static composed validation: each exam 200 questions, 54 listening groups, 284 frames, 2,700 seconds, no legacy IDs in active packs.
- `browser-preflight/test_fixture.py` passed on the same-process loopback server: receipt checked, three pages and scripts served, old MP3 and new WAV byte ranges checked. `resume-compat/test_compat.cjs` 4/4 against composed app: old full exam IDs/ordering/assets and position, current WAV, fail-closed invalid epoch/ID.
- Shell-only loopback could not be reached by isolated Cloud Chrome, so none of this counts as real-browser acceptance. Do not open a public port. Use the final authored candidate, real deployment epoch and native desktop/mobile browser/media checks, including old in-progress Cedar, score history, visibility/resume and no replay. No publication from this fixture.

Reproduction order: export immutable old snapshot with `resume-compat/write_snapshot.py`; build proof assets with `media-all/migrate_exam.py` for each exam; `layout.py split --omit-legacy-questions`, then `layout.py build`; call `browser-preflight/prepare_fixture.py <new-dir> --workspace <isolated-workspace> --practice-filter`; run the fixture, compatibility and pack validators. See the acceptance READMEs for workspace/path contract.
