# Three reading sections accepted offline; release remains blocked

Evidence checkpoint: `9047812299d67c6a69b4b5e7cb39c8544b180651` on the work branch.
Immutable deployed baseline remains `043b91761f63062708d70f7cda3a6b2046cd4cf9`.
This is a reproducible checkpoint, not a second specification or a deployed site.
Read root `SHIFT-SPEC.md` at the current stage branch before using it.

| Exam | Reading reviewed | Reading foundation / intermediate / advanced | Listening verified | Listening still awaiting audio evidence |
| --- | ---: | --- | ---: | ---: |
| Test 01 | 100 | 47 / 49 / 4 | 67 | 33 |
| Test 02 | 100 | 43 / 45 / 12 | 65 | 35 |
| Test 03 | 100 | 46 / 47 / 7 | 83 | 17 |

515 content and difficulty evidence records, no identity or media-evidence
errors, and all three reading mix checks pass. The 81 alternate reading items
are exact, independently adjudicated work-branch revisions, not additional
questions. All superseded originals are recoverable from the reserve and/or
historical source. Test03 Cedar new chart bytes match the prior reviewed chart,
while previously deployed Test03 Q177 remains the original text-only version.

Reproduce with the full Git objects for that stage checkpoint and the baseline
`8ab882d065cd33550ab8e694cc035c5135f1b146`. Use
`qa-checkpoints/exam-layout/reconcile/reconcile.py`, its rotation options,
`baseline-8ab882d-overrides-with-part5.json`, scoped verified/difficulty
ledgers and exact reviewed-media inputs. Exit 2 is expected while 85 audio
rows are unverified. Do not use `--out` to bypass the threshold. See
`ROTATIONS.md`, `STANDALONE.md`, and `GRAPHIC.md` for scope and fixture details.

The authoring smoke reproduced the complete 600 numbered folders, per-exam
`common` references and one exact Cedar SVG under its new group folder. Running
the standard structural validator on that isolated preflight found all three
draft sets at 200 questions, 54 listening groups, 284 formal frames and 2700 s.
That fixture intentionally retains unchanged base audio for not-yet-approved
items. It is not a published or publishable release artifact. Neither these
checks nor the offline historical replay validate real browser behavior.

Next: continue independent evidence for existing audio while drafting
prospective repairs separately, especially fully held groups whose reuse is
unlikely, and keep necessary editorial and capture fixes ahead of any F0
generation. Any newly timed source must later be checked in both practice and
formal audio roles, including unchanged siblings, timed stems, and the complete
2700 s plan. Real current/prior browser acceptance stays separate, using
`qa-checkpoints/exam-layout/acceptance/final-browser/`; the current tool is
syntax-checked but has not exercised a final site. Do not move `main` or the
Pages release until all original release gates pass.
