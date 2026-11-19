# Next difficulty tranche, pinned work candidate 5caabdb55aa0faca2ce7dc76bb33723c515a9c42

All counts in F/I/A order (foundation/intermediate/advanced). Source: exact-number `difficulty_gate.report` against archived `qa-checkpoints/verified-items` and `qa-checkpoints/difficulty`; see `distribution.json`. Group eligibility counts include standalone questions as units. None of the six sections is ready: reading lacks a medium plurality in every exam and Test03 also lacks even one whole advanced-eligible unit; listening still has holds and no complete advanced unit.

| Exam | Section | Reviewed F/I/A | Filter-eligible complete questions | Complete selectable units | Unverified |
|---|---|---|---|---|---:|
| 01 | Listening | 50/16/1 | 33/7/0 | 25/7/0 | 33 |
| 01 | Reading | 68/28/4 | 35/12/3 | 28/8/1 | 0 |
| 02 | Listening | 49/15/1 | 34/8/0 | 22/6/0 | 35 |
| 02 | Reading | 65/23/12 | 42/5/8 | 30/5/2 | 0 |
| 03 | Listening | 46/34/3 | 22/14/0 | 16/14/0 | 17 |
| 03 | Reading | 63/34/3 | 26/13/0 | 24/10/0 | 0 |

515 reviewed, 85 listening holds, no identity/evidence errors. The site's smallest target is 10; result under 10 is not itself failure if scarcity is explained rather than padded. Endpoint distribution gate expects >=3 separately and >=3 filter-eligible endpoint questions; the ordinary medium-plurality requirement is still unmet. If only moving foundation to intermediate, the mathematical minimum is 21 (T01), 22 (T02), 15 (T03); this is not a reclassification target and does not account for the additional T03 advanced deficit. Do not pad.

## Recommended next three verified foundation rotations

All are complete text-only Part 7 groups, not in the current reserve index; keep current part, number and passage-type format. Preserve old originals and verified artifacts in reserve before replacement; new IDs/version for material changes, complete bilingual+blind review. New passages should be meaningfully original, not update dates or obscure language.

1. Test01 Q159–161 `t01-r-p7-05` (manufacturing, Quality hold notice): make a fully intermediate manufacturing lot-disposition notice from a different scenario (cosmetic-only vs traceability hold, rework/reinspection vs disposition, cutoff and responsible team); solve from paired conditions rather than line-matching. Keep manufacturing coverage and increase T01 intermediate selectable from 12 to 15 without adding media. Alternative within same exam is Q162–164 factory visit (same manufacturing domain), if QA-lot duplication elsewhere warrants avoiding it.
2. Test02 Q171–173 `t02-r-p7-09` (business, Meeting-room booking rules): make a fully intermediate different business notice, e.g. a hybrid-client demo room assignment with AV/accessibility or vendor entry restrictions; require interpreting a confirmation, inventory constraint and check-in grace period, without three variants of the same clue. T02 recently gained real advanced semiconductor Q147–149 and museum Q162–164; prioritize medium and retain manufacturing sample (Q150–152), handover (Q153–155), and supplier audit (Q196–200). Intermediate selectable moves 5→8, so later medium groups still needed.
3. Test03 Q151–152 `t03-g061` (daily, Community orchard advertisement): fully intermediate replacement keeping a varied everyday/workplace crossover, e.g. a cooperative repair/reuse outing with capacity and alternate contributions. Use distinct adjacent-clue inferences. Complement, don't substitute for resolving the independently reviewed advanced Cedar Q176–180 proposal; any group change must preserve old group/figure and same-ID history semantics or introduce new IDs with exact historical snapshots. Inventory-software Q149–150 is another possible wholly foundation, text-only group, but if used preserve systems/tech as the replacement domain.

Reproduce exact audit by exporting the pinned commit's `qa-checkpoints/verified-items`, `qa-checkpoints/difficulty`, and `question-reserve/index.json`; import `difficulty_gate` from `shift-media-migration/difficulty`. This measures offline adjudicated evidence, not browser usability or listening acceptance.
