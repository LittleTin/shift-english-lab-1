/* DOM/IndexedDB integration with real synthetic HTTP service; not a native browser test. */
const fs=require('node:fs'), path=require('node:path'),vm=require('node:vm');
const {strict:assert}=require('node:assert');
const {JSDOM,VirtualConsole}=require('jsdom');
const {IDBFactory}=require('fake-indexeddb');
const base=path.resolve(process.env.SHIFT_ROOT||path.join(__dirname,'../..'));
const host=process.env.SHIFT_QA_ORIGIN||'http://127.0.0.1:18765';
const A=['alex@shift-fixture.invalid','123456'],B=['blair@shift-fixture.invalid','654321'];
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
 Object.assign(w,{indexedDB:db,fetch:global.fetch.bind(global),scrollTo:()=>{},TextEncoder});
 const p=w.document.querySelector('audio');p.pause=()=>{};p.load=()=>{};
 const d=w.document.querySelector('dialog');d.showModal=()=>d.setAttribute('open','');d.close=()=>d.removeAttribute('open');
 if(existing)for(const [k,v] of existing)w.sessionStorage.setItem(k,v);
 w.eval(read('data/catalog.js'));
 for(let i=1;i<=5;i++)w.eval(read('data/test-0'+i+'.js'));
 for(const f of ['assets/question-uuid.js','assets/shift-sync-config.js','assets/shift-sync-records.js']){
  if(f.endsWith('shift-sync-config.js')) {
   w.SHIFT_SYNC_CONFIG=configured?{url:host,publishableKey:'sb_publishable_shift_fixture_only',allowLocal:true}:{url:'',publishableKey:''}
  } else w.eval(read(f));
 }
 const filename=path.join(base,'assets/app.js');
 new vm.Script(read('assets/app.js'),{filename,importModuleDynamically:vm.constants.USE_MAIN_CONTEXT_DEFAULT_LOADER}).runInContext(dom.getInternalVMContext());
 return {w,db,dom,d:w.document};
}
const click=(p,x)=>{const el=p.d.querySelector('[data-action="'+x+'"]:not(:disabled)');assert.ok(el,'Missing action: '+x);el.click()};
const text=(p,s)=>p.d.querySelector(s)?.textContent?.trim()||'';
async function wait(f,msg){
 for(let i=0;i<160;i++){const value=await f();if(value)return value;await sleep(30)}
 throw Error(msg);
}
const data=async p=>{click(p,'nav-data');await wait(()=>p.d.querySelector('#account-sync'),'Missing account settings')};
async function signIn(p,[email,code]){
 const ef=p.d.querySelector('#shift-sync-email-form');assert.ok(ef);
 ef.querySelector('[name=email]').value=email;ef.dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));
 const cf=await wait(()=>p.d.querySelector('#shift-sync-code-form'),'No code form: '+text(p,'#shift-sync-status'));
 cf.querySelector('[name=code]').value=code;cf.dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));
 await wait(()=>p.d.querySelector('[data-action="sync-logout"]'),'Sign-in failed');
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
 const a=make(),b=make(),baseline=make({configured:false});let reload=null,otherTab=null;
 try{
  for(const p of [a,b,baseline])await wait(()=>p.d.querySelector('[data-action="quick-reading"]'),'app boot: '+p.d.body.textContent.slice(0,100));
  await complete(baseline); click(baseline,'nav-data');await wait(()=>baseline.d.querySelector('[data-action="export-backup"]'),'guest settings');
  assert.equal(baseline.d.querySelector('#account-sync'),null);console.log('PASS feature disabled: original guest scoring and Settings remain available');
  await complete(a);let s=await snapshot(a);assert.equal(s.state.sessions.length,1);assert.equal(s.state.sessions[0].correct,0);const guest=result(s.state);
  await data(a);await signIn(a,A);await wait(()=>text(a,'#shift-sync-status')==='Completed history is synced.','initial empty sync');
  s=await snapshot(a);assert.equal(s.state.sessions.length,1);assert.equal(matches(s,1,1),undefined);
  console.log('PASS first sign-in leaves guest history local');
  click(a,'sync-import-guest');(await wait(()=>a.d.querySelector('dialog[open] #confirm-modal'),'copy confirmation')).click();
  const a1=await listWait(a,1,1);assert.deepEqual(result(a1),guest);
  await data(b);await signIn(b,A);const b1=await listWait(b,1,1);assert.deepEqual(result(b1),guest);
  assert.equal(b1.sessions[0].id,a1.sessions[0].id);assert.notEqual(a1.sessions[0].id,s.state.sessions[0].id);
  click(b,'nav-review');await wait(()=>b.d.querySelector('.record-card'),'synced wrong reviews');
  console.log('PASS explicit copy, score and wrong items synchronize to another device cache');
  await data(b);click(b,'sync-logout');await wait(()=>b.d.querySelector('#shift-sync-email-form'),'logout');
  await signIn(b,B);await wait(()=>text(b,'#shift-sync-status')==='Completed history is synced.','Blair blank sync');
  click(b,'nav-review');await wait(()=>b.d.body.textContent.toLowerCase().includes('review & remember'),'different account review');
  assert.equal(b.d.querySelectorAll('.record-card').length,0);
  console.log('PASS switching accounts hides the first account history');
  await data(b);click(b,'sync-logout');await wait(()=>b.d.querySelector('#shift-sync-email-form'),'Blair logout');
  await signIn(b,A);await listWait(b,1,1);
  const existing=Array.from({length:b.w.sessionStorage.length},(_,i)=>b.w.sessionStorage.key(i)).map(k=>[k,b.w.sessionStorage.getItem(k)]);
  assert.ok(existing.every(([key,value])=>!/auth|token/i.test(key+value)));
  reload=make({db:b.db,existing});await wait(()=>reload.d.querySelector('[data-action="nav-data"]'),'reload boot');
  await data(reload);assert.ok(reload.d.querySelector('#shift-sync-email-form'));
  await signIn(reload,A);await listWait(reload,1,1);
  console.log('PASS reload stores no credentials, requires sign-in, then restores account history');
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
  assert.deepEqual(seenErrors,[]);
 }finally{for(const p of [a,b,baseline,reload,otherTab])p?.dom.window.close()}
})().catch(e=>{console.error(e.stack,seenErrors);process.exitCode=1});
