# Local SHIFT account-sync checks

Run in this directory (Node 22 and Python 3). No real project, account, email, or historical user data is needed. Test addresses ending in `.invalid` are fictional.

```sh
npm install --ignore-scripts --no-save --no-audit --no-fund --no-package-lock @electric-sql/pglite@0.3.15 jsdom@26.1.0 fake-indexeddb@6.2.4
node --test shift-sync.test.mjs
node test-local.mjs
python3 fixture.py ../.. --port 18765 --ttl 360 &
fixture_pid=$!
node integration.cjs; status=$?
kill "$fixture_pid"
exit "$status"
```

- Transport tests: secret-key rejection, synthetic auth, double request suppression on refresh, stale-scope responses, stable IDs and cursor ties.
- PostgreSQL tests: PGlite executes real PostgreSQL RLS on a disposable in-memory schema. The supplied synthetic Auth stubs are not for production.
- DOM/IndexedDB integration: exact app code + existing test packs in JSDOM with two isolated fake IndexedDB devices and a local HTTP fixture. Covers guest opt-in, wrong-question sync, account isolation, sign-in after reload without browser token storage, failed upload, offline recovery, and another same-account tab's durable pending session.
- These checks do not cover live hosted Supabase Auth/mail/CORS or native browser UI, including iOS. Complete those, plus origin review, before enabling real accounts.
