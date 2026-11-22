/* DOM/IndexedDB integration with real synthetic HTTP service; not a native browser test. */
const fs=require('node:fs'), path=require('node:path'),vm=require('node:vm');
const {strict:assert}=require('node:assert');
const {JSDOM,VirtualConsole}=require('jsdom');
const {IDBFactory}=require('fake-indexeddb');
const base=path.resolve(process.env.SHIFT_ROOT||path.join(__dirname,'../..'));
const host=process.env.SHIFT_QA_ORIGIN||'http://127.0.0.1:18765';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(host))throw Error('Loopback fixture only');
const A=['alex@shift-fixture.invalid','AlexInitialPass-V1'],B=['blair@shift-fixture.invalid','BlairInitialPass-V1'];
const NEW='BlairReplacementPass-V2';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const read=f=>fs.readFileSync(path.resolve(base,f),'utf8');
const seenErrors=[];
function req(e){return new Promise((y,n)=>{e.onsuccess=()=>y(e.result);e.onerror=()=>n(e.error)})}
function make({db=new IDBFactory(),existing=null,configured=true}={}){
 const vc=new VirtualConsole();
 vc.on('jsdomError',e=>seenErrors.push(String(e.message)));
 vc.on('error',e=>seenErrors.push(String(e)));
 const dom=new JSDOM(read('index.html'),{url:host,runScripts:'outside-only',virtualConsole:vc});
 const w=dom.window;
 const wire=[];
 const fetchFixture=async(input,opts)=>{
  const u=new URL(typeof input==='string'?input:input.url,host);
  assert.equal(u.origin,host,'unexpected external fetch');
  const r=await global.fetch(u,opts);
  if(u.pathname.startsWith('/auth/')) wire.push([opts?.method||'GET',u.pathname,u.searchParams.get('grant_type'),r.status]);
  return r;
 };
 Object.assign(w,{indexedDB:db,fetch:fetchFixture,scrollTo:()=>{},TextEncoder});
 const p=w.document.querySelector('audio');p.pause=()=>{};p.load=()=>{};
 const d=w.document.querySelector('dialog');d.showModal=()=>d.setAttribute('open','');d.close=()=>d.removeAttribute('open');
 if(existing)for(const [k,v] of existing)w.sessionStorage.setItem(k,v);
 w.eval(read('data/catalog.js'));
 for(let i=1;i<=6;i++)w.eval(read('data/test-0'+i+'.js'));
 for(const f of ['assets/question-uuid.js','assets/shift-sync-config.js','assets/shift-sync-records.js']){
  if(f.endsWith('shift-sync-config.js')) {
   w.SHIFT_SYNC_CONFIG=configured?{url:host,publishableKey:'sb_publishable_shift_fixture_only',allowLocal:true}:{url:'',publishableKey:''}
  } else w.eval(read(f));
 }
 const filename=path.join(base,'assets/app.js');
 new vm.Script(read('assets/app.js'),{filename,importModuleDynamically:vm.constants.USE_MAIN_CONTEXT_DEFAULT_LOADER}).runInContext(dom.getInternalVMContext());
 return {w,db,dom,d:w.document,wire};
}
const click=(p,x)=>{const el=p.d.querySelector('[data-action="'+x+'"]:not(:disabled)');assert.ok(el,'Missing action: '+x);el.click()};
const text=(p,s)=>p.d.querySelector(s)?.textContent?.trim()||'';
async function wait(f,msg){
 for(let i=0;i<160;i++){const value=await f();if(value)return value;await sleep(30)}
 throw Error(msg);
}
const data=async p=>{click(p,'nav-data');await wait(()=>p.d.querySelector('#account-sync'),'Missing account settings');await sleep(10)};
function submit(p,selector,values){
 const f=p.d.querySelector(selector);assert.ok(f,selector);
 for(const [name,value] of Object.entries(values)){const el=f.querySelector('[name='+name+']');assert.ok(el,name);el.value=value}
 assert.ok(f.checkValidity(),Array.from(f.elements).filter(x=>x.validationMessage).map(x=>x.name+': '+x.validationMessage).join('; '));
 f.dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));return f;
}
async function signIn(p,[email,password]){
 await sleep(10);
 submit(p,'#shift-sync-login-form',{email,password});
 await wait(()=>p.d.querySelector('[data-action="sync-logout"]'),'Sign-in failed');
}
async function rejectedSignIn(p,[email,password]){
 const index=p.wire.length;
 submit(p,'#shift-sync-login-form',{email,password});
 await wait(()=>p.wire.slice(index).some(([m,path,grant,s])=>m==='POST'&&path==='/auth/v1/token'&&grant==='password'&&s===400),'No invalid-login HTTP response');
 await wait(()=>{const now=text(p,'#shift-sync-status');return now&&!/signing in|loading|checking/i.test(now)},'No invalid-login feedback');
 assert.ok(p.d.querySelector('#shift-sync-login-form'));
 assert.equal(p.d.querySelector('[data-action="sync-logout"]'),null);
}
async function changeBlairPassword(p){
 click(p,'sync-change-password');
 await wait(()=>p.d.querySelector('#shift-sync-password-form'),'missing password form');await sleep(0);
 const index=p.wire.length;
 submit(p,'#shift-sync-password-form',{currentPassword:'DefinitelyWrongPass-V0',newPassword:NEW,confirmPassword:NEW});
 await wait(()=>p.wire.slice(index).some(([m,path,,s])=>m==='PUT'&&path==='/auth/v1/user'&&s===400),'No incorrect-current HTTP response');
 await sleep(50);
 assert.ok(p.d.querySelector('#shift-sync-password-form'));
 const prev=text(p,'#shift-sync-status');const second=p.wire.length;
 submit(p,'#shift-sync-password-form',{currentPassword:B[1],newPassword:NEW,confirmPassword:NEW});
 await wait(()=>p.wire.slice(second).some(([m,path,,s])=>m==='PUT'&&path==='/auth/v1/user'&&s===200),'No valid password-change HTTP response');
 await wait(()=>{const now=text(p,'#shift-sync-status');return (now&&now!==prev&&/chang|updat|success/i.test(now)&&!/changing|updating|could not|unable|incorrect/i.test(now))||!p.d.querySelector('#shift-sync-password-form')},'No password-change completion');
}
async function snapshot(p){
 const db=await req(p.db.open('shift-english-lab-v1'));
 try{
  const keys=await req(db.transaction('kv').objectStore('kv').getAllKeys());
  const objects={};
  for(const k of keys.filter(k=>k.startsWith('state')))objects[k]=await req(db.transaction('kv').objectStore('kv').get(k));
  return objects;
 }finally{db.close()}
}
async function installExam(p,owner,{variant='guest',questionIndex=109,answers=2}={}){
 const pack=p.w.SHIFT_PACKS.find(x=>x.testId==='test-01');
 const ids=Array.from(pack.questions,q=>q.id);
 const deadline=Date.now()+2100000;
 const exam={id:'qa-formal-'+variant,title:'QA formal '+variant,mode:'exam',examVersion:2,examPhase:'reading',
  audioEdition:'toeic-1',contentVersion:p.w.SHIFT_CATALOG.version,questionIds:ids,testIds:['test-01'],index:questionIndex,
  startedAt:deadline-4200000,deadline,sectionDeadline:deadline,listeningStartedAt:deadline-3000000,
  answers:Object.fromEntries(ids.slice(questionIndex,questionIndex+answers).map((id,i)=>[id,i?'B':'D'])),
  submitted:{},audioUsed:{}};
 const key=owner?p.w.SHIFT_SYNC_RECORDS.key('state',owner):'state';
 const db=await req(p.db.open('shift-english-lab-v1'));
 try{
  const tx=db.transaction('kv','readwrite'),store=tx.objectStore('kv');
  const done=new Promise((yes,no)=>{tx.oncomplete=yes;tx.onerror=()=>no(tx.error);tx.onabort=()=>no(tx.error)});
  const r=store.get(key);
  r.onsuccess=()=>store.put({...r.result||{formatVersion:1,attempts:[],sessions:[]},active:exam},key);
  await done;
 }finally{db.close()}
 return {key,exam};
}
const canResume=p=>p.d.querySelector('[data-action="resume"]');
async function resumed(p,exam){
 click(p,'nav-home');await wait(()=>canResume(p),'Progress was not available to resume');
 await sleep(20);click(p,'resume');
 await wait(()=>p.d.querySelector('#timer')&&p.d.querySelector('[data-question="'+exam.questionIds[exam.index]+'"][data-option="D"]'),'Wrong question after resume');
 assert.match(text(p,'#timer'),/\b34:[0-5][0-9]\b|\b35:00\b/);
 assert.ok(p.d.querySelector('[data-question="'+exam.questionIds[exam.index]+'"][data-option="D"]').classList.contains('selected'));
}
function matches(s,n,sent){return Object.entries(s).filter(([k,v])=>k!=='state'&&v.sessions.length===n&&Object.keys(v.syncSent||{}).length===sent).at(0)?.[1]}
async function complete(p){
 click(p,'nav-home');await wait(()=>p.d.querySelector('[data-action="quick-reading"]'),'home');
 await sleep(20);click(p,'quick-reading');
 try{await wait(()=>p.d.querySelector('[data-action="finish-session"]'),'quiz not shown')}catch(e){throw Error(e.message+' '+p.d.body.textContent.replace(/\s+/g,' ').slice(0,600)+' TOAST '+text(p,'#toast'))}
 click(p,'finish-session');(await wait(()=>p.d.querySelector('dialog[open] #confirm-modal'),'score confirmation')).click();
 await wait(()=>p.d.body.textContent.includes('Session complete. See what you learned.'),'score not rendered');
}
async function listWait(p,n,sent){return wait(async()=>matches(await snapshot(p),n,sent),'Missing '+n+' sessions with '+sent+' acknowledged: '+text(p,'#shift-sync-status'))}
async function flag(p,val){Object.defineProperty(p.w.navigator,'onLine',{configurable:true,get:()=>val});if(val)p.w.dispatchEvent(new p.w.Event('online'))}
function result(s){return [s.sessions.length,s.attempts.length,Object.values(s.stats).filter(x=>x.needsReview).length]}
(async()=>{
 await wait(async()=>{try{return (await fetch(host)).ok}catch{return false}},'Synthetic HTTP fixture not ready');
 const a=make(),b=make(),baseline=make({configured:false});let reload=null,otherTab=null,ex=null;
 try{
  for(const p of [a,b,baseline])await wait(()=>p.d.querySelector('[data-action="quick-reading"]'),'app boot: '+p.d.body.textContent.slice(0,100));
  await complete(baseline); click(baseline,'nav-data');await wait(()=>baseline.d.querySelector('[data-action="export-backup"]'),'guest settings');
  assert.equal(baseline.d.querySelector('#account-sync'),null);console.log('PASS feature disabled: original guest scoring and Settings remain available');
  await complete(a);let s=await snapshot(a);assert.equal(s.state.sessions.length,1);assert.equal(s.state.sessions[0].correct,0);const guest=result(s.state);
  await data(a);await rejectedSignIn(a,[A[0],'DefinitelyWrongPass-V0']);await signIn(a,A);await wait(()=>text(a,'#shift-sync-status')==='Completed history is synced.','initial empty sync');
  s=await snapshot(a);assert.equal(s.state.sessions.length,1);assert.equal(matches(s,1,1),undefined);
  console.log('PASS first sign-in leaves guest history local');
  click(a,'sync-import-guest');(await wait(()=>a.d.querySelector('dialog[open] #confirm-modal'),'copy confirmation')).click();
  const a1=await listWait(a,1,1);assert.deepEqual(result(a1),guest);
  await data(b);await signIn(b,A);const b1=await listWait(b,1,1);assert.deepEqual(result(b1),guest);
  assert.equal(b1.sessions[0].id,a1.sessions[0].id);assert.notEqual(a1.sessions[0].id,s.state.sessions[0].id);
  click(b,'nav-review');await wait(()=>b.d.querySelector('.record-card'),'synced wrong reviews');
  console.log('PASS explicit copy, score and wrong items synchronize to another device cache');
  await data(b);click(b,'sync-logout');await wait(()=>b.d.querySelector('#shift-sync-login-form'),'logout');
  await signIn(b,B);await wait(()=>text(b,'#shift-sync-status')==='Completed history is synced.','Blair blank sync');
  click(b,'nav-review');await wait(()=>b.d.body.textContent.toLowerCase().includes('review & remember'),'different account review');
  assert.equal(b.d.querySelectorAll('.record-card').length,0);
  console.log('PASS switching accounts hides the first account history');
  await data(b);await changeBlairPassword(b);
  if(b.d.querySelector('[data-action="sync-logout"]'))click(b,'sync-logout');
  await wait(()=>b.d.querySelector('#shift-sync-login-form'),'Blair logout');
  await rejectedSignIn(b,B);
  await signIn(b,[B[0],NEW]);
  await wait(()=>text(b,'#shift-sync-status')==='Completed history is synced.','Clear after password change');
  click(b,'nav-review');await wait(()=>b.d.body.textContent.toLowerCase().includes('review & remember'),'changed account review');assert.equal(b.d.querySelectorAll('.record-card').length,0);
  await data(b);click(b,'sync-logout');await wait(()=>b.d.querySelector('#shift-sync-login-form'),'Changed Blair logout');
  console.log('PASS wrong current password, change, old login rejected, new login works, no other-account history');
  await signIn(b,A);await listWait(b,1,1);
  const existing=Array.from({length:b.w.sessionStorage.length},(_,i)=>b.w.sessionStorage.key(i)).map(k=>[k,b.w.sessionStorage.getItem(k)]);
  const remembered=existing.find(([key])=>key.startsWith('shift:/shift-english-lab-1/:auth-refresh/'));
  assert.ok(remembered);
  assert.deepEqual(Object.keys(JSON.parse(remembered[1])).sort(),['projectOrigin','refreshToken','userId','version']);
  assert.ok(existing.every(([key,value])=>!/accessToken|InitialPass|ReplacementPass|WrongPass/i.test(key+value)));
  // This exercise models replacing the page in one tab, not concurrent pages using one refresh handle.
  b.dom.window.close();
  reload=make({db:b.db,existing});await wait(()=>reload.d.querySelector('[data-action="nav-data"]'),'reload boot');
  await data(reload);await wait(()=>reload.d.querySelector('[data-action="sync-logout"]'),'reload should re-verify sign-in');
  await listWait(reload,1,1);
  assert.match(text(reload,'#shift-auth-badge'),/Signed in/);
  assert.ok(reload.wire.some(([m,path,grant,s])=>m==='POST'&&path==='/auth/v1/token'&&grant==='refresh_token'&&s===200));
  console.log('PASS same-tab reload re-verifies, stores no access token or password, then restores the same account workspace');
  const fault=await fetch(host+'/__shift_qa/fault',{method:'POST',headers:{'X-Shift-Fixture-Control':'1','Content-Type':'application/json'},body:JSON.stringify({path:'/rest/v1/rpc/shift_save_completed_session',status:503})});
  assert.ok(fault.ok);await complete(a);await data(a);
  await wait(()=>text(a,'#shift-sync-status').startsWith('Unable to connect.'),'server error shown');
  await listWait(a,2,1);
  click(a,'sync-now');await listWait(a,2,2);
  click(reload,'sync-now');const b2=await listWait(reload,2,2);
  assert.equal(new Set(b2.attempts.map(x=>x.id)).size,b2.attempts.length);
  console.log('PASS 503 keeps score local; retry uploads one immutable session and another account cache pulls it');
  await flag(a,false);await complete(a);await listWait(a,3,2);await flag(a,true);await listWait(a,3,3);
  console.log('PASS simulated offline completion persists and uploads on reconnect');
  otherTab=make({db:a.db});await wait(()=>otherTab.d.querySelector('[data-action="nav-data"]'),'same-device other tab');
  await data(otherTab);await signIn(otherTab,A);await listWait(otherTab,3,3);
  await flag(otherTab,false);await complete(otherTab);await listWait(otherTab,4,3);
  otherTab.dom.window.close();otherTab=null;
  await data(a);click(a,'sync-now');await listWait(a,4,4);
  console.log('PASS an offline second tab may close; a surviving same-account tab uploads its durable result');
  const owner='11111111-1111-4111-8111-111111111111';
  const guestExam=await installExam(baseline,null);
  const ownExam=await installExam(baseline,owner,{variant:'account-before',questionIndex:113,answers:1});
  ex=make({db:baseline.db});
  await wait(()=>canResume(ex),'Guest exam seed');
  await data(ex);
  await rejectedSignIn(ex,[A[0],'DefinitelyWrongPass-V0']);
  assert.equal(ex.d.querySelector('#shift-sync-status').hidden,false);
  assert.equal((await snapshot(ex)).state.active.id,guestExam.exam.id);
  await signIn(ex,A);
  await wait(()=>text(ex,'#shift-sync-status')==='Completed history is synced.','Active account did not sync');
  let es=await snapshot(ex);
  for(const [key,t] of [[guestExam.key,guestExam.exam],[ownExam.key,ownExam.exam]]){
   assert.equal(es[key].active.index,t.index);assert.equal(es[key].active.sectionDeadline,t.sectionDeadline);
   assert.deepEqual(es[key].active.answers,t.answers);assert.ok(es[key].sessions.every(r=>r.id!==guestExam.exam.id&&r.id!==ownExam.exam.id));
  }
  assert.equal(es[ownExam.key].sessions.length,4);
  // Another tab has a newer checkpoint; the tab holding the older active exam must not overwrite it when pulling new history.
  const later=await installExam(ex,owner,{variant:'account-newer',questionIndex:122,answers:2});
  await complete(reload);await listWait(reload,5,5);
  click(ex,'sync-now');
  await listWait(ex,5,5);
  es=await snapshot(ex);assert.deepEqual(es[later.key].active,later.exam);
  click(ex,'sync-logout');await wait(()=>ex.d.querySelector('#shift-sync-login-form'),'Logout with unfinished account exam');
  await resumed(ex,guestExam.exam);
  await data(ex);await signIn(ex,B.map((v,i)=>i?NEW:v));await wait(()=>text(ex,'#shift-sync-status')==='Completed history is synced.','Switch to B');
  click(ex,'nav-home');await sleep(40);assert.equal(canResume(ex),null);
  await data(ex);click(ex,'sync-logout');await wait(()=>ex.d.querySelector('#shift-sync-login-form'),'Logout B');
  await signIn(ex,A);await wait(()=>text(ex,'#shift-sync-status')==='Completed history is synced.','Switch back A');
  await resumed(ex,later.exam);
  console.log('PASS active formal exam never blocks login, logout or Sync Now; guest and accounts remain isolated; correct answers, question and timer resume; stale sync does not overwrite a newer checkpoint');
  assert.deepEqual(seenErrors,[]);
 }finally{for(const p of [a,b,baseline,reload,otherTab,ex])p?.dom.window.close()}
})().catch(e=>{console.error(e.stack,seenErrors);process.exitCode=1});
