"""Small app-only composition check; does not require a quiz/media fixture."""
import argparse
from pathlib import Path
import shutil
import tempfile
from prepare_fixture import compose_app,sha

def test(root,app):
 original=sha(app)
 with tempfile.TemporaryDirectory(prefix='shift-backup-app-') as d:
    base=Path(d)
    for opt in (False,True):
        out=base/str(opt)
        target=out/'site/assets/app.js'
        target.parent.mkdir(parents=True)
        shutil.copyfile(app,target)
        proof=compose_app(root,out,target,practice_filter=True,backup_readonly=opt)
        assert ('backupReadonly' in proof)==opt
        if opt:
            assert proof['backupReadonly']['offlineRegressionsPassed']==8
            assert proof['backupReadonly']['testedAppSha256']==sha(target)
        else:
            assert 'async function backupSnapshot(' not in target.read_text()
    assert sha(app)==original

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__)
 p.add_argument('--workspace',required=True,type=Path)
 p.add_argument('--app',required=True,type=Path)
 a=p.parse_args()
 test(a.workspace.resolve(),a.app.resolve())
 print('PASS: small app composition, option off/on, 8 backup regressions, exact final-app SHA and unchanged input')
