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
        self.test_id = TEST
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source, self.site = self.root / 'authoring', self.root / 'site'
        w(self.site, AU, fixtures.Synthetic.fake_audio)
        for ref in (PIC, SV):
            w(self.site, ref, b'<svg/>')
        self.pack = fixtures.Synthetic.make(self)
        self.pack['testId'] = self.pack['listeningPlan']['testId'] = self.test_id
        q, g = self.pack['questions'], self.pack['groups']
        for item in q + g:
            item.update(testId=self.test_id, topic='business')
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
        w(self.site, f'data/{self.test_id}.json', p)
        w(self.site, f'data/{self.test_id}.js',
          b'window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('
          + e.canonical(p).strip() + b');\n')
        if self.source.exists():
            shutil.rmtree(self.source)
        qp = [f'{self.test_id}/questions/Q{row["number"]:03}/question.json' for row in q]
        gp = [f'{self.test_id}/groups/{row["id"]}/group.json' for row in g]
        for path, row in zip(qp + gp, q + g, strict=True):
            w(self.source, path, row)
        w(self.source, f'{self.test_id}/exam.json',
          dict(testId=self.test_id, records=dict(questions=qp, groups=gp),
               metadata={k:v for k,v in p.items() if k not in ('questions', 'groups')}))
        refs = sorted(set(e.media_refs(p)))
        for ref in refs:
            w(self.source, f'{self.test_id}/common/media/{ref}', (self.site / ref).read_bytes())
        w(self.source, f'{self.test_id}/common/media.json',
          dict(files=[dict(url=ref, source=f'{self.test_id}/common/media/{ref}') for ref in refs]))

    def assert_gates(self, rejection=None):
        for inventory in (False, True):
            with self.subTest(inventory=inventory):
                self.emit(inventory)
                if inventory:
                    cmd = [TOOLS/'release_qa_v151/exam_lock.py', 'snapshot',
                           '--source', self.source, '--site', self.site,
                           '--exam', self.test_id, '--out', self.root/'draft-inventory.json']
                else:
                    cmd = [TOOLS/'validate_exam.py', '--no-plan', '--authoring', self.source,
                           '--site', self.site, f'{self.test_id}.json']
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


    def physical_fixture(self):
        self.test_id = 'test-13'
        self.pack['testId'] = self.pack['listeningPlan']['testId'] = self.test_id
        q, g = self.pack['questions'], self.pack['groups']
        for item in q + g:
            item['testId'] = self.test_id
        starts = [147, 150, 153, 157, 159, 162, 165, 168, 171, 174, 176]
        for lo, hi in zip(starts, starts[1:]):
            for number in range(lo, hi):
                q[number - 1]['groupId'] = f'synthetic-group-{lo}'
        active = {row.get('groupId') for row in q}
        self.pack['groups'] = [row for row in g if row['id'] in active]
        for row in self.pack['groups']:
            if row['part'] != 7:
                continue
            count = row['documentCount']
            docs = [dict(id=f'doc{n}', title=f'Document {n} — Fixture',
                         titleZh=f'文件 {n}｜測試',
                         passage=f'Body of genuine Test 13 document {n}.',
                         passageZh=f'第 {n} 份測試文件的內文。') for n in range(1, count + 1)]
            row['documents'] = docs
            row['passage'] = '\n\n'.join(d['title'].upper() + '\n' + d['passage'] for d in docs)
            row['passageZh'] = '\n\n'.join(d['titleZh'] + '\n' + d['passageZh'] for d in docs)

    def test_test13_physical_bilingual_documents(self):
        self.physical_fixture()
        self.assert_gates()

    def test_test13_declared_count_cannot_hide_an_actual_document(self):
        self.physical_fixture()
        row = next(x for x in self.pack['groups'] if x['id'] == 'synthetic-group-176')
        row['documents'].append(dict(id='doc3', title='Third memo', titleZh='第三份備忘錄',
                                     passage='Different information.', passageZh='另一段資訊。'))
        self.assert_gates('documentCount must match the physical Part 7 source documents')

    def test_test13_chinese_order_must_match_the_document_order(self):
        self.physical_fixture()
        row = next(x for x in self.pack['groups'] if x['id'] == 'synthetic-group-176')
        row['passageZh'] = '\n\n'.join(d['titleZh'] + '\n' + d['passageZh']
                                       for d in reversed(row['documents']))
        self.assert_gates('passageZh missing its ordered document title')

    def test_test13_single_group_cannot_have_five_questions(self):
        self.physical_fixture()
        for number in range(159, 162):
            self.pack['questions'][number - 1]['groupId'] = 'synthetic-group-157'
        self.pack['groups'] = [row for row in self.pack['groups']
                               if row['id'] != 'synthetic-group-159']
        self.assert_gates('each single passage needs 2–4 questions')
