"""Layout invariants shared by the formal exam and release inventory gates."""
from collections import Counter, defaultdict
import re


def require_contiguous_groups(questions, check):
    """Group only active items; match navigation's question-number ordering."""
    by = defaultdict(list)
    for row in sorted(questions, key=lambda row: row['number']):
        if row.get('groupId') is not None:
            by[row['groupId']].append(row)
    for gid, members in by.items():
        numbers = [row['number'] for row in members]
        check(numbers == list(range(numbers[0], numbers[0] + len(numbers))),
              f'{gid}: non-consecutive active group question numbers: {numbers}')
    return by


def uses_source_document_count(test_id):
    match = re.fullmatch(r'test-([0-9]+)', test_id, re.IGNORECASE)
    return match is not None and int(match[1]) >= 10


def uses_physical_part7_layout(test_id):
    """The revised 10-passage source contract starts with Test 13."""
    match = re.fullmatch(r'test-([0-9]+)', test_id, re.IGNORECASE)
    return match is not None and int(match[1]) >= 13


def require_physical_part7_documents(source, check):
    """Check source metadata and the actual ordered bilingual rendered bodies."""
    gid = source['id']
    docs = source.get('documents')
    count = source.get('documentCount')
    check(isinstance(docs, list) and type(count) is int and count == len(docs)
          and count in (1, 2, 3),
          f'{gid}: documentCount must match the physical Part 7 source documents')
    ids = []
    for doc in docs:
        check(isinstance(doc, dict), f'{gid}: malformed Part 7 document')
        fields = ('id', 'title', 'titleZh', 'passage', 'passageZh')
        check(all(isinstance(doc.get(key), str) and doc[key].strip() for key in fields),
              f'{gid}: Part 7 document needs an ID, bilingual titles and bilingual bodies')
        ids.append(doc['id'])
    check(len(set(ids)) == count, f'{gid}: duplicate Part 7 document IDs')

    # The renderer may uppercase the title line. The ordered body text must
    # be exact; no extra or missing paragraphs are allowed.
    for title_key, body_key in (('title', 'passage'), ('titleZh', 'passageZh')):
        rendered = source.get(body_key)
        check(isinstance(rendered, str), f'{gid}: missing rendered {body_key}')
        check(len({d[body_key].strip() for d in docs}) == count,
              f'{gid}: duplicated {body_key} source document')
        remaining = rendered.strip()
        for d in docs:
            title, body = d[title_key].strip(), d[body_key].strip()
            line, sep, rest = remaining.partition('\n')
            if sep and line.strip().casefold() == title.casefold():
                remaining = rest.lstrip()
            else:
                check(count == 1, f'{gid}: {body_key} missing its ordered document title')
            check(remaining.startswith(body), f'{gid}: {body_key} does not match ordered source body')
            remainder = remaining[len(body):]
            check(not remainder or remainder.startswith('\n'),
                  f'{gid}: extra text after {body_key} source body')
            remaining = remainder.lstrip()
        check(not remaining, f'{gid}: extra text after final {body_key} source body')
    return count


def require_part7_layout(groups, by, document_count, check, require_ten_singles=False):
    """The caller supplies the count from the matched authoring group."""
    totals, multi = Counter(), Counter()
    singles = 0
    for group in groups:
        if group['part'] != 7:
            continue
        gid = group['id']
        count = document_count(group)
        check(type(count) is int and count in (1, 2, 3),
              f'{gid}: authoring record needs an integer documentCount of 1, 2 or 3')
        numbers = [row['number'] for row in by.get(gid, ())]
        allowed = range(147, 176) if count == 1 else range(176, 201)
        check(numbers and all(number in allowed for number in numbers),
              f'{gid}: {count}-document Part 7 group has positions {numbers}, '
              f'expected Q{allowed.start}–Q{allowed.stop - 1}')
        totals[count] += len(numbers)
        if count == 1 and require_ten_singles:
            check(2 <= len(numbers) <= 4, f'{gid}: each single passage needs 2–4 questions')
            singles += 1
        if count > 1:
            check(len(numbers) == 5, f'{gid}: each multiple passage group has 5 questions')
            multi[count] += 1
    check(totals == {1: 29, 2: 10, 3: 15}, f'wrong single/double/triple: {totals}')
    check(multi == {2: 2, 3: 3}, f'expected two double and three triple groups: {multi}')
    if require_ten_singles:
        check(singles == 10, f'expected ten single passage groups, got {singles}')
