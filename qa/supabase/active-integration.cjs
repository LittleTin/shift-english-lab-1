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
 const wire=[];let frozen;
 const fetchFixture=async(input,opts)=>{
  const u=new URL(typeof input==='string'?input:input.url,host);
  assert.equal(u.origin,host,'unexpected external fetch');
  if(frozen&&u.pathname.startsWith('/rest/v1/')&&u.pathname.includes('active_checkpoint'))await frozen;
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
 return {w,db,dom,d:w.document,wire,holdActive(){let release;frozen=new Promise(r=>release=r);return ()=>{frozen=null;release()}}};
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
 try{await wait(()=>p.d.querySelector('[data-action="sync-logout"]'),'Sign-in failed')}catch(e){throw Error(e.message+' | '+text(p,'#shift-sync-status')+' | '+JSON.stringify(p.wire))}
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
 const {createShiftSync}=await import('../..//assets/shift-sync.mjs');
 const c=createShiftSync({url:host,publishableKey:'sb_publishable_shift_fixture_only',allowLocal:true});
 const scope=await c.signInWithPassword(...A);
 const remote=()=>c.readActiveCheckpoint(scope);
 const a=make(),b=make(),other=make();
 const tap=async(p,name)=>{await sleep(16);click(p,name);await sleep(16)};
 const ui=p=>text(p,'#shift-auth-badge');
 const routeQuiz=p=>p.d.querySelector('.question-number');
 const answer=(p,n=0,letter='D')=>{
  const cards=[...p.d.querySelectorAll('.grouped-question')];
  const el=cards[n].querySelector('[data-action="answer"][data-option="'+letter+'"]');
  assert.ok(el);el.click();return el.dataset.question
 };
 try{
  for(const p of [a,b,other])await wait(()=>p.d.querySelector('[data-action="nav-data"]'),'app boot');
  assert.equal(ui(a),'Not signed in');
  await data(a);await signIn(a,A);assert.equal(ui(a),'Signed in');
  await tap(a,'nav-home');await wait(()=>a.d.querySelector('[data-action="quick-reading"]'),'home ready');
  await tap(a,'quick-reading');await wait(()=>routeQuiz(a),'opened A practice');
  const first=await wait(async()=>{const x=await remote();return x.checkpoint&&x},'zero answer did not upload');
  assert.deepEqual(first.checkpoint.answers,{});assert.equal(first.checkpoint.index,0);
  await data(b);await signIn(b,A);await tap(b,'nav-home');await wait(()=>canResume(b),'second device resume not visible');
  assert.equal(b.d.querySelector('.resume-main').textContent.trim(),'Resume Practice');
  await tap(b,'resume');await wait(()=>routeQuiz(b),'second device resume click did not open exact question');
  assert.match(routeQuiz(b).textContent,/Question 1 /);
  await data(other);await signIn(other,B);await tap(other,'nav-home');
  await wait(()=>other.d.querySelector('[data-action="quick-reading"]'),'different account home');
  assert.equal(canResume(other),null);
  console.log('PASS a zero-answer practice resumes in a second independent same-account profile, never another account');
  const releaseWire=a.holdActive();
  await sleep(24);const q0=answer(a,0,'D');
  const oldCursor=routeQuiz(a).textContent;
  try{
   await sleep(550);
   await tap(a,'next-question');
   await wait(()=>routeQuiz(a)?.textContent!==oldCursor,'camera frozen while checkpoint network pending');
   assert.equal((await remote()).checkpoint.index,0);
   await tap(a,'prev-question');
   await wait(()=>routeQuiz(a)?.textContent===oldCursor,'previous was blocked by sync');
  }finally{releaseWire()}
  console.log('PASS slow checkpoint HTTP cannot block forward/back navigation or answer selection');
  const update=await wait(async()=>{const x=await remote();return x.checkpoint?.answers?.[q0]==='D'&&x},'answer did not upload');
  // Follow the newer cloud checkpoint outside the quiz; never silently replace an open quiz.
  await data(b);await tap(b,'nav-home');await wait(()=>canResume(b),'return B home');
  const ob=await wait(async()=>Object.values(await snapshot(b)).find(w=>w.active?.answers?.[q0]==='D'),'B did not receive answer');
  assert.equal(ob.active.id,update.checkpoint.id);
  await tap(b,'resume');await wait(()=>routeQuiz(b),'resume B after updated answer');
  await flag(a,false);await tap(a,'next-question');await wait(()=>Number(/Question (\d+)/.exec(routeQuiz(a)?.textContent||'')?.[1])>1,'A offline advance');
  const staleChoice=answer(a,0,'B');assert.notEqual(staleChoice,q0);
  const remoteBefore=await remote();assert.equal(remoteBefore.checkpoint.index,0);
  const bChoice=answer(b,0,'C');assert.equal(bChoice,q0);
  await wait(async()=> (await remote()).checkpoint?.answers?.[q0]==='C','newer B answer not saved');
  await tap(b,'finish-session');(await wait(()=>b.d.querySelector('dialog[open] #confirm-modal'),'confirm B')).click();
  await wait(()=>b.d.body.textContent.includes('Session complete. See what you learned.'),'score B');
  await wait(async()=>{const c=await remote();return c.revision>remoteBefore.revision&&c.checkpoint===null},'B submission did not tombstone cloud progress');
  await flag(a,true);
  await wait(()=>/differs|submitted/i.test(a.d.body.textContent),'A did not surface stale progress');
  assert.equal((await remote()).checkpoint,null);
  assert.ok(Object.values(await snapshot(a)).some(w=>w.active?.answers?.[staleChoice]==='B'));
  console.log('PASS offline stale edits stayed on A; B submitted newer work, tombstone stood; no overwriting or resurrection');
  const d=make();
  try{
   await wait(()=>d.d.querySelector('[data-action="nav-data"]'),'fresh formal device boot');
   const scope2=await c.logout().then(()=>c.signInWithPassword(...B));
   await tap(other,'test-exam');
   (await wait(()=>other.d.querySelector('dialog[open] #confirm-modal'),'formal start confirmation')).click();
   await wait(()=>other.d.querySelector('#timer')?.textContent.includes('Ready to start'),'formal not started');
   const opened=await wait(async()=>{const x=await c.readActiveCheckpoint(scope2);return x.checkpoint?.mode==='exam'&&x},'opening exam did not sync');
   assert.equal(opened.checkpoint.examPhase,'listening');assert.deepEqual(opened.checkpoint.answers,{});
   const seed={...opened.checkpoint,index:100,examPhase:'reading',listeningStartedAt:Date.now()-2600000,sectionDeadline:null,readingStartsOnReturn:true,
    answers:{[opened.checkpoint.questionIds[0]]:'A'}};
   assert.equal(await c.writeActiveCheckpoint({revision:opened.revision,checkpoint:seed,mutationId:crypto.randomUUID()},scope2),'saved');
   // Synthetic server cursor represents handoff. The visible Reading timer is initialized by the real app on this second profile.
   Object.defineProperty(d.d,'hidden',{configurable:true,get:()=>false});
   await data(d);await signIn(d,B);await tap(d,'nav-home');await wait(()=>canResume(d),'formal resume not visible');
   assert.equal(d.d.querySelector('.resume-main').textContent.trim(),'Resume Formal Test');
   await tap(d,'resume');
   await wait(()=>routeQuiz(d)?.textContent.includes('101')&&d.d.querySelector('#timer'),'Reading handoff resume');
   assert.match(text(d,'#timer'),/74:5[7-9]|75:00/);
   const firstReading=await wait(async()=>{const x=await c.readActiveCheckpoint(scope2);return typeof x.checkpoint?.sectionDeadline==='number'&&x},'Reading deadline did not sync');
   assert.equal(firstReading.checkpoint.answers[opened.checkpoint.questionIds[0]],'A');
   assert.ok(firstReading.checkpoint.sectionDeadline-Date.now()>4490000);
   await tap(d,'nav-home');await tap(d,'resume');await wait(()=>routeQuiz(d)?.textContent.includes('101'),'same device restart');
   await sleep(500);
   assert.equal((await c.readActiveCheckpoint(scope2)).checkpoint.sectionDeadline,firstReading.checkpoint.sectionDeadline);
   console.log('PASS synthetic cross-device formal Reading handoff starts 75 minutes once and preserves prior answer, position and same deadline on resume');
  }finally{d.dom.window.close()}
  assert.deepEqual(seenErrors,[]);
 }finally{for(const p of [a,b,other])p.dom.window.close();await c.logout()}
})().catch(e=>{console.error(e.stack,seenErrors);process.exitCode=1});
