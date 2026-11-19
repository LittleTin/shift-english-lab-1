"""Read-only assertions on a local split/build with the rotated three-exam fixture."""
import hashlib
import json
from pathlib import Path
import sys

source=Path(sys.argv[1]); built=Path(sys.argv[2])
read=lambda root,path:json.loads((root/path).read_text())
manifest=read(source,'manifest.json')
for t in ('test-01','test-02','test-03'):
    assert (source/t/'common'/'media.json').is_file(),f'Exam common file unavailable: {t}'
    assert not (source/t/'shared').exists(),f'Old shared folder remains: {t}'
    exam=read(source,t+'/exam.json')
    assert len(exam['records']['questions'])==200
    for n in range(1,201):
        assert (source/t/'questions'/f'Q{n:03}'/'question.json').is_file(), (t,n)
    assert len(read(built,f'data/{t}.json')['questions'])==200
paths=set(i['source'] for i in manifest['media'].values())
assert any(p.startswith('common/media/') for p in paths)
assert not any(p.startswith('shared/') or '/shared/' in p for p in paths)
url='assets/graphics/t03-g069-room-guide.svg'
asset=manifest['media'][url]
assert asset['source'].startswith('test-03/groups/t03-g069-r2/media/')
assert asset['sha256']=='a1b4f915b2635ca9f7161da6665f77627669f2ddf9059e4387ccfde1f76d9264'
for p in (source/asset['source'],built/url):
    assert hashlib.sha256(p.read_bytes()).hexdigest()==asset['sha256']
for n in range(176,181):
    base=f'test-03/questions/Q{n:03}'
    q=read(source,base+'/question.json')
    assert q['groupId']=='t03-g069-r2'
    assert {'url':url,'source':asset['source']} in read(source,base+'/media.json')['files']
assert not (source/'question-reserve').exists() and not (built/'question-reserve').exists()
print('PASS: 600 number folders; per-exam common manifests; exact one-copy Cedar SVG in its rotated group; authoring only.')
