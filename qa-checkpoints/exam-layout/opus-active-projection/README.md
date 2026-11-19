# Active-release Ogg Opus projection

This is a local, non-public proof and repeatable pipeline. It converts only reachable active listening (formal timeline, practice clips) and all 14 existing accent samples. It omits pre-release resume snapshots and legacy-only pack fields from the release staging tree. Authoring evidence and reserve history stay outside the generated web site; the inputs are never modified or removed.

## Build and verify

Requires Python, NumPy, FFmpeg/FFprobe with libopus, and a known-good complete runtime tree. Use a new output directory. Point each optional --pack at the final approved source JSON and add any --media-root that provides uniquely named new source assets. Never reuse a relative path for different source bytes; the converter fails closed on conflicts. Run:

    OPENBLAS_NUM_THREADS=1 python project.py --runtime "$RUNTIME" --out "$OUTPUT"       --pack "$APPROVED_TEST_02" --media-root "$APPROVED_MEDIA"       --reuse "$EARLIER_PROOF"
    python check_ranges.py --proof "$OUTPUT"

Use only the generated site/ in the release directory (after approval), not the proof directory or source audio tree. Every audio object is true Ogg Opus at 48 kHz, using deterministic bitexact FFmpeg/libopus, constrained VBR at 56 kbps mono or 96 kbps stereo, 20 ms frames. The SHA-addressed target name names the source bytes, not the encoded-object hash: asset-report.json maintains both identities and the active paths/boundaries. Reused objects require identical source SHA, profile, encoder build, output SHA, and Opus page geometry. When changing codec settings, update the profile intentionally and start without reuse.

For new future material, keep only a private working source until the exact output is decoded and independently checked. Project with a new content-addressed path, verify matching total decoded samples, pre-skip and last granule, active timing windows, SHA, and listening semantics on the actual Opus version. Record source SHA as provenance; do not publish a duplicate raw master. Follow project retention instructions before discarding temporary sources. Never delete Git history or required authoring evidence.

The checker makes no padding/truncation concessions by default, validates source and decoded Opus sample duration, checks zero-lag PCM shape as a basic corruption guard, and leaves the 2,700-second exams, all point-in-time fields and graphs unchanged. Output is expected to return Content-Type audio/ogg and Accept-Ranges bytes. Our loopback-only HTTP proof checks HEAD, start/middle/end range bytes, and EOF 416 from an exact local server; it is not proof of the release host. The runtime probes native browser Ogg/Opus support, not user-agent strings. Real browser playback, network transport, release metadata, semantically verified latest packs, and publication authorization are distinct steps.

## Scoped delivery association

The canonical 600-row QA verification remains immutable. scoped-rebound/ contains 24 separately bound changed items, not a replacement for the entire raw/canonical ledger. association-proof.json identifies every verified row and corresponding active Opus group by exact hashes, plus the exact output hashes of every asset referenced by the changed scope. None of these artifacts asserts public/release readiness; Test01 and Test02 still require genuine medium expansions. The complete authored alternatives remain archived under the top-level question-reserve/ hierarchy and are not shipped.

HQ 56/96 is the project default; the earlier compact 40/64 experiment was a pilot only and is not offered as a published fallback. The exact decoded source/output sample totals must match; no padding or truncation; fractional decimal endpoints use nearest physical sample. Actual output packet coverage, waveform statistics, and local HTTP MIME/ranges are recorded. These numeric checks do not by themselves prove absence of a perceptible difference; actual listening/browser checks are separate. This transfer contains no converted runtime tree or raw render files. The encoded asset bindings point to the separate locally verified site output.
