# SHIFT account sync v1

SHIFT remains a static GitHub Pages site. Keep the existing test catalog, quiz/answer formats and Opus media. The optional Account & Sync section is hidden until a public project URL and browser publishable key are configured.

## User behavior

- Guest practice, unfinished sessions, backups, and existing local data work without an account. Signing in opens that account's separate local workspace; it does not upload guest history.
- Sign-in uses a manually provisioned email and password. There is no public registration, sign-in email, or self-service password reset. New users should change their temporary password from Account & Sync after their first sign-in. This version keeps tokens in memory, not in browser storage or URLs. Closing or reloading the page requires signing in again. The account workspace remains on disk, available again only after sign-in in this app. An open signed-in tab can continue offline.
- Cloud sync covers completed session summaries plus every answer in those sessions; the wrong-question list is rebuilt from that history on each device. Notes, starred questions, files, custom packs, unfinished sessions, and preferences are local-only. Results are practice data, not certified scores.
- `Data & Settings → Copy Guest History` gives a separate confirmation before uploading eligible previous sessions. This copies, not moves. Incomplete or oversized records remain local; they aren't silently discarded. Account “Export Backup” remains available; replacing/deleting synced history is intentionally not offered in v1. Guest backup import remains available.
- Browser resends use the same stable key. A conflicting snapshot is not overwritten. Automatic retries after reconnect do not mean that a failed/delayed write succeeded.
- Browser storage is isolated by **origin**, not URL path. The public launch origin must not serve unrelated or untrusted scripts, including another GitHub Pages project on the same account host. Prefer a dedicated HTTPS origin controlled by the owner for public sign-in. Do not migrate the guest cache to a new origin silently; users can export in the original site and import as guests at the new origin if needed.

## Provision the Free pilot

1. In the owner's verified Supabase account, create a clearly named, dedicated **Free** project in Tokyo if available (Singapore if needed and approved). Confirm Free status; do not add a paid plan, payment method, or optional paid service. Keep database credentials in Supabase/operator storage, never in Git, URLs, browser config, or chat.
2. Apply **only** `supabase/migrations/20261120000000_shift_completed_sessions.sql` to the new project. Do not apply the synthetic test stubs. Verify anonymous requests are rejected and authenticated accounts can access only their rows. The browser key cannot bypass data policies. No admin, secret, or service-role key belongs in the frontend.
3. For the closed group, keep public signup and anonymous sign-in off. Leave Email enabled, disable magic links and email OTP, require the current password for password changes, and configure a minimum of 12 characters. Hidden or disabled settings cannot be replaced by browser validation. Keep email confirmation enabled. Provision only authorized learning identities through the project's Authentication → Users admin interface as confirmed accounts, not as Supabase organization members and not through public signup. Use unique temporary passwords supplied privately by the account administrator, never via a shared channel or this repository. Password changes run in the signed-in account; without a mail service, forgotten passwords are reset manually by the administrator after verifying identity. Check any optional Password Changed notification separately if enabling notices; do not use team membership as an email workaround.
4. Set `assets/shift-sync-config.js` to the verified project HTTPS origin and **publishable** key. Leave it blank on every other deployment. No changes to testing data, media, or website hosting. The dormant configuration is the rollback switch: disabling it stops new cloud traffic without altering existing data.
5. Before pointing regular visitors at the login, use isolated approved test identities to verify real password sign-in, password changes, and two-user isolation in the actual project, desktop and phone-width UI, two separate browser contexts, reconnect, logout/account switching, stale token, explicit guest-history transfer and no transfer before consent. Use synthetic exercise records, not existing user history. Check that the unchanged guest app and site still work. Validate the correct deployment and a usable opt-out. Do not treat local HTTP or SQL tests as proof that live Auth and CORS work.

## Data path and validation

One immutable account-owned row per submitted session includes the full result and per-question attempt snapshots. Supabase RLS authorizes SELECT/INSERT only for the JWT owner, and the security-invoker RPC distinguishes inserted, already_exists, and conflict. Direct admin access is not used by the website. App-side IndexedDB protects account queues locally, avoids losing completed records in normal cross-tab writes, and holds corrupt/oversized snapshots out of sync rather than discarding them. The cloud can hold the owner's asserted practice data, not verified grading evidence.

Official references:
- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Password sign-in](https://supabase.com/docs/reference/javascript/auth-signinwithpassword)
- [Password security](https://supabase.com/docs/guides/auth/password-security)
- [Manually provision an account](https://supabase.com/docs/reference/javascript/auth-admin-createuser)
- [SMTP restrictions and custom configuration](https://supabase.com/docs/guides/auth/auth-smtp)
- [API keys and privileges](https://supabase.com/docs/guides/api/api-keys)
- [Project regions](https://supabase.com/docs/guides/platform/regions)
