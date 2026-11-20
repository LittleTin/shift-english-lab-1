import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';

// In memory, no network, account, credentials, or user data.
const db = new PGlite();
try {
  console.log((await db.query('SELECT version() AS version')).rows[0].version);
  for (const filename of ['000_synthetic_bootstrap.sql', '../../supabase/migrations/20261120000000_shift_completed_sessions.sql', '002_synthetic_rls_test.sql']) {
    const results = await db.exec(await readFile(new URL(filename, import.meta.url), 'utf8'));
    for (const r of results) for (const row of (r.rows ?? [])) if (row.result) console.log(row.result);
    console.log('OK', filename);
  }
} catch (error) {
  console.error(error.code ?? '', error.message, error.detail ?? '', error.where ?? '');
  process.exitCode = 1;
} finally {
  await db.close();
}
