# Authoring a SHIFT question pack

Use [the example pack](data/example-pack.json) as the starting format. Give your pack and each question/group distinct IDs, then add matching English content, Traditional Chinese answer explanations, options and vocabulary. For personal practice, use Data & Settings → Import question pack. The browser keeps imported question data; referenced media must still be present in the local site folder.

All published and future audio uses **Ogg Opus** (.ogg; MIME type audio/ogg). Use relative paths below audio/ or assets/ and keep media separate from the JSON. The project uses 48 kHz Opus at 56 kbps mono or 96 kbps stereo, constrained VBR. True Opus bytes are required; renaming another format is not conversion. Verify all spoken text, exported audio lengths and clip boundaries, images, and native playback before publication. A verified raw hash may be retained as evidence, but the web package should not contain a redundant raw master.

Use unique IDs for revised items with a change in meaning or correct answer. Keep authoring archives separate from the active quiz bank. The developer repository contains the authoring and release validation tools; those tools and archives are not required to open this runtime.

### Stable question UUIDs

The UI displays a reproducible UUIDv5 for each question, in practice, formal tests and answer review. It is computed from the existing exact, case-sensitive `question.id` using the fixed namespace `fa3963cb-8585-4191-a84e-08f061ecd026`. Never change this namespace or reuse a retired question ID for a different question. Grouped questions each have their own UUID. This is display-only: retain the original IDs in question packs, answer history, bookmarks, notes and unfinished sessions. No extra UUID field is required when authoring future packs.

To trace a reported UUID in the repository's published packs, run from its root (replace UUID):
```sh
node -e 'const uuid=require("./assets/question-uuid.js"),target=process.argv[1].toLowerCase();for(const path of process.argv.slice(2)){const pack=require("./"+path);for(const q of pack.questions)if(uuid(q.id)===target)console.log(path,pack.testId,"Q"+q.number,q.id,q.groupId||"no group")}' UUID data/test-*.json
```
