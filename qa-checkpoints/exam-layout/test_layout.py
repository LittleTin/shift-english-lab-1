"""Unit guards and real site integration for the SHIFT source/build prototype."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import layout


class LayoutTests(unittest.TestCase):
    site = Path(__file__).resolve().parent.parent / 'shift-qa'

    def test_safe_relative_paths(self):
        for bad in ['/audio/file.mp3', 'audio/../file.mp3', 'audio//file.mp3',
                    'audio/./file.mp3', r'audio\file.mp3', 'audio/%2E%2E/file.mp3',
                    '', 'https://x.invalid/f.mp3']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                layout.safe_rel(bad)
        self.assertEqual(str(layout.safe_rel('audio/formal-v2/test-01-01.mp3')),
                         'audio/formal-v2/test-01-01.mp3')

    def test_symlink_guard(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            p = Path(tmp)
            (p/'alias').symlink_to(p)
            with self.assertRaises(ValueError):
                layout.locate(p,'alias/test.json')

    def test_site_roundtrip_and_legacy_mode(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            root = Path(tmp)
            source, rebuilt, preview = (root/'source',root/'rebuilt',root/'preview')
            layout.split(self.site, source)
            layout.build(source, rebuilt)
            layout.build(source, preview, omit_legacy_questions=True)
            source_manifest = layout.load(source/'manifest.json')['media']
            self.assertEqual(len({x['source'] for x in source_manifest.values()}),
                             len(source_manifest))
            for item in source_manifest.values():
                self.assertTrue((source/item['source']).is_file())
            for name in layout.EXAMS:
                for ext in ('json','js'):
                    f = f'data/{name}.{ext}'
                    self.assertEqual((self.site/f).read_bytes(), (rebuilt/f).read_bytes(), f)
                original = layout.load(self.site/f'data/{name}.json')
                active = layout.load(preview/f'data/{name}.json')
                self.assertNotIn('legacyQuestions',active)
                self.assertEqual(original['questions'],active['questions'])
                if 'legacyQuestions' in original:
                    self.assertEqual(len(list((source/name/'archive/questions').glob('*.json'))),
                                     len(original['legacyQuestions']))
                manifests = list((source/name/'questions').glob('*/question.json'))
                self.assertEqual(len(manifests),200)
                self.assertEqual([q['id'] for q in original['questions']],
                                 [layout.load(p)['id'] for p in sorted(manifests)])
            for url,item in source_manifest.items():
                self.assertEqual(layout.file_hash(rebuilt/url),item['sha256'])
                self.assertEqual(layout.file_hash(self.site/url),item['sha256'])
            active_source = root/'active'
            layout.split(self.site, active_source, omit_legacy_questions=True)
            for name in layout.EXAMS:
                self.assertFalse((active_source/name/'archive/questions').exists())
                self.assertNotIn('legacyQuestions',layout.load(active_source/name/'exam.json')['records'])

            url = next(iter(source_manifest))
            physical = source/source_manifest[url]['source']
            physical.write_bytes(physical.read_bytes()+b'preview-only synthetic appended marker')
            with self.assertRaisesRegex(ValueError,'Invalid content for media'):
                layout.build(source,root/'stale')
            layout.refresh(source,[url])
            layout.build(source,root/'refreshed')
            self.assertEqual(physical.read_bytes(),(root/'refreshed'/url).read_bytes())
            physical.unlink()
            physical.symlink_to(self.site/url)
            with self.assertRaisesRegex(ValueError,'Symlink'):
                layout.refresh(source,[url])


if __name__=='__main__':
    unittest.main()
