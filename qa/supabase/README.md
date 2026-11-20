# SHIFT account-sync checks
Use Node 22 and Python 3 in this directory. Only synthetic accounts ending in .invalid and a disposable local store are used. Nothing contacts hosted Supabase.

```sh
npm install --ignore-scripts --no-save --no-audit --no-fund --no-package-lock @electric-sql/pglite@0.3.15 jsdom@26.1.0 fake-indexeddb@6.2.4
node --test shift-sync.test.mjs
node test-local.mjs
python3 fixture.py ../.. --port 18765 --ttl 360 &
fixture_pid=$!
trap 'kill "$fixture_pid" 2>/dev/null || true' EXIT
node integration.cjs
```

- Transport: owner scope and token refresh; initial login and current-password validation; rejected/stale auth; ordered cursor and immutable writes.
- PGlite: disposable PostgreSQL RLS checks. Never apply the test Auth schema to a hosted project.
- Local HTTP + DOM/IndexedDB simulation: no guest upload by default; opt-in copy; finished results and wrong answers seen on another browser profile; account switching; wrong password and password rotation; no stored credentials; offline queue and retry.
- Native Chromium, when the approved VM supports it: install the pinned Playwright test dependency (`playwright@1.62.1`), start a fresh copy of the same loopback fixture before each run, and run `node browser-smoke.cjs` with Chromium installed at `/usr/bin/chromium`. The fixture's users and config do not become site defaults. The synthetic tests do not certify native iOS and do not replace the approved live Auth and origin checks.
