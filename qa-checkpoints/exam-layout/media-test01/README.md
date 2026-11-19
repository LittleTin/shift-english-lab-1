# Test 01 editable media migration proof

Run from the parent directory with Python, FFmpeg and FFprobe:

```sh
python3 shift-media-migration/migrate_exam01.py --site shift-qa --out shift-media-migration/proof
python3 shift-media-migration/check_proof.py --site shift-qa --out shift-media-migration/proof
python3 shift-qa/tools/validate_exam.py --site shift-media-migration/proof test-01.json
```

The output is initially nonexistent; the script stages and verifies into a temporary directory, then renames it into place. It is an overlay, not a complete deployable web site. The source checkout is read-only to this tool. Keep `proof/` and its rendered WAV/JSON/JS files out of the first code-only checkpoint.

- Each active unique-practice item and image gets a stable question slot below `audio/exams/test-01/questions/Q###/` and `assets/exams/test-01/questions/Q###/`, respectively. The separate roots preserve the existing validation contract. Shared scenes and audio go under `groups/<group-id>/`; narration goes under `common/`; an individually identified stem uses its question's folder. New layout source manifests can point to these slots. A future authoring checkout can omit both old material and build outputs only after safe-reference and old-history review.
- Each original bank is decoded to native-rate / native-channel signed 16-bit PCM once; exact rounded sample indices are sliced and written to WAV. The read-back WAV PCM, expected frame count, sample rate, channel count and width are validated per clip. A manifest records original asset hash, seconds, sample positions and PCM hash. The separate proof checker re-decodes representative independent source ranges with FFmpeg, validates every WAV against the manifest, and checks all copied images and retained paths byte-for-byte.
- Only active group `audio/audioStart/audioEnd/image` and active formal frame `src/start/end` change. Frame order, at/duration, IDs, question IDs, group metadata, edition, previous plans and alternate plans are unchanged. Old source files still referenced (including any legacy pictures) remain available at their existing URLs; unreferenced files from the checkout are untouched and are not copied into the overlay. This media proof deliberately does not strip archived question records; the separate retirement migration is needed for that.
- Test 01 runtime loads WAV already and accepts the media roots; no app source edits are made. Browser playback, seek/resume, latency of small files, and publish/repo size policy still require acceptance. Use the latest candidate before running a real migration: this tool does not reconcile last-minute question edits.
