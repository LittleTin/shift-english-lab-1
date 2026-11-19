#!/usr/bin/env python3
"""Compose only the five approved SHIFT listening overlays on a pinned ref."""
import argparse,hashlib,io,json,os,shutil,subprocess,sys,tarfile
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
PIN='fa6e3f8fa86a6b8f701dc4574db32bdbdc35cb01'
OLD='043b91761f63062708d70f7cda3a6b2046cd4cf9'
TUPLES={'test-01':(('Q098-100',()),),'test-02':(('Q013-Q014-Q016',(13,14,16)),('Q019',(19,)),('Q044-046',())),'test-03':(('Q095-097',()),)}
NUMS={'test-01':(98,99,100),'test-02':(13,14,16,19,44,45,46),'test-03':(95,96,97)}
ROOT='qa-checkpoints/approved-overlays'
HISTORY=('legacyQuestions','previousListeningPlan','alternateListeningPlans')
def req(ok,note):
 if not ok:raise ValueError(note)
def digest(b):return hashlib.sha256(b).hexdigest()
def read(f):return json.loads(f.read_bytes())
def tick(x):return int((Decimal(str(x))*100000).to_integral_value(rounding=ROUND_HALF_UP))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 req(not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE'),'Overlay assertions must be enabled')
 out=a.out.resolve(); repo=a.repo.resolve(); req(not out.exists() and not out.is_relative_to(repo),'Output must be absent and outside repo')
 def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
 req(git('rev-parse',PIN).decode().strip()==PIN,'Missing exact ref')
 req(git('rev-parse',OLD).decode().strip()==OLD,'Missing exact old deployed ref')
 out.mkdir(parents=True); source=out/'pinned';source.mkdir(); stage=out/'site';stage.mkdir(); scratch=out/'intermediate';scratch.mkdir()
 files=git('archive',PIN,'audio','assets','data',ROOT,'qa-checkpoints/verified-items','qa-checkpoints/difficulty','qa-checkpoints/exam-layout/reconcile','qa-checkpoints/exam-layout/difficulty','qa-checkpoints/exam-layout/layout.py','tools')
 with tarfile.open(fileobj=io.BytesIO(files),mode='r:') as t:t.extractall(source,filter='data')
 for f in ('audio','assets'): shutil.copytree(source/f,stage/f,copy_function=os.link)
 (stage/'data').mkdir()
 for n in ('reconcile','difficulty'):
  sys.path.insert(0,str(source/'qa-checkpoints/exam-layout'/n))
 sys.path.insert(0,str(source/'qa-checkpoints/exam-layout'))
 from reconcile import want_audio,check_audio,rel
 from difficulty_gate import check
 from layout import js_pack
 from reconcile import dig
 proof={'status':'offline-scratch-proof-not-a-release','workRef':PIN,'priorDeploymentRef':OLD,'exams':{}}
 def wave_sha(path,kind=None):return digest(rel(source,path,kind).read_bytes())
 for exam,overlays in TUPLES.items():
  raw=source/'data'/f'{exam}.json'; rawhash=digest(raw.read_bytes()); before=read(raw); old=git('show',f'{OLD}:data/{exam}.json')
  old_sha=digest(old); compiled=raw; steps=[]
  for tag,select in overlays:
   new=scratch/f'{exam}-{tag}.json'; ap=source/ROOT/f'{exam}-{tag}'/'apply.py'
   run=subprocess.run([sys.executable,str(ap),'--input',str(compiled),'--output',str(new),'--assets',str(source),*(['--select',*(str(n) for n in select)] if select else [])],check=True,capture_output=True,text=True)
   steps.append({'overlay':tag,'packSha256':digest(new.read_bytes()),'listeningPlanCanonicalSha256':dig(read(new)['listeningPlan'])}); compiled=new
  final=read(compiled); frames=final['listeningPlan']['frames']
  req(set(final)==set(before) and all(final[key]==before[key] for key in final if key not in ('questions','groups','listeningPlan')),f'{exam} metadata/history drift')
  for ident,(q,q0) in enumerate(zip(final['questions'],before['questions']),1):
   req(q['number']==q0['number']==ident and (ident in NUMS[exam] or q==q0),f'{exam} unapproved question drift')
  req(len(final['questions'])==200 and sum(g['part']<=4 for g in final['groups'])==54 and len(frames)==284,f'{exam} layout drift')
  req(sum(f['role']=='answer' for f in frames)==100 and tick(frames[-1]['at'])+tick(frames[-1]['duration'])==270000000,f'{exam} timeline')
  groups={g['id']:g for g in final['groups']}; active={q['number']:q for q in final['questions']}; items={}
  known_group_ids={active[n]['groupId'] for n in NUMS[exam]}|{before['questions'][n-1]['groupId'] for n in NUMS[exam]}
  req([g for g in final['groups'] if g['id'] not in known_group_ids]==[g for g in before['groups'] if g['id'] not in known_group_ids],f'{exam} unapproved group drift')
  for num in NUMS[exam]:
   q=active[num]; group=groups[q['groupId']]
   e=read(source/f'qa-checkpoints/verified-items/{exam}/Q{num:03}.json'); de=read(source/f'qa-checkpoints/difficulty/{exam}/Q{num:03}.json')
   req(e['status']=='verified-item-not-published' and e['activeQuestion']==q and e['group']==group,f'{exam} Q{num} active checkpoint drift')
   if group.get('image'):req(wave_sha(group['image'],'assets')==e['imageSha256'],f'{exam} Q{num} graphic association')
   has=any(row.get('mode')=='cue' for row in e['audio'])
   association=check_audio(e,want_audio(final,q,group,has_cue=has),wave_sha)
   items[str(num)]={'id':q['id'],'groupId':group['id'],'level':check(de,exam,q,group),'reviewedRoles':association}
  (stage/'data'/f'{exam}.json').write_bytes(compiled.read_bytes())
  (stage/'data'/f'{exam}.js').write_text(js_pack(final))
  req(digest(raw.read_bytes())==rawhash and digest(git('show',f'{OLD}:data/{exam}.json'))==old_sha,f'{exam} raw/prior pack changed')
  proof['exams'][exam]={'rawSha256':rawhash,'priorGitPackSha256':old_sha,'preservedHistoryCanonicalSha256':{key:dig(final.get(key)) for key in HISTORY},'steps':steps,'items':items}
 validator=subprocess.run([sys.executable,str(source/'tools/validate_exam.py'),'--site',str(stage)],capture_output=True,text=True)
 req(validator.returncode==0,validator.stderr+validator.stdout)
 proof['validation']=validator.stdout
 (out/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print(validator.stdout,end='')
 print('PASS: 13 exact verified item, media and difficulty association checks; all history fields preserved; immutable prior Git pack hashes unchanged.')
if __name__=='__main__':main()
