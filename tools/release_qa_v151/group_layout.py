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


def require_part7_layout(groups, by, document_count, check):
    """The caller supplies the count from the matched authoring group."""
    totals, multi = Counter(), Counter()
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
        if count > 1:
            check(len(numbers) == 5, f'{gid}: each multiple passage group has 5 questions')
            multi[count] += 1
    check(totals == {1: 29, 2: 10, 3: 15}, f'wrong single/double/triple: {totals}')
    check(multi == {2: 2, 3: 3}, f'expected two double and three triple groups: {multi}')
