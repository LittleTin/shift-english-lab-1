#!/usr/bin/env python3
"""Generate isolated app.js proof patch. No changes are made to source."""
import argparse
import difflib
from pathlib import Path

def modify(source):
    def swap(old,new):
        nonlocal source
        if source.count(old)!=1:
            raise ValueError('guard failed: '+old[:90])
        source=source.replace(old,new,1)
    swap("let archivedIds=new Set();","""let archivedIds=new Set();
// Compatibility snapshots are never registered in the active practice pool.
let resumeEnv=null;
const resumeLoads=new Map();
const contentVersion=()=>catalog.version||VERSION;
function pinnedFor(s=state.active){return !!s&&resumeEnv?.sessionId===s.id?resumeEnv:null}
function sessionQuestion(id,s=state.active){return pinnedFor(s)?.questions.get(id)||Q.get(id)}
function sessionGroup(id,s=state.active){return pinnedFor(s)?.groups.get(id)||G.get(id)}
function quizGroup(id){return route==='quiz'?sessionGroup(id):G.get(id)}
async function loadResumeSnapshot(id,s){
 const entry=catalog.resumeSnapshots?.[id];
 if(!entry||!Number.isSafeInteger(entry.from)||!Number.isSafeInteger(entry.until)||s.startedAt<entry.from||s.startedAt>=entry.until||
    (s.contentVersion&&s.contentVersion!==entry.version)||!/^data\\/resume\\/[A-Za-z0-9_-]+\\/test-[0-9]{2}\\.js$/.test(entry.path))
  throw new Error('The original version for this unfinished test cannot be confirmed. Your work is kept. Export a backup before starting another test.');
 const key=entry.path;
 if(!resumeLoads.has(key)){
  const load=new Promise((resolve,reject)=>{
   const script=document.createElement('script');script.src=entry.path;
   script.onload=()=>{try{
     const snapshot=window.SHIFT_RESUME_SNAPSHOTS?.[entry.version]?.[id];
     if(!snapshot||snapshot.testId!==id||snapshot.legacyQuestions!==undefined)throw new Error('The original test snapshot is unavailable'); 
     validatePack(snapshot);resolve(snapshot);
   }catch(e){reject(e)}};
   script.onerror=()=>{script.remove();reject(new Error('The original test archive could not load. Your saved work is unchanged.'))};
   document.head.append(script)
  });
  resumeLoads.set(key,load);
 }
 try{return await resumeLoads.get(key)}catch(e){resumeLoads.delete(key);throw e;}
}
async function prepareResume(s){
 const next={sessionId:s.id,questions:new Map(),groups:new Map(),packs:new Map()};
 if(s.contentVersion!==contentVersion()){
  for(const id of new Set(s.testIds)){
   if(!catalog.tests.some(t=>t.id===id)||state.importedPacks.some(p=>p.testId===id))continue;
   const p=await loadResumeSnapshot(id,s);
   next.packs.set(id,p);
   p.groups.forEach(g=>next.groups.set(g.id,g));
   p.questions.forEach(q=>next.questions.set(q.id,q));
  }
 }
 for(const id of s.questionIds){
  const q=next.questions.get(id)||Q.get(id);
  if(!q||next.packs.has(q.testId)&&!next.questions.has(id)||
     (s.answers[id]&&!q.options.some(o=>o.id===s.answers[id])))
   throw new Error('An original question version is missing. Your unfinished test and answers are kept; export a backup before replacing it.');
 }
 if(state.active?.id!==s.id)throw new Error('The active test changed while its archive loaded.');
 resumeEnv=next.packs.size?next:null;
}""")
    swap("y.testIds=x.testIds.slice();","y.testIds=x.testIds.slice();if(safeId(x.contentVersion))y.contentVersion=x.contentVersion;")
    swap("state.active={id:'session-'+uid(),title,mode,questionIds:","resumeEnv=null;state.active={id:'session-'+uid(),contentVersion:contentVersion(),title,mode,questionIds:")
    swap("function questionByActive(){return state.active?Q.get(state.active.questionIds[state.active.index]):null}","function questionByActive(){return state.active?sessionQuestion(state.active.questionIds[state.active.index]):null}")
    swap("return s.questionIds.map(id=>Q.get(id))","return s.questionIds.map(id=>sessionQuestion(id,s))")
    swap(" const p=state.importedPacks.find(p=>p.testId===g.testId)||(window.SHIFT_PACKS||[]).find(p=>p.testId===g.testId);"," const p=pinnedFor(s)?.packs.get(g.testId)||state.importedPacks.find(p=>p.testId===g.testId)||(window.SHIFT_PACKS||[]).find(p=>p.testId===g.testId);")
    replacements = [
        ('function examSeconds(s,g=G.get(questionByActive()?.groupId))','function examSeconds(s,g=sessionGroup(questionByActive()?.groupId,s))'),
        ('s.questionIds.findIndex(id=>Q.get(id)?.part>=5)','s.questionIds.findIndex(id=>sessionQuestion(id,s)?.part>=5)'),
        ('const g=G.get(q.groupId),qs=groupQuestions(q)','const g=sessionGroup(q.groupId,s),qs=groupQuestions(q)'),
        ('formal(s)&&Q.get(s.questionIds[s.index-1])','formal(s)&&sessionQuestion(s.questionIds[s.index-1],s)'),
        ('questionByActive(),g=q&&G.get(q.groupId)','questionByActive(),g=q&&quizGroup(q.groupId)'),
        ('const next=G.get(questionByActive()?.groupId);','const next=sessionGroup(questionByActive()?.groupId,s);'),
        ('async function playAudio(groupId){const g=G.get(groupId);','async function playAudio(groupId){const g=quizGroup(groupId);'),
        ('groupReady(G.get(q.groupId))','groupReady(sessionGroup(q.groupId,s))'),
        ("if(formal(s)&&s.examPhase==='reading'&&Q.get(s.questionIds[target])?.part<5)return;if(listening(s)&&Q.get(s.questionIds[target])?.part>=5)", "if(formal(s)&&s.examPhase==='reading'&&sessionQuestion(s.questionIds[target],s)?.part<5)return;if(listening(s)&&sessionQuestion(s.questionIds[target],s)?.part>=5)"),
        ('for(const id of s.questionIds){const q=Q.get(id);','for(const id of s.questionIds){const q=sessionQuestion(id,s);'),
        ('state.active=null;await persist();route=\'result\';','state.active=null;resumeEnv=null;await persist();route=\'result\';'),
        ('s.questionIds.forEach((id,i)=>{const q=Q.get(id);','s.questionIds.forEach((id,i)=>{const q=sessionQuestion(id,s);'),
        ("if(!s.questionIds.every(id=>Q.has(id)))throw new Error('The pack needed for this unfinished session is missing. Import the matching pack first.');","await prepareResume(s);"),
        ('q=Q.get(el.dataset.question)||questionByActive();','q=sessionQuestion(el.dataset.question,s)||questionByActive();'),
        ('formal(s)&&Q.get(s.questionIds[index])?.part<5','formal(s)&&sessionQuestion(s.questionIds[index],s)?.part<5'),
        ('G.get(currentAudioGroup);player.currentTime','quizGroup(currentAudioGroup);player.currentTime'),
        ('q=card?Q.get(card.dataset.questionId):questionByActive();','q=card?sessionQuestion(card.dataset.questionId):questionByActive();'),
        ('const g=G.get(currentAudioGroup);if(Number.isFinite','const g=quizGroup(currentAudioGroup);if(Number.isFinite'),
        ('runFormalGroup(G.get(pending.groupId))','runFormalGroup(sessionGroup(pending.groupId))'),
        ("if(state.active&&lastQuiz===state.active.id){await resume()}else","if(state.active&&lastQuiz===state.active.id){try{await resume()}catch(e){route='home';render();notify(e.message)}}else"),
        ("async()=>{state=next;clearNoteDraft();","async()=>{resumeEnv=null;state=next;clearNoteDraft();"),
        ("await loadAll();await finishSession(true)","await loadAll();await finishSession(true)"),
    ]
    for old,new in replacements:swap(old,new)
    return source

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('app',type=Path)
    a.add_argument('out',type=Path)
    a.add_argument('--patch',type=Path)
    x=a.parse_args()
    before=x.app.read_text()
    after=modify(before)
    x.out.write_text(after)
    if x.patch:
        x.patch.write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/assets/app.js',tofile='b/assets/app.js')))
