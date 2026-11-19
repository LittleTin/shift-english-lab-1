# Offline timing guard for finished replacement audio

Use only after an authorized F0 recording exists as an isolated, reviewed WAV.
This utility never synthesizes, listens, clears a hold, changes project files,
or deploys. The synthetic timing fixtures are silent and are not replacement
audio.

`draft(pack, audio_root, unit)` checks the original 100 answer windows and
exact 2700-second timeline; binds targeted old source SHA and exact source range
on each tracked mode; validates a new dedicated immutable file by SHA and
measured mono PCM WAV sample count; and returns an in-memory candidate and timing
proof. Never overwrite shared banks. Practice-only replacements leave formal
frames untouched. For a formal passage or numbered stem replacement, all
other groups and the two boundary anchors of the affected group stay fixed.
Only that group's answer silence absorbs the measured delta; if a supplied,
reviewed minimum answer duration would be violated, the guard refuses the
change. It never trims, stretches, or accelerates speech to fit.

Input `unit` has `testId`, `groupId`, an explicit `minAnswerSec` (formal only),
and a `changes` list. A change declares `mode` (`formal` or `practice`),
`role` (`passage`, or `question` for an independently recorded formal stem),
and `questionId` only for a formal question. Its `old` object is
`{path,sha256,start,end}` and its `new` object is
`{path,sha256,frames,sampleRate}` measured from the exact new local PCM file.
Use distinct audio paths. Formal and practice may point to the same new asset
only after the actual script, voices, ordering, and sample range are verified
equivalent; otherwise submit separate replacements. This lower-level timing
guard does not perform text/ID successor edits or carry over their evidence.

From the workspace root, run:
```sh
python3 -m unittest discover -s shift-media-migration/repair-timing -p 'test_*.py' -v
```

All six tests use a real draft Test02 timeline and synthetic local media, test
immutable surrounding ranges and group end, and reject stale source hashes,
unsafe in-place edits, altered sample counts, forbidden cue splices, and
overlong audio. Any real replacement still needs source-bound verbal,
translation, speaker, history, and actual browser QA, then complete release
gates. The test's answer-duration floor is not a project-wide specification.
