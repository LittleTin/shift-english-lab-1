# Authoring a SHIFT Question Pack

The site loads question packs as static files. Add or update a pack without editing the HTML or application code.

## Import or publish

1. Copy `data/example-pack.json` to a new file.
2. Choose a unique `testId` and prefix all question and group IDs with it.
3. Add the actual audio and images before validation. The pack tool does not generate or copy media.
4. To load a pack only for yourself, use **Data & Settings → Import question pack**. The pack stays in the current browser; its media must still exist in the site folder.
5. To publish a pack for all users, run the authoring tool from the site folder:

```sh
python3 tools/add_pack.py data/custom-003.json --check
python3 tools/add_pack.py data/custom-003.json --title "Technology Practice" --subtitle "Specifications and suppliers"
```

Windows users can substitute `py -3` for `python3`. The tool requires Python 3.9 or later, uses only the standard library, and supports `--site-dir` to specify another site root. It creates `data/<testId>.js` and updates `data/catalog.js`. In a static deployment, publish the catalogue, generated JS, and linked media together.

## Schema version 1

| Object | Required fields |
|---|---|
| Pack | `schemaVersion: 1`, `testId`, `groups`, `questions`; optional English `title` and `subtitle`. |
| Group | Unique `id`, matching `testId`, integer `part`, `topic`, `title`, `titleZh`, `passage`, `passageZh`. Listening also requires `audio`; Part 1 requires `image`. |
| Question | Unique `id`, matching `testId`, unique positive `number`, integer `part` (1–7), `groupId`, `topic`, `difficulty`, `tags`, `prompt`, `promptZh`, `options`, `answer`, `explanationZh`, `evidence`, and `vocabulary`. Only standalone Part 5 questions can omit the group. |
| Option | `id`, English `text`, Traditional Chinese `zh`, and `whyZh`. Use A–C in Part 2 and A–D elsewhere, with distinct options and one correct answer. |
| Vocabulary entry | `term`, `zh`, and `note`. Give at least one entry per question. |

Topic values: `technology`, `manufacturing`, `business`, `daily`.
Difficulty values: `foundation`, `intermediate`, `advanced`. The pack limit is 5,000 questions and 20 MiB of UTF-8 JSON. Use unique IDs across all packs. Use an alphanumeric initial character followed by up to 95 alphanumerics, dots, underscores, colons, or hyphens for question/group IDs. Pack IDs allow alphanumerics, underscores, or hyphens up to 64 characters.

## Media and language

- Use relative ASCII paths inside `audio/` or `assets/` (no URL, backslash, spaces, or traversal). Audio: MP3, WAV, OGG, M4A. Images: SVG, PNG, JPG, JPEG, WebP.
- Part 1 audio reads four statements; Part 2 reads the prompt plus three responses. Parts 3 and 4 share one passage within each group. Keep transcripts and any English prompts consistent with the audio. Attach required graphics with descriptive English `imageAlt`.
- Optional audio fields include duration in seconds, `audioStart`/`audioEnd` for a clip within a bank, and `audioSpeakers` containing official locale metadata. For authoring, `audioScript` and `turns` contain the spoken English source.
- Public-facing content before review must be English. Do not remove the `*Zh`, `zh`, and `whyZh` fields: they are needed for the answer review.
- The built-in formal exam validator is `python tools/validate_exam.py` and requires FFprobe. Standard question packs can be practice-only.

## Update without losing study history

The tool does not overwrite existing packs by default. For your own published pack, use the same `testId` and check first:

```sh
python3 tools/add_pack.py data/custom-003.json --replace --check
python3 tools/add_pack.py data/custom-003.json --replace
```

The built-in `test-01`, `test-02`, and `test-03` IDs are reserved. Keep question IDs stable for typos; use a new ID for changes to meaning or the correct answer and preserve old built-in questions for historical review. The catalogue and pack JS formats are data-only; the tool does not execute a pack while validating it. Before publishing large changes, export a study backup and keep a copy of the previous site revision.
