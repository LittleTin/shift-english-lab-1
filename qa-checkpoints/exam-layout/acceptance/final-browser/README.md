# Release browser acceptance addendum: Cedar, history, and real clients

This is a test plan, **not a pass**. Neither browser script is evidence against
the final artifact: `shift-browser-preflight/browser-smoke.cjs` enforces a
synthetic loopback receipt, and the migration smoke samples the first group and
an old Test01 Q1. Its old unfinished fixture grafts one old ID to new IDs;
never use that as proof of comparable Test03 history. The older harness can
warn about missing genuine tab visibility and still exit zero. Keep such a
run explicitly incomplete; the synthetic harness already exits 2 in that case.

## Bind a real artifact before running

1. Record immutable current candidate ref, selected publish mode, exact static
   receipt SHA/bytes, pack/catalog/app/script and Cedar image hashes. Verify
   staged HTTP responses match these bytes, including JSON vs JS pack content,
   correct URL base (a Pages project subpath if applicable), cache behavior and
   byte-range media. Never substitute the synthetic fixture for the candidate.
   Do not modify staging files to make a case pass. Use a local or approved
   isolated same-origin preview; no partial deployment to production.
2. Export exact prior 1.4.1 `data/test-03.json` from commit
   `043b91761f63062708d70f7cda3a6b2046cd4cf9`; SHA-256 is
   `849c26f1b903d3f89fbe88e39294caeb2386da2a1f8c2f7e4769b2e40a0d849d`.
   Pin prior deployment interval independently; the application's snapshot
   selector checks `startedAt ∈ [from,until)` and declared version if any.
   A Git commit time or fake interval is not evidence. Prefer an actual
   preserved old-profile backup where authorized; otherwise generate scoped
   test state from that exact old pack and evidenced timestamps. If no valid
   old interval, leave successful prior-version resume untested, test failure
   preserving data, and block the release acceptance. Do not invent epoch or
   combine archived and current question IDs.

## Test03 Cedar: one archived profile, one current profile

### A. Archived 1.4.1 in-progress **and** completed records

- Preserve/restore a backup independently of the new profile. In-progress
  fixture uses all 200 old IDs in their old order, Test03, formal exam version 2,
  phase reading, Q177 array index, original old start time inside the evidenced
  interval, remaining time, prior audio and answers. Include old Q176/C and
  Q177/D in selected answers; old group `t03-g069` has **no image**. Archive
  prior completed result with original date, scores, attempts including
  correct-key fields, a note/star, and at least one wrong item.
- Open candidate on that same origin, load old completed result before
  resuming. Check original totals/options/answer facts and saved note/star
  survive. When retired text is intentionally unavailable, show previous
  result and original stored key, not the current stem or misleading score.
  Check backup export retains original values for both completed and active
  histories. Do not claim that an archived ID's full explanation remains
  visible unless the screen actually shows the archived explanation.
- Resume the unfinished old session. Assert old group passage identity, all
  five old IDs in one group, Q176/C and Q177/D selected, learned scores not
  revealed in-progress, original English choices, **no**
  `.scored-graphic img`, no new-room-guide request from the archived quiz.
  Reload and resume; prove index/answers/timer stay anchored. Previous/Next or
  grid must keep 5 items together and cannot jump to listening. Submit and
  compare persisted new result's attempts to prior pack scoring: old Q176
  selected C is correct (new B), old Q177 D is correct (same key alone would
  not detect wrong passage) and untouched Q178 is recorded as unanswered.
  Check archived completed fixture is unchanged and other state preserved.
- Separate negative profile: unsupported/missing source or mismatched
  version. Expect explicitly blocked resume and unchanged stored question
  IDs, answers, timestamps, media offset and export. A fail-safe refusal is
  acceptable for truly unknown versions only, never a substitute for the
  positive known-prior case. A partially failed/missing archive is not a pass.

### B. Current Test03 Section Practice, mobile and desktop

- Fresh browser profile; Test03 Reading Section Practice, grid select Q177.
  The five and only five grouped IDs are current Q176–180; Q177 is
  `t03-q177-r2`. Confirm current published-to-preview image route is the
  canonical current path (not hardcoded old working filename), HTTP 200,
  SHA-256 `a1b4f915b2635ca9f7161da6665f77627669f2ddf9059e4387ccfde1f76d9264`
  if packing did not intentionally transform it, DOM image decodes and is
  readable at supported widths. Compare passage to current pack; Q177/D
  remains the correct option. Align chart table values to English fallback.
- Select Q176/C (current wrong), Q177/D (correct) and leave Q178 unanswered.
  Before submission and after clicking Next/Previous or reloading, check all
  quiz content remains English and there are no visible or hidden answer
  results, explanations, translations, rationales, color/checkmark hints,
  transcripts or answer-revealing controls in the quiz DOM. Pressed state
  indicates selection, not correctness. Static pack JSON necessarily
  contains answers; prohibit disclosure by UI, not network inspection.
- Press Submit & Score, then confirm. Verify current Q176/C is now wrong
  with key B while Q177/D is right; use exact current attempts and score
  count (e.g. 1/100 when just two chosen). Q178 is unanswered, review opens
  for all three statuses, and each shows exact EN + Traditional Chinese
  prompt/choices, full passage translation, answer evidence and 4 translated
  option explanations. Verify History and backup restore/export in another
  fresh profile preserve these facts and do not change old-profile results.

## Extended gate beyond Cedar

- Run on supported real desktop and iOS Safari/Android Chrome. A 390px Chromium
  viewport is not mobile acceptance. At default/large font and portrait,
  confirm no clipped controls or horizontal scroll, readable room chart at
  normal zoom with text equivalent, logical focus/tap targets, and grouped
  reading navigation. Record devices/versions, dimensions, image accessibility.
- Reuse native visibility and HTMLAudio probes but require PASS per engine,
  not warning-only. Formal: check 3-group per Part 1-4 representative sequence,
  introduction/unscored picture, group changes, Part 1/2 letters-only, actual
  Part 3/4 shared passage and spoken stems, close into 75-minute reading; run
  at least one full natural duration per required release coverage. On tab
  switch/app background lock, assert current media has actually stopped and
  displayed and stored timer do not count down. Foreground blocked autoplay
  must show Resume Listening and eventually start the same frame at saved
  offset, not replaying prior passage; reload and prove the same, then next
  frame/session progression exactly once. Record start/offset/section times.
  Repeat current WAV and prior archived supported MP3, nonzero range start.
  No fake event, set-current-time shortcut, or console mutation qualifies.
- In practice verify replay/seek and 0.75/1/1.25x; formal disables those,
  cannot revisit completed audio. On all three current exams, unfiltered
  section practice is exact named exam, 100 each; full test exactly 200.
  Check single-accent purity, difficulty and whole-group scarcity behavior
  with final populated packs, not a test fixture's synthetic difficulty.
- Verify each results screen displays listening and reading raw counts,
  estimates 5–495 each and 10–990 overall with clear unofficial label.
  Confirm all three pages show the exact final user-facing release version.
  Run final 600-item/data-location/difficulty gates separately. Record PASS,
  FAIL or NOT RUN per case with screenshot/console/media/time evidence against
  the same release fingerprint. Any required NOT RUN is not a release pass.

### Optional targeted desktop/viewport add-on

`cedar-smoke.cjs` was syntax-checked only. After final packaging and epoch
review, run (on the same permitted staging/execution surface) alongside the
other browser gates:

```sh
git -C shift-qa show 043b91761f63062708d70f7cda3a6b2046cd4cf9:data/test-03.json > previous-test-03.json
HEADED=1 node shift-release-browser-acceptance/cedar-smoke.cjs \
  '<approved isolated preview URL ending in />' <exact-static-site-dir> \
  previous-test-03.json reviewed-epoch.json
```

Epoch keys are `priorCommit`, `version`, `from`, `until` (both epoch ms), and
`source` (external corroborating evidence description). This file is not an
authority to infer dates; the script also checks the served catalog's entries
match the independently reviewed values. It refuses GitHub-hosting domains,
requires positive old-history resume, and byte-checks the served catalog,
current JSON and Cedar figure against the candidate artifacts. Remaining
cross-engine mobile/visibility and manual scenarios above are still mandatory.
