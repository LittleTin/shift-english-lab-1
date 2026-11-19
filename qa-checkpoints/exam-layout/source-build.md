# SHIFT source-by-question build prototype

Choose the source root with `--source` (e.g. `assets/exams` in a finished migration). Authoring and browser data are different:

```
<source>/
  manifest.json                         # canonical bindings of runtime URL → file + size and SHA-256
  test-01/
    exam.json                           # ordered ID/file index and exam-level timing
    questions/Q001/question.json        # exactly one current question per directory
    questions/Q001/media.json            # media dependencies (paths relative to source)
    questions/Q001/media/…               # files exclusive to this question
    groups/<stable group ID>/group.json  # shared passage, graphics references and audio range
    groups/<stable group ID>/media/…     # group-only media files
    shared/media/…                       # banks used by multiple questions/groups
    archive/questions/<legacy ID>.json  # only with compatibility mode, not active items
  shared/media/…                         # cross-exam reuse, stored once
```

Use empty output directories. No web server or third-party packages are needed.

```sh
python3 layout.py split --site path/to/current-site --source path/to/new-source
python3 layout.py build --source path/to/new-source --site path/to/generated-assets
python3 path/to/current-site/tools/validate_exam.py --site path/to/generated-assets
```

The generated directory contains the original-format data/test-01..03 JSON/JS browser packs and precisely their referenced binary files at the same runtime URLs. Other application files such as catalog, app.js, CSS and index.html remain independent inputs to deployment; this prototype does not replace them. Don't track both a generated duplicate and editable source under the same authoring branch unless static deployment requires the generated outputs; do not hand-edit the generated JS.

Replace an existing media file at its canonical source path, then explicitly record that intended change:

```sh
python3 layout.py refresh-media --source path/to/new-source assets/graphics/t01-g039.svg
```

The build refuses edits with stale digests, source symlinks, unsafe paths, duplicate physical source paths, missing assets and malformed record placement. No audio is cut/re-encoded: shared audio keeps exact offsets and binary hashes. For a future per-question clip, provide a new clip and update its data/timeline together; name changes or new URL bindings require updating the canonical manifest.

The default split/build saves old questions separately from editable active questions, with exact legacy compatibility of the generated bundles. After validating that history is recoverable independently, `split --omit-legacy-questions` excludes old question records entirely from both the new editable layout and generated packs. The build also supports `--omit-legacy-questions` for preview from a compatibility-mode source. Neither flag removes historical audio plans required by the existing runtime; the front end's treatment of new and legacy results must be completed and verified before production use.

`python3 test_layout.py` exercises the real working checkout at `../shift-qa` and compares every default generated JSON/JS file byte-for-byte and all media hashes, checks clean paths, archives, question counts, and safe intentional media replacement.
