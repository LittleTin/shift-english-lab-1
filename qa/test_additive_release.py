import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

spec=importlib.util.spec_from_file_location("gate",Path(__file__).resolve().parents[1]/"tools"/"check_additive_release.py")
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

with tempfile.TemporaryDirectory() as local:
    repo=Path(local)
    def git(*args):
        return subprocess.check_output(["git","-C",local,*args],stderr=subprocess.PIPE).decode().strip()
    git("init","-q");git("config","user.name","Synthetic QA");git("config","user.email","qa@example.invalid")
    def write(path,content):
        p=repo/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
    def catalog(version="1.5.0",new=False,title="Original"):
        entries=[dict(id="test-01",path="data/test-01.js",title=title)]
        if new: entries.append(dict(id="test-02",path="data/test-02.js",title="Added"))
        write("data/catalog.js","window.SHIFT_CATALOG="+json.dumps(dict(version=version,tests=entries))+";\nwindow.SHIFT_PACKS=window.SHIFT_PACKS||[];\n")
    def commit(label):
        git("add","-A");git("commit","-qm",label);return git("rev-parse","HEAD")
    catalog();write("data/test-01.js","original");write("audio/existing.ogg","fixture")
    baseline=commit("original")
    catalog(new=True)
    for suffix in (".js",".json",".lock.json"): write("data/test-02"+suffix,"fixture")
    appended=commit("append")
    result=gate.audit(local,baseline,appended,1);assert result["passed"] and result["protectedFiles"]==2
    print("pass: preserves old objects and appends one test")
    write("data/test-01.js","changed");r=gate.audit(local,baseline,commit("change existing source"),1)
    assert not r["passed"] and "data/test-01.js" in str(r["errors"]);print("pass: old question content change rejected")
    git("checkout","-q","--detach",appended)
    (repo/"audio/existing.ogg").unlink();r=gate.audit(local,baseline,commit("delete existing audio"),1)
    assert not r["passed"] and "audio/existing.ogg" in str(r["errors"]);print("pass: disappearing old audio rejected")
    git("checkout","-q","--detach",appended)
    catalog(version="2.0.0",new=True);r=gate.audit(local,baseline,commit("bump content version"),1)
    assert not r["passed"] and "Content version changed" in str(r["errors"]);print("pass: content version bump held for compatibility migration")
    git("checkout","-q","--detach",appended)
    catalog(new=True,title="Modified");r=gate.audit(local,baseline,commit("edit old catalog entry"),1)
    assert not r["passed"] and "published catalog" in str(r["errors"]);print("pass: changed old catalog entry rejected")
    git("checkout","-q","--detach",appended)
    (repo/"data/test-02.lock.json").unlink();r=gate.audit(local,baseline,commit("remove new lock"),1)
    assert not r["passed"] and "test-02.lock.json" in str(r["errors"]);print("pass: missing new lock rejected")
