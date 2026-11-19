"""Prototype tests; proposed review rows synthesized locally, no approval claimed."""
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from rotation import Repo,EXAMS,GRAPHIC_KIND,check_site_and_ledger,dig,dump,media,rotate

DRAFT_REF='f05269f6f63f1a191950fa8995188ea9f83ac9a5'
REF='5caabdb55aa0faca2ce7dc76bb33723c515a9c42'
BASE='8ab882d065cd33550ab8e694cc035c5135f1b146'
PAST='043b91761f63062708d70f7cda3a6b2046cd4cf9'
T='test-03'; G='t03-g069'; NEW=G+'-r2'
META=f'qa-checkpoints/reconstructions/{T}/{G}.json'
HIST=f'qa-checkpoints/reconstructions/history/{T}/{G}.json'
PRE=f'question-reserve/{T}/{G}'
PACK='data/'+T+'.json'; NUMS=list(range(176,181))
OVERRIDES='qa-checkpoints/exam-layout/reconcile/baseline-8ab882d-overrides-six-rotations.json'

class Proxy(Repo):
    def __init__(self):super().__init__('shift-qa');self.add={}
    def read(self,r,p):
        return self.add[p] if r==REF and p in self.add else super().read(r,p)
    def git(self,*a):
        response=super().git(*a)
        if a[0]=='ls-tree' and a[-2]==REF:
            paths=[p for p in self.add if p.startswith('qa-checkpoints/reconstructions/') and p.encode() not in response.splitlines()]
            response+=''.join(p+'\n' for p in paths).encode()
        return response
    def put(self,path,obj):self.add[path]=dump(obj).encode()

def fixture():
    r=Proxy();draft=r.row(DRAFT_REF, 'qa-checkpoints/difficulty/drafts/test-03/Q176-180/history-versioned-draft.json')
    base={t:r.row(BASE,f'data/{t}.json') for t in EXAMS}
    idx=r.row(REF,'question-reserve/index.json')
    oldg=next(g for g in base[T]['groups'] if g['id']==G)
    oldqs=[q for q in base[T]['questions'] if q.get('groupId')==G]
    override=r.row(REF,OVERRIDES)
    asset=dict(runtimePath=draft['sourceChart']['path'],checkpointPath=draft['sourceChart']['stageCheckpointPath'],
               sha256=draft['sourceChart']['sha256'])
    candidateGroup=draft['group'];candidateGroup['id']=NEW
    candidateGroup['passageType']='double'
    provenance='39fc9f85732230e7ed8b6310d8bcd6e5d7d92faa'
    nr=[]; oldgwork=None; oldmanifest=[]; ev=[]
    for n,baseq,q in zip(NUMS,oldqs,draft['questions'],strict=True):
        v=f'qa-checkpoints/verified-items/{T}/Q{n}.json'
        then=r.read(provenance,v); previous=json.loads(then); oldq=previous['activeQuestion']; oldgwork=previous['group']; ev.append(v)
        qq=f'questions/Q{n}'
        r.add[f'{PRE}/{qq}/verification.json']=then;r.put(f'{PRE}/{qq}/question.json',oldq)
        oldmanifest.append(dict(number=n,questionId=oldq['id'],revision=oldq['revision'],answer=oldq['answer'],
           verificationPath=qq+'/verification.json',sourceEvidencePath=v,
           sourceEvidenceGitBlob=r.git('rev-parse',f'{provenance}:{v}').decode().strip(),
           sourceEvidenceSha256=hashlib.sha256(then).hexdigest()))
        if q['id']==oldq['id']:q['id']+='-r2';q['revision']+=1
        q['groupId']=NEW;nr.append(q)
        if baseq!=oldq:override[T+f'/Q{n}']={'observedSha256':dig(baseq),'verifiedSha256':dig(oldq)}
        r.put(v,dict(status='verified-item-not-published',scope='reading',checks='synthetic fixture only',
            activeQuestion=q,group=candidateGroup,originalQuestion=oldq,
            imageSha256=asset['sha256'],retiredSourceReference=f'{PRE}/{qq}/verification.json'))
    candidateGroup['passageType']=oldgwork['passageType']
    for v in ev:
       q=r.row(REF,v);q['group']=candidateGroup;r.put(v,q)
    override[T+'/'+G]={'observedSha256':dig(oldg),'verifiedSha256':dig(oldgwork)}
    r.put(f'{PRE}/group.json',oldgwork)
    status='reserved-inactive-in-work-candidate'
    r.put(f'{PRE}/manifest.json',dict(
       status=status,sourceTest=T,sourceGroupId=G,sourceQuestionNumbers=NUMS,
       sourceCommit=provenance,format='complete-single-svg-reading-group',media=[asset],notActiveHere=True,sourceStillActive=False,
       replacementGroupId=NEW,replacementQuestionIds=[q['id'] for q in nr],questions=oldmanifest))
    idx['groups'].append(dict(sourceTest=T,groupId=G,path=f'{T}/{G}/manifest.json',status=status,numbers=NUMS))
    r.put(HIST,dict(status='historical-only-never-active-not-for-deploy',testId=T,sourceGroupId=G,
       sourceActiveScope=NUMS,retiredWorkGroup=oldgwork,noHistoricalRegrade=True,priorDeployedCommit=PAST,priorDeployedPack=PACK,
       priorDeployedPackSha256=hashlib.sha256(r.read(PAST,PACK)).hexdigest(),priorDeployedGroup=oldg,
       priorDeployedQuestions=oldqs, legacyQuestions=oldqs))
    r.put(META,dict(kind=GRAPHIC_KIND,sourceGroupId=G,newGroupId=NEW,questionNumbers=NUMS,notPublished=True,
       replacementEvidence=ev,questionCanonicalSha256=[dig(q) for q in nr],newGroupCanonicalSha256=dig(candidateGroup),
       previousReserve=f'{PRE}/manifest.json',retiredLegacyHistory=HIST,preservedGraphic=asset))
    return r,base,idx,override,asset

class GraphicTests(unittest.TestCase):
    def test_replay_old_text_and_new_image(self):
        r,b,i,o,a=fixture()
        now,splices,archive=rotate(r,REF,b,i,o)
        self.assertEqual(set(media(now[T]))-set(media(b[T])),{a['runtimePath']})
        self.assertEqual(archive[f'historical-snapshots/{PAST}/{PACK}'],r.read(PAST,PACK))
        self.assertEqual(archive[PRE+'/media/'+a['runtimePath'].rsplit('/',1)[1]],r.read(REF,a['checkpointPath']))
        self.assertEqual((now[T]['questions'][176]['id'],now[T]['questions'][176]['answer']),('t03-q177-r2','D'))
        self.assertEqual(splices[-1]['addedGraphic'],a)
        with TemporaryDirectory() as tmp:
            site=Path(tmp); ledger=site/'ledger'
            for exam in EXAMS:
                for relative,body in [(f'data/{exam}.json',r.read(BASE,f'data/{exam}.json'))]:
                    f=site/relative;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(body)
            for splice in splices:
                for n in splice['numbers']:
                    f=ledger/splice['testId']/f'Q{n:03}.json';f.parent.mkdir(parents=True,exist_ok=True)
                    f.write_bytes(r.read(REF,f'qa-checkpoints/verified-items/{splice["testId"]}/{f.name}'))
            f=site/a['runtimePath'];f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(r.read(REF,a['checkpointPath']))
            check_site_and_ledger(r,BASE,REF,site,ledger,splices)
            f.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'site graphic does not match'):check_site_and_ledger(r,BASE,REF,site,ledger,splices)
    def test_no_retroactive_deployed_graphic(self):
        r,b,i,o,a=fixture()
        h=r.row(REF,HIST);h['priorDeployedGroup']['image']=a['runtimePath'];r.put(HIST,h)
        with self.assertRaisesRegex(ValueError,'historical prior group mismatch'): rotate(r,REF,b,i,o)
    def test_reject_changed_item_image_hash(self):
        r,b,i,o,a=fixture(); f=f'qa-checkpoints/verified-items/{T}/Q177.json'; q=r.row(REF,f)
        q['imageSha256']='0'*64;r.put(f,q)
        with self.assertRaisesRegex(ValueError,'item-level image hash drift'): rotate(r,REF,b,i,o)
    def test_reject_same_q177_id_with_new_passage(self):
        r,b,i,o,a=fixture(); f=f'qa-checkpoints/verified-items/{T}/Q177.json'; q=r.row(REF,f)
        q['activeQuestion']['id']='t03-q177';r.put(f,q)
        manifest=r.row(REF,f'{PRE}/manifest.json')
        manifest['replacementQuestionIds'][1]='t03-q177';r.put(f'{PRE}/manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'replacement numbered identity mismatch'): rotate(r,REF,b,i,o)

if __name__=='__main__':unittest.main()
