# SHIFT synthetic same-origin browser preflight

**Local QA only. Do not deploy this directory, its static output, or any of its
synthetic version/interval metadata.** Nothing here uploads, pushes, or accesses
the production site. The fixture is derived from the exact three-exam media
proof staged in `shift-media-migration/acceptance/rebuilt` and the matching staged
shell, not from fully reviewed or accepted questions. Hashes bind this snapshot.

## Build and preflight

Use Python 3.11+ from the shared workspace parent, and choose an unused output:

```sh
D=shift-browser-preflight
python3 "$D/prepare_fixture.py" "$D/fixture-local"
python3 "$D/test_fixture.py" "$D/fixture-local"
python3 shift-qa/tools/validate_exam.py --site "$D/fixture-local/site"
node --check "$D/browser-smoke.cjs"
```

The builder verifies current pack/media bytes unchanged and copies only the
ancillary files referenced by the staged shell, including the unscored
formal-example SVG, three pages, the fourteen local voice previews and guide
dependencies. It applies the completed-retirement and resume-only code in this
isolated fixture. The historical question pack and audio assets come from the
existing local snapshot of exact prior commit `043b91761…` (1.4.1). Identical media
overlaps share paths; differing overlaps block the build. The synthetic 1.4.2
stamp distinguishes the two content editions **in tests only**; this is not a
suggested release version. No mock answer keys: the old Test01 Q1 key is A and
the active old test IDs are the entire actual prior list, not just a retired Q1
patched into a list of new IDs.

The prepared artifact created on this executor contains 1,077 static files
(558,569,750 bytes), with receipt SHA-256
`ee7fbc987c671864e547e3cf1ea01e0fa148701a40dfe05f02122217e544b6db`.
It includes synthetic archival media, not an editable authoring tree. The receipt
is outside the served site and is bound to the HTTP fixture identity; copied
assets were rehashed before the transport tests.

## Real browser requires another compatible executor

In the **same working network namespace as the browser**, run:

```sh
python3 "$D/serve_fixture.py" "$D/fixture-local" --port 8769
# In another process in the same executor:
HEADED=1 node "$D/browser-smoke.cjs" http://127.0.0.1:8769/ "$D/fixture-local"
# For quick coverage of one exam (the three general/history cases still run):
TEST_ID=test-01 HEADED=1 node "$D/browser-smoke.cjs" http://127.0.0.1:8769/ "$D/fixture-local"
```

Set `CHROMIUM_BIN` only for an existing trusted Chromium installed at a different
path. The server binds only to IPv4 loopback, has no listing/write endpoints,
and restricts static routes to the exact receipt paths. It serves byte ranges
so original MP3 offsets and current WAV loads can be tested realistically.
The harness refuses non-loopback or mismatched fixture identity and blocks
browser requests to another origin. No external preview or tunnel is needed
when runner, HTTP server, and browser actually share the executor.

The harness uses real browser audio events and IndexedDB (not mocked timers or
visibility), distinguishes repeated media sources by new playback events and
frame starts, checks actual paused timer and offset, next group and reload,
renders quiz artwork at phone-size viewport, and tests no early answer reveal.
A synthetic near-end listening session checks the real last-frame transition
to 75-minute reading, score calculation and answer review/export without
waiting a full formal exam. Synthetic backup records test retired score/note
preservation, the exact old question image and MP3 start/offset, and refusal to
guess an earlier unknown epoch without changing stored progress. All UI cases
use a new browser context. Exit 2 means true tab visibility was not observed,
not a pass; retry headed. Exit 1 means another test or environment failed.

### What is and is not verified

- Manifest and actual localhost transport tests passed on this executor:
  identity, same-origin pages and scripts, Unicode routes, original/current
  media GET/HEAD/valid byte ranges and invalid-range/traversal refusal.
- Existing structural validator rerun on composed fixture: each exam 200 active
  questions, 54 listening groups, 284 frames, 2,700 seconds, zero embedded
  legacy IDs; 714 distinct ranged media assets probed.
- Node syntax checks passed for the harness and composed app/catalog. Syntax
  does not prove selectors or actual media behavior.
- No Chromium execution attempted in this extension: existing CLI and
  Playwright failures were caused by the executor's forbidden AF_UNIX singleton
  socket. The separate cloud browser cannot access this local loopback. A
  reachable HTTP preflight is not browser acceptance.
- Still required: real browser on a supported executor, actual mobile Safari
  and Chrome (or agreed supported targets; viewport emulation is not a phone),
  final question/media acceptance, real deployment interval or another
  verified continuation route, broader formal timing and complete exam runs,
  older cached/offline histories, production capacity/rollback and independent
  deployment checks. The synthetic known interval must never be substituted
  for the actual previous release interval. If no historical release can be
  identified, preserve unfinished data and refuse guessing.
- Keep only the harness/docs/scripts if checkpointing this prototype. Do not
  commit the generated fixture/rebuilt trees or publish the synthetic catalog.

## Optional candidate practice-filter proof
Build a separate fixture by adding `--practice-filter` to the prepare command
and using a fresh output path. This composes the independently tested
`practice-filter-proof/make_patch.py` with both history patches without editing
the source. The real-browser harness then also tests difficulty filtering across
all three candidate packs: hard filters must not select mismatched siblings,
entire groups remain together, and fewer eligible groups are allowed. This
additional browser scenario is not yet run. The residue of any build remains
synthetic and must not enter production.
