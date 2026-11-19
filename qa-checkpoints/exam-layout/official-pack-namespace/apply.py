#!/usr/bin/env python3
import hashlib,sys
from pathlib import Path
pin='50e779e815e972b5f42c23b2e9a90bf137f4ed335652dcb289c9a3d1e6f7c188'
src,out=map(Path,sys.argv[1:]); raw=src.read_bytes()
if hashlib.sha256(raw).hexdigest()!=pin:raise SystemExit('unexpected scoped HQ app baseline')
s=raw.decode()
def rep(old,new):
 global s
 if s.count(old)!=1:raise ValueError(old)
 s=s.replace(old,new)
rep("const catalog=window.SHIFT_CATALOG||{tests:[]};","""const catalog=window.SHIFT_CATALOG||{tests:[]};
const officialEntry=id=>catalog.tests.find(t=>t.id===id);
const officialPacks=new Map(), unavailableCustom=new Set();""")
rep("if(!catalog.tests.some(t=>t.id===id)||state.importedPacks.some(p=>p.testId===id))continue;","if(!officialEntry(id))continue;")
rep("const testIds=new Set();for(const p of s.importedPacks||[]){validatePack(p);if(testIds.has(p.testId))throw new Error('The backup contains duplicate test ID');testIds.add(p.testId);r.importedPacks.push(p)}return r}",
"""const blocked=new Set(),testIds=new Set();
for(const p of s.importedPacks||[]){
 if(officialEntry(p?.testId)){blocked.add(p.testId);continue}
 validatePack(p);
 if(testIds.has(p.testId))throw new Error('The backup contains duplicate test ID');
 testIds.add(p.testId);r.importedPacks.push(p)
}
if(r.active&&(s.active?.reservedPackConflict===true||r.active.testIds.some(id=>blocked.has(id))))r.active.reservedPackConflict=true;
return r}""")
a=s.index("function registerPack(p)");b=s.index("function allQuestions()",a)
s=s[:a]+"""function registerPack(p,official=false){
 validatePack(p);
 if(Boolean(officialEntry(p.testId))!==official)throw new Error('Pack is outside its catalog namespace.');
 const legacy=p.legacyQuestions||[];
 if(legacy.length){
  if(!official)throw new Error('Only built-in packs may include archived questions');
  validatePack({...p,questions:legacy});
 }
 const ids=new Set(p.questions.map(q=>q.id));
 for(const q of legacy)if(ids.has(q.id))throw new Error('Archived question ID conflict');
 for(const q of [...p.questions,...legacy])if(Q.has(q.id)&&Q.get(q.id).testId!==p.testId)throw new Error('Question ID already exists: '+q.id);
 for(const g of p.groups)if(G.has(g.id)&&G.get(g.id).testId!==p.testId)throw new Error('Group ID already exists: '+g.id);
 for(const[id,q]of Q)if(q.testId===p.testId){Q.delete(id);archivedIds.delete(id)}
 for(const[id,g]of G)if(g.testId===p.testId)G.delete(id);
 for(const q of legacy){Q.set(q.id,q);archivedIds.add(q.id)}
 for(const g of p.groups)G.set(g.id,g);
 for(const q of p.questions){Q.set(q.id,q);archivedIds.delete(q.id)}
 if(official)officialPacks.set(p.testId,p);
 loaded.add(p.testId)
}
async function loadTest(id){
 const t=officialEntry(id);
 if(t?officialPacks.has(id):loaded.has(id))return;
 if(loading.has(id))return loading.get(id);
 if(!t){
  const p=state.importedPacks.find(x=>x.testId===id&&!unavailableCustom.has(id));
  if(!p)throw new Error('Test pack not found: '+id);
  registerPack(p);return;
 }
 const promise=new Promise((resolve,reject)=>{
  const script=document.createElement('script');
  script.src=t.path+(location.protocol==='file:'?'':'?v='+encodeURIComponent(catalog.version||VERSION));
  script.onload=()=>{try{
   const p=(window.SHIFT_PACKS||[]).find(p=>p.testId===id);
   if(!p)throw new Error('The test-pack file has no content');
   registerPack(p,true);resolve()
  }catch(e){reject(e)}};
  script.onerror=()=>{script.remove();reject(new Error('Unable to load '+t.path+'. Extract the entire folder before opening index.html.'))};
  document.head.append(script)
 });
 loading.set(id,promise);try{await promise}finally{loading.delete(id)}
}
async function loadAllOfficial(){for(const t of catalog.tests)await loadTest(t.id)}
async function installPackIndexes(){
 Q=new Map();G=new Map();loaded=new Set();archivedIds.clear();officialPacks.clear();unavailableCustom.clear();
 for(const p of window.SHIFT_PACKS||[])if(officialEntry(p.testId))registerPack(p,true);
 if(!state.importedPacks.length)return;
 await loadAllOfficial();
 for(const p of state.importedPacks){
  try{registerPack(p)}catch(e){unavailableCustom.add(p.testId);console.warn('Custom pack not loaded:',p.testId,e.message)}
 }
}
async function loadAll(){for(const t of allTests())await loadTest(t.id)}
function customTest(p){return {id:p.testId,title:p.title||p.testId,subtitle:'Custom pack',reading:p.questions.filter(q=>q.part>4).length,listening:p.questions.filter(q=>q.part<5).length,imported:true}}
function allTests(){return catalog.tests.concat(state.importedPacks.filter(p=>!officialEntry(p.testId)&&!unavailableCustom.has(p.testId)).map(customTest))}
"""+s[b:]
rep("pinnedFor(s)?.packs.get(g.testId)||state.importedPacks.find(p=>p.testId===g.testId)||(window.SHIFT_PACKS||[]).find(p=>p.testId===g.testId)","pinnedFor(s)?.packs.get(g.testId)||(officialEntry(g.testId)?officialPacks.get(g.testId):state.importedPacks.find(p=>p.testId===g.testId&&!unavailableCustom.has(p.testId)))")
rep("if(!p||state.importedPacks.includes(p))","if(!p||!officialEntry(g.testId))")
rep("const next=normalizeState(obj.state);confirmBox(", "const next=normalizeState(obj.state);const omitted=(obj.state.importedPacks||[]).filter(p=>officialEntry(p?.testId)).length;confirmBox(")
rep("Export your current backup first.',async()=>{resumeEnv=null;state=next;clearNoteDraft();Q=new Map();G=new Map();loaded=new Set();for(const p of window.SHIFT_PACKS)registerPack(p);for(const p of state.importedPacks)registerPack(p);", "Export your current backup first.'+(omitted?' Custom definitions with official test IDs will not be installed. Your saved scores and answers are kept.':''),async()=>{if(next.importedPacks.length)await loadAllOfficial();resumeEnv=null;state=next;clearNoteDraft();await installPackIndexes();")
rep("notify(state.importedPacks.some(p=>catalog.tests.some(t=>t.id===p.testId))?'Records restored. Your existing custom pack with the same ID is preserved; the new built-in pack is not loaded.':'Learning records restored.')","notify(omitted||unavailableCustom.size?'Learning records restored. Conflicting custom packs were not loaded.':'Learning records restored.')")
rep("if(catalog.tests.some(t=>t.id===p.testId))throw new Error('Imported packs cannot overwrite built-in packs. Use a new testId.');const old=", "if(officialEntry(p.testId))throw new Error('Imported packs cannot overwrite built-in packs. Use a new testId.');await loadAllOfficial();const old=")
rep("const commit=async()=>{if(old){for(const q of old.questions)Q.delete(q.id);for(const g of old.groups)G.delete(g.id);state.importedPacks=state.importedPacks.filter(x=>x.testId!==p.testId)}state.importedPacks.push(p);registerPack(p);","const commit=async()=>{registerPack(p);unavailableCustom.delete(p.testId);state.importedPacks=state.importedPacks.filter(x=>x.testId!==p.testId);state.importedPacks.push(p);")
rep("for(const id of s.testIds||[])await loadTest(id);await prepareResume(s);","if(s.reservedPackConflict)throw new Error('This saved session used a custom pack with an official test ID. Your saved answers are kept, but its original pack is not available to resume.');for(const id of s.testIds||[])await loadTest(id);await prepareResume(s);")
rep("for(const p of state.importedPacks)registerPack(p);for(const p of window.SHIFT_PACKS||[])registerPack(p);","await installPackIndexes();")
out.write_text(s,encoding='utf-8')
