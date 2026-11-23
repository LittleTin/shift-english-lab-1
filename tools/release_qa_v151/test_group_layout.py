"""Regression tests through the formal validator and release inventory CLI."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import exam_lock as e
import test_exam_lock as fixtures
from test_exam_lock import AU, PIC, SV, w

TEST = 'test-10'
TOOLS = Path(__file__).resolve().parents[1]


class GroupLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.Synthetic.setUpClass()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source, self.site = self.root / 'authoring', self.root / 'site'
        w(self.site, AU, fixtures.Synthetic.fake_audio)
        for ref in (PIC, SV):
            w(self.site, ref, b'<svg/>')
        self.pack = fixtures.Synthetic.make(self)
        self.pack['testId'] = self.pack['listeningPlan']['testId'] = TEST
        q, g = self.pack['questions'], self.pack['groups']
        for item in q + g:
            item.update(testId=TEST, topic='business')
        for row in q:
            row['tags'] = []
        for row in g:
            row.update(title='Sample', titleZh='例題')
            if row["part"] <= 4:
                row["duration"] = 1
            if row['part'] == 7:
                n = int(row['id'].rsplit('-', 1)[1])
                row['documentCount'] = 1 if n < 176 else (2 if n < 186 else 3)
        for n in range(176, 201):
            start = 176 + 5 * ((n - 176) // 5)
            q[n - 1]['groupId'] = f'synthetic-group-{start}'
        active = {row.get('groupId') for row in q}
        self.pack['groups'] = [row for row in g if row['id'] in active]

    def emit(self, inventory):
        p = self.pack
        q = sorted(p['questions'], key=lambda row: row['number'])
        g = p['groups']
        if not inventory:
            p = {k:v for k,v in p.items() if k != 'listeningPlan'}
        w(self.site, f'data/{TEST}.json', p)
        w(self.site, f'data/{TEST}.js',
          b'window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('
          + e.canonical(p).strip() + b');\n')
        if self.source.exists():
            shutil.rmtree(self.source)
        qp = [f'{TEST}/questions/Q{row["number"]:03}/question.json' for row in q]
        gp = [f'{TEST}/groups/{row["id"]}/group.json' for row in g]
        for path, row in zip(qp + gp, q + g, strict=True):
            w(self.source, path, row)
        w(self.source, f'{TEST}/exam.json',
          dict(testId=TEST, records=dict(questions=qp, groups=gp),
               metadata={k:v for k,v in p.items() if k not in ('questions', 'groups')}))
        refs = sorted(set(e.media_refs(p)))
        for ref in refs:
            w(self.source, f'{TEST}/common/media/{ref}', (self.site / ref).read_bytes())
        w(self.source, f'{TEST}/common/media.json',
          dict(files=[dict(url=ref, source=f'{TEST}/common/media/{ref}') for ref in refs]))

    def assert_gates(self, rejection=None):
        for inventory in (False, True):
            with self.subTest(inventory=inventory):
                self.emit(inventory)
                if inventory:
                    cmd = [TOOLS/'release_qa_v151/exam_lock.py', 'snapshot',
                           '--source', self.source, '--site', self.site,
                           '--exam', TEST, '--out', self.root/'draft-inventory.json']
                else:
                    cmd = [TOOLS/'validate_exam.py', '--no-plan', '--authoring', self.source,
                           '--site', self.site, f'{TEST}.json']
                proc = subprocess.run([sys.executable, *map(str, cmd)],
                                      capture_output=True, text=True)
                if rejection:
                    self.assertNotEqual(proc.returncode, 0, proc.stdout)
                    self.assertIn(rejection, proc.stderr)
                else:
                    self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_valid_without_document_headers(self):
        self.assert_gates()

    def test_swap_positions_preserving_counts_and_group_size(self):
        q = self.pack['questions']
        q[179]['number'], q[184]['number'] = q[184]['number'], q[179]['number']
        q.sort(key=lambda row: row['number'])
        self.assert_gates('non-consecutive active group question numbers')

    def test_move_whole_multi_group_ahead_preserving_contiguity(self):
        q = self.pack['questions']
        for row in q[146:180]:
            n = row['number']
            row['number'] = n + 5 if n < 176 else n - 29
        q.sort(key=lambda row: row['number'])
        self.assert_gates('expected Q147–Q175')

    def test_missing_source_document_count_fails_closed(self):
        del next(row for row in self.pack['groups'] if row['part'] == 7)['documentCount']
        self.assert_gates('authoring record needs an integer documentCount')
