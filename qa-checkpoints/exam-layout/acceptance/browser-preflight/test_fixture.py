from argparse import ArgumentParser
from contextlib import closing
from hashlib import sha256
from http.client import HTTPConnection
import json
from pathlib import Path
from threading import Thread
from urllib.parse import quote

from prepare_fixture import PRIOR_SHA, sha
from serve_fixture import make_server


def test_fixture(root):
    receipt=root/'fixture.json'
    original=receipt.read_bytes()
    m=json.loads(original)
    assert m['fixtureOnly'] and m['doNotDeploy']
    assert m['priorCommit']==PRIOR_SHA
    site=root/'site'
    for rel,info in m['files'].items():
        f=site/rel
        assert f.is_file() and not f.is_symlink()
        assert f.stat().st_size==info['size'] and sha(f)==info['sha256'],rel
    server=make_server(root,0)
    worker=Thread(target=server.serve_forever,daemon=True)
    worker.start()
    def req(ref, method='GET', headers=None):
        with closing(HTTPConnection('127.0.0.1',server.server_port,timeout=5)) as c:
            c.request(method,ref,headers=headers or {})
            r=c.getresponse()
            return r.status,dict(r.getheaders()),r.read()
    try:
        code,h,b=req('/__shift_fixture')
        assert code==200 and h['X-Shift-Fixture']==sha256(original).hexdigest()
        assert json.loads(b)['case']=='SHIFT_SYNTHETIC_LOCAL_ONLY'
        ref=list(m['activeDraftMajors'])[0]
        for f in ('index.html','使用說明.html','語音試聽.html','assets/app.js','data/catalog.js',
                  f'data/{ref}.js',m['oldResume']['entry']['path'],'assets/scenes/formal-example.svg'):
            code,h,b=req('/'+quote(f)+'?v='+m['syntheticVersion'])
            assert code==200 and sha256(b).hexdigest()==m['files'][f]['sha256'],f
        old=m['oldResume']['passage']['src']
        new=next(f for f in m['files'] if f.startswith(f'audio/exams/{ref}/common/') and f.endswith('.wav'))
        for f in (old,new):
            data=(site/f).read_bytes()
            code,h,b=req('/'+f,'HEAD')
            assert code==200 and not b and int(h['Content-Length'])==len(data)
            code,h,b=req('/'+f,headers={'Range':'bytes=64-127'})
            assert code==206 and h['Content-Range']==f'bytes 64-127/{len(data)}' and b==data[64:128]
            code,h,b=req('/'+f,headers={'Range':'bytes=-17'})
            assert code==206 and b==data[-17:]
            code,h,b=req('/'+f,headers={'Range':f'bytes={len(data)}-'})
            assert code==416 and not b
        assert req('/%2e%2e%2ffixture.json')[0]==400
        assert req('/fixture.json')[0]==404
        assert req('/assets/')[0]==400  # no directory listing
        print(f'PASS manifest bytes ({len(m["files"])} files), 3 pages and session scripts, original MP3/current WAV Range, loopback refusal checks.')
        print('Not a browser playback, UI, or publication pass.')
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=4)


if __name__=='__main__':
    a=ArgumentParser()
    a.add_argument('fixture',type=Path)
    test_fixture(a.parse_args().fixture.resolve())
