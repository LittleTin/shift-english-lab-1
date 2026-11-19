#!/usr/bin/env python3
"""Scoped HQ work replay. Writes fresh candidate pack(s), never replaces inputs."""
from pathlib import Path
import re,argparse,json,copy,hashlib
D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def j(b):return json.loads(b)
def rd(p):return j(p.read_bytes())
def dig(o):return sha(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def dump(p):return (json.dumps(p,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
def wrapper(p):return ('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push('+json.dumps(p,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')+');\n').encode()
def asset(root,alt,rel,h):
 assert re.fullmatch(r'(audio|assets)/[A-Za-z0-9_./-]+',rel) and not {'','.','..'}.intersection(rel.split('/'))
 hits=[]
 for x in (root,alt):
  p=x/rel
  if p.is_file():
   assert p.resolve()==p.absolute() and sha(p.read_bytes())==h,rel
   hits.append(p)
 assert hits,rel
 return hits[0]
def apply(src,y,base,media):
 assert sha(src)==y['predecessorPackSha256']; o=j(src); r=copy.deepcopy(o)
 assert dig(o['listeningPlan'])==y['predecessorPlanSha256'] and o['testId']==y['exam']
 for name,rows in [('questions',r['questions']),('groups',r['groups']),('frames',r['listeningPlan']['frames'])]:
  for edit in y['replace'][name]:
   i,b=edit['index'],edit['beforeSha256'];assert dig(rows[i])==b
   rows[i]=edit['after']
 for k,v in y['metadata'].items():
  assert k in r and dig(r[k])==v['beforeSha256'];r[k]=v['after']
 if y['exam']=='test-02':
  assert [n+1 for n,(a,b) in enumerate(zip(o['questions'],r['questions'],strict=True)) if a!=b]==[74,75,76]
  assert all(q0['difficulty']==q1['difficulty'] for n,(q0,q1) in enumerate(zip(o['questions'],r['questions'],strict=True),1) if n not in [74,75,76])
  assert [x['id'] for x,g in zip(o['groups'],r['groups'],strict=True) if x!=g]==['t02-g046']
  for a,b in zip(o['listeningPlan']['frames'],r['listeningPlan']['frames'],strict=True):
   if a['groupId']!='t02-g046':assert a==b
 assert dig(r['listeningPlan'])==y['successorPlanSha256']
 assert len(r['questions'])==200 and len(r['listeningPlan']['frames'])==284
 assert sum(x['role']=='answer' for x in r['listeningPlan']['frames'])==100
 assert round((r['listeningPlan']['frames'][-1]['at']+r['listeningPlan']['frames'][-1]['duration'])*100000)==270000000
 for x,h in y['successorActiveAssets'].items():asset(base,media,x,h)
 b=dump(r);w=wrapper(r)
 assert sha(b)==y['successorPackSha256'] and sha(w)==y['successorWrapperSha256']
 return b,w
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base-site',required=True,type=Path);p.add_argument('--media',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--exam',required=True,choices=('test-01','test-02'))
 a=p.parse_args();s=rd(D/'overlay.json')['exams'][a.exam];f=a.base_site/'data'/f'{a.exam}.json';assert not a.out.exists(); b,w=apply(f.read_bytes(),s,a.base_site,a.media)
 path=a.out/'data';path.mkdir(parents=True);(path/f'{a.exam}.json').write_bytes(b);(path/f'{a.exam}.js').write_bytes(w)
 print(a.exam,s['successorPackSha256'],s['successorPlanSha256'])
