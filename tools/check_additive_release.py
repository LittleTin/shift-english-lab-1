#!/usr/bin/env python3
"""Guard a catalog-only/additive release. Review broader migrations separately."""
import argparse
import json
import re
import subprocess
import sys

PACK = re.compile(r"test-\d{2,}")
SHA = re.compile(r"[a-f0-9]{40}")

def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args])

def pin(repo, oid):
    if not SHA.fullmatch(oid) or git(repo, "rev-parse", "--verify", oid+"^{commit}").decode().strip() != oid:
        raise ValueError("Both revisions must be full commit IDs.")

def tree(repo, oid):
    out = {}
    for record in git(repo, "ls-tree", "-r", "-z", oid, "--", "data", "audio", "assets/scenes", "assets/graphics").split(b"\0"):
        if record:
            attrs, path = record.split(b"\t", 1)
            out[path.decode()] = tuple(attrs.decode().split())
    return out

def catalog(repo, oid):
    s = git(repo,"show",oid+":data/catalog.js").decode().strip()
    prefix = "window.SHIFT_CATALOG="
    if not s.startswith(prefix) or not s.endswith(";"):
        raise ValueError("Unrecognized catalog wrapper.")
    doc, consumed = json.JSONDecoder().raw_decode(s[len(prefix):])
    tail = s[len(prefix)+consumed:].strip()
    if tail not in (";", ";\nwindow.SHIFT_PACKS=window.SHIFT_PACKS||[];"):
        raise ValueError("Unrecognized catalog statements.")
    if not isinstance(doc.get("version"), str) or not doc["version"]:
        raise ValueError("Missing content version.")
    for e in doc["tests"]:
        if not PACK.fullmatch(e["id"]) or e["path"] != "data/"+e["id"]+".js":
            raise ValueError("Catalog entry has an unexpected ID or script path.")
    if len({e["id"] for e in doc["tests"]}) != len(doc["tests"]):
        raise ValueError("Duplicate catalog test IDs.")
    return doc

def audit(repo, base, candidate, expect_add):
    for oid in (base,candidate):
        pin(repo,oid)
    before, after = (catalog(repo,r) for r in (base,candidate))
    old, new = (tree(repo,r) for r in (base,candidate))
    errors=[]
    if before["version"] != after["version"]:
        errors.append("Content version changed: verify original snapshot restoration separately.")
    if before.get("resumeSnapshots") != after.get("resumeSnapshots"):
        errors.append("The saved-session snapshot registry changed.")
    prior, proposed = before["tests"], after["tests"]
    if proposed[:len(prior)] != prior:
        errors.append("Previously published catalog entries changed or were reordered.")
    if len(proposed)-len(prior) != expect_add:
        errors.append("Unexpected number of new catalog tests.")
    protected = {path: row for path,row in old.items() if path != "data/catalog.js"}
    changed = sorted(path for path,row in protected.items() if row != new.get(path))
    if changed:
        errors.append("Existing protected files changed or disappeared: " + ", ".join(changed))
    added = [e["id"] for e in proposed[len(prior):]]
    for id in added:
        for suffix in (".js",".json",".lock.json"):
            path="data/"+id+suffix
            row=new.get(path)
            if not row or row[0] != "100644" or row[1] != "blob" or path in old:
                errors.append("New catalog test lacks new regular file: "+path)
    return dict(base=base,candidate=candidate,contentVersion=after["version"],priorTests=len(prior),
                protectedFiles=len(protected),added=added,errors=errors,passed=not errors,
                scope="Git tree only; not proof of media decode, question quality, or native resume.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo")
    p.add_argument("base")
    p.add_argument("candidate")
    p.add_argument("--expect-add",type=int,default=1)
    a=p.parse_args()
    if a.expect_add<0:
        p.error("--expect-add must be nonnegative")
    try:
        out=audit(a.repo,a.base,a.candidate,a.expect_add)
    except (ValueError,KeyError,TypeError,subprocess.CalledProcessError) as e:
        print(str(e),file=sys.stderr)
        return 2
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if out["passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
