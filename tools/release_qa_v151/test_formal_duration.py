"""Sample-exact checks for legacy and variable-length formal listening plans."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import exam_lock as lock
from continuous_contract import MAX_SAMPLES, RATE, geometry, timeline
import test_group_layout as fixtures

TEST = 'test-10'


def make_plan(total, sample_fields=True):
    gids = ('g001', 'g002')
    splits = (total // 2, total - total // 2)
    frames, media = [], {}
    at = 0
    for gid, size in zip(gids, splits, strict=True):
        frames.append(dict(at=at / RATE, duration=size / RATE, groupId=gid,
                           role='gap', kind='silence'))
        media[gid] = dict(src=f'audio/formal-groups/{TEST}/{gid}.ogg', duration=size / RATE)
        if sample_fields:
            media[gid]['totalSamples'] = size
        at += size
    plan = dict(duration=total / RATE, frames=frames, groupAudio=media)
    if sample_fields:
        plan.update(sampleRate=RATE, totalSamples=total)
    return plan


class Contract(unittest.TestCase):
    def test_legacy_without_sample_fields_and_shorter_complete_plans(self):
        for seconds in (2700, 3000, 3600, 4800):
            for fields in (False, True):
                with self.subTest(seconds=seconds, fields=fields):
                    p = make_plan(seconds * RATE, fields)
                    self.assertEqual(sum(g['size'] for g in geometry(p, TEST).values()), seconds * RATE)

    def test_sample_inexact_or_over_cap(self):
        for duration in (0, -1, float('nan'), float('inf'), True, 12.000001):
            with self.subTest(duration=duration):
                p = make_plan(12 * RATE)
                p['duration'] = duration
                with self.assertRaisesRegex(ValueError, '80 minutes|exact 48 kHz'):
                    timeline(p)
        with self.assertRaisesRegex(ValueError, 'at most 80 minutes'):
            geometry(make_plan(MAX_SAMPLES + 1), TEST)

    def test_present_metadata_must_match_including_type(self):
        for field, value in (('sampleRate', 44100), ('sampleRate', 48000.0),
                             ('totalSamples', 3000 * RATE - 1), ('totalSamples', True)):
            with self.subTest(field=field, value=value):
                p = make_plan(3000 * RATE)
                p[field] = value
                with self.assertRaisesRegex(ValueError, 'sample rate|totalSamples'):
                    geometry(p, TEST)
        p = make_plan(3000 * RATE)
        p['groupAudio']['g001']['totalSamples'] += 1
        with self.assertRaisesRegex(ValueError, 'group totalSamples'):
            geometry(p, TEST)

    def test_one_sample_gap_overlap_and_terminal_mismatch(self):
        for timing_key, offset in (('at', 1), ('at', -1), ('duration', -1), ('duration', 1)):
            with self.subTest(timing_key=timing_key, offset=offset):
                p = make_plan(3000 * RATE, sample_fields=False)
                p['frames'][-1][timing_key] += offset / RATE
                with self.assertRaisesRegex(ValueError, 'gap, overlap|frame coverage'):
                    geometry(p, TEST)

    def test_group_duration_is_checked_even_with_matching_sample_metadata(self):
        p = make_plan(3000 * RATE)
        p['groupAudio']['g001']['duration'] += 1 / RATE
        with self.assertRaisesRegex(ValueError, 'group duration'):
            geometry(p, TEST)

    def test_exact_published_test07_geometry_when_fixture_is_available(self):
        name = os.environ.get('SHIFT_TEST07_PACK')
        if not name:
            self.skipTest('set SHIFT_TEST07_PACK to the exact published Test 07 JSON')
        raw = Path(name).read_bytes()
        self.assertEqual(sha256(raw).hexdigest(),
                         '9fcfd9f4a137fc692f060fd299b66906e49f992ac9f300e84a11cf3a6bfe6d0f')
        pack = json.loads(raw)
        plan = pack['listeningPlan']
        gid_geometry = geometry(plan, 'test-07')
        self.assertEqual((len(gid_geometry), sum(g['size'] for g in gid_geometry.values())), (54, 144891449))
        self.assertEqual({gid: g['size'] for gid, g in gid_geometry.items()},
                         {gid: g['totalSamples'] for gid, g in plan['groupAudio'].items()})
        lock.validate_pack(pack, 'test-07')  # structure only, not inventory/lock/approved release
        changed = deepcopy(plan)
        changed['frames'][-1]['duration'] += 1 / RATE
        with self.assertRaisesRegex(ValueError, 'gap, overlap'):
            geometry(changed, 'test-07')

    def test_decode_roles_retain_guard_and_answer_checks(self):
        def inspect(pcm, role):
            mocked = [subprocess.CompletedProcess([], 0, b'1', b''),
                      subprocess.CompletedProcess([], 0, pcm, b'')]
            with patch.object(lock.subprocess, 'run', side_effect=mocked):
                return lock.inspect_continuous_decode(Path('fixture.ogg'), {'size': RATE, 'frames': [
                    dict(index=0, start=0, end=RATE, kind='silence', role=role)]})
        for role in ('answer', 'intro', 'gap'):
            with self.subTest(role=role):
                self.assertEqual(inspect(bytes(2 * RATE), role)['checks'][0][1], role)
                audio = bytearray(2 * RATE)
                audio[2000:2002] = (100).to_bytes(2, 'little')
                with self.assertRaisesRegex(lock.LockError, 'non-silent encoded'):
                    inspect(audio, role)
        with self.assertRaisesRegex(lock.LockError, 'unknown decoded silence purpose'):
            inspect(bytes(2 * RATE), 'direction')
        with self.assertRaisesRegex(lock.LockError, 'incorrect 48k sample count'):
            inspect(bytes(2 * RATE - 2), 'gap')


class ReleaseEntrypoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.GroupLayout.setUpClass()

    def setUp(self):
        fixtures.GroupLayout.setUp(self)

    def assemble(self, total):
        p = self.pack
        by = {}
        for row in p['questions'][:100]:
            by.setdefault(row['groupId'], []).append(row)
        frames = []
        cursor = 0

        def frame(group, kind, role, samples=RATE, question=None):
            nonlocal cursor
            row = dict(at=cursor / RATE, duration=samples / RATE, groupId=group['id'],
                       part=group['part'], kind=kind, role=role)
            if kind == 'audio':
                row.update(src=fixtures.AU, start=0, end=1)
            if question is not None:
                row['questionId'] = question['id']
            frames.append(row)
            cursor += samples

        prior = 0
        # Four directions, 54 passages, 69 spoken stems and two one-second guards.
        wait, remainder = divmod(total - (4 + 54 + 69 + 2) * RATE, 100)
        for group in p['groups']:
            gid, part = group['id'], group['part']
            if part > 4:
                continue
            if part != prior:
                frame(group, 'audio', 'direction')
                if part == 1:
                    frame(group, 'silence', 'intro')
                    frame(group, 'silence', 'gap')
                prior = part
            frame(group, 'audio', 'passage')
            for question in by[gid]:
                if part >= 3:
                    frame(group, 'audio', 'question', question=question)
                frame(group, 'silence', 'answer', wait + (question['number'] <= remainder), question)
        assert cursor == total
        p['listeningPlan'] = dict(testId=TEST, duration=total / RATE, sampleRate=RATE,
                                  totalSamples=total, frames=frames)

    def run_release(self, rejection=None):
        fixtures.GroupLayout.emit(self, True)
        for cmd in (
            [fixtures.TOOLS/'validate_exam.py', '--authoring', self.source,
             '--site', self.site, f'{TEST}.json'],
            [fixtures.TOOLS/'release_qa_v151/exam_lock.py', 'snapshot',
             '--source', self.source, '--site', self.site,
             '--exam', TEST, '--out', self.root/'draft.json'],
        ):
            with self.subTest(entrypoint=str(cmd[0])):
                proc = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True)
                if rejection:
                    self.assertNotEqual(proc.returncode, 0, proc.stdout)
                    if isinstance(rejection, tuple):
                        self.assertTrue(any(x in proc.stderr for x in rejection), proc.stderr)
                    else:
                        self.assertIn(rejection, proc.stderr)
                else:
                    self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_complete_non_2700_plan_at_exact_80m(self):
        self.assemble(MAX_SAMPLES)
        self.run_release()

    def test_one_sample_over_80m_blocked(self):
        self.assemble(MAX_SAMPLES + 1)
        self.run_release('at most 80 minutes')

    def test_non_answer_guards_cannot_claim_extra_answers(self):
        self.assemble(3000 * RATE)
        gap = next(f for f in self.pack['listeningPlan']['frames'] if f['role'] == 'gap')
        gap['questionId'] = self.pack['questions'][0]['id']
        self.run_release('non-answer silence may not claim an answer slot')

    def test_relabeling_answer_as_gap_cannot_hide_missing_slot(self):
        self.assemble(3000 * RATE)
        answer = next(f for f in self.pack['listeningPlan']['frames'] if f['role'] == 'answer')
        del answer['questionId']
        answer['role'] = 'gap'
        self.run_release(('answer slot coverage drift', 'passage/answer window mismatch'))
