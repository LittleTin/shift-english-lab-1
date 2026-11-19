# Resume-only immutable compatibility snapshot (prototype)

This is separate from the retired **completed result** patch. No production
release has been changed. Browser acceptance remains required.

## Mechanism

- Build a resume-only snapshot from the exact publicly deployed previous Git
  commit after verifying the deployment's real interval and versions.
  `write_snapshot.py` extracts that release's 200 current question records per
  exam (already-retired legacy copies inside that release are excluded), group
  content, answer keys, audio plans and every old media asset at its original
  relative URL. The generated files have a separate namespace in
  `data/resume/v<version>/` and are not listed as active tests.
- Retain the old audio routes, checking byte equality wherever they overlap a
  current asset. Merge the overlay's `catalogEntries` into the future catalog's
  `resumeSnapshots`. Do not publish `resume-overlay-manifest.json`; it is build
  evidence. Set the newly released catalog and every visible version label to
  the new version.
- The proof patch pins the original snapshot in a separate session-only map
  when a saved in-progress test comes from its verified previous period. Quiz
  assets, answered IDs, original scoring and formal playback frame/offset use
  that map. It never registers snapshot questions in the active question pool.
  New attempts store the current content version; active application packs
  stay active, and imported packs keep their preexisting behavior.
- Existing persisted sessions lack explicit content version; the actual
  confirmed same-origin deployment interval is essential. If it cannot be
  verified, or no exact saved ID/option is available, preserve and notify rather
  than guessing, relabeling IDs, clearing, or regrading. Old sessions from before
  the audited lower boundary need another separately proven snapshot/recovery
  route. Older downloadable ZIP origins or cached pages not attributable to the
  verified release require separate analysis, not a widened guessed interval.
- After a resumed session completes, persist original answer, selected answer
  and grade. Combine with the existing retired-result patch to display saved
  historical details when old question text has been discontinued. A retirement
  must use a new ID when question semantics or the answer key changes.
- Generate a fresh patch against the actual release candidate:
  `python3 make_patch.py <app.js> <scratch-app.js> --patch resume-compat.patch`;
  the included diff uses the working migration fixture as its base. The source
  guards reject version drift. Use a production-appropriate controlled process
  before editing deployments.

## Local verification

Fixture source: public prior candidate commit
`043b91761f63062708d70f7cda3a6b2046cd4cf9`, catalog 1.4.1.
The fixture below uses synthetic bounds **only in tests**; never publish them.

```sh
D=shift-media-migration/resume-compat
python3 "$D/make_patch.py" shift-qa/assets/app.js "$D/app-patched.js" --patch "$D/resume-compat.patch"
python3 "$D/write_snapshot.py" --repo shift-qa --commit 043b91761f63062708d70f7cda3a6b2046cd4cf9 \
  --version 1.4.1 --from-ms 1000000000000 --until-ms 2000000000000 --out "$D/fixture"
node --test "$D/test_compat.cjs"
```

Tests require the separate active-only three-exam build under
`shift-media-migration/acceptance/rebuilt`. Four Node app-logic tests passed:
actual prior deployed IDs and image/plan loaded outside the active 600-item pool;
saved answer/note/original score preserved; old frame and offset passed to
stub media; new attempt uses new WAV and corresponding offset; unknown epoch or
unavailable original ID refused with saved state unchanged. Node media stubs
do not count as true browser testing.

Size comparison with the actual three-exam rebuilt test tree: 304 original
asset paths total, 69,483,587 bytes before overlap; 55 paths (10,831,607 bytes)
not already in that tree; 0 contradictory content collisions. Three snapshot
scripts add 1,841,061 bytes. Verify actual candidate output and policy limits;
do not include duplicate editable source trees in published bytes.

Checkpoint code/docs only (not `app-patched.js`, `fixture/`, or audio).
