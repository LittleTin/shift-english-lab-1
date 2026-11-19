'use strict';
// Final-candidate scenario: real download/native visibility on an isolated origin.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
const digest=b=>createHash('sha256').update(b).digest('hex');
function target(s){
 const u=new URL(s);
 assert.ok(['http:','https:'].includes(u.protocol)&&u.pathname.endsWith('/')&&!u.search&&!u.hash&&!u.username&&!u.password);
 assert.ok(['localhost','127.0.0.1','[::1]'].includes(u.hostname),'Isolated loopback staging only');
 return u;
}
async function transport(base,root,appSha,refs){
 const url=x=>new URL(x,base);
 async function get(ref,opts){
  assert.ok(/^[a-zA-Z0-9_./-]+$/.test(ref)&&!ref.split('/').includes('..')&&!ref.startsWith('/'));
  return fetch(url(ref),{redirect:'error',...opts});
 }
 const app=fs.readFileSync(path.join(root,'assets/app.js'));
 assert.equal(digest(app),appSha); assert.ok(app.includes(Buffer.from('async function backupSnapshot(')));
 const a=await get('assets/app.js');assert.equal(a.status,200);assert.equal(digest(Buffer.from(await a.arrayBuffer())),appSha);
 for(const ref of refs){
  const bytes=fs.readFileSync(path.join(root,ref));assert.ok(bytes.length>128);
  const h=await get(ref,{method:'HEAD'});assert.equal(h.status,200);assert.equal(h.headers.get('content-length'),String(bytes.length));
  const r=await get(ref,{headers:{Range:'bytes=64-127'}});
  assert.equal(r.status,206);assert.equal(r.headers.get('content-range'),`bytes 64-127/${bytes.length}`);
  assert.deepEqual(Buffer.from(await r.arrayBuffer()),bytes.subarray(64,128));
  const bad=await get(ref,{headers:{Range:`bytes=${bytes.length}-`}});assert.equal(bad.status,416);
 }
}
async function run(){
 const [baseURL,site,appSha]=process.argv.slice(2);
 assert.ok(baseURL&&site&&/^[a-f0-9]{64}$/.test(appSha||''),'URL SITE EXPECTED_APP_SHA256 required');
 const base=target(baseURL),url=x=>new URL(x,base).toString();
 const {chromium}=require('playwright');
 const pfile='data/test-01.json', pbuf=fs.readFileSync(path.join(site,pfile)),pack=JSON.parse(pbuf);
 const pserver=await fetch(url(pfile),{redirect:'error'});assert.equal(pserver.status,200);
 assert.equal(digest(Buffer.from(await pserver.arrayBuffer())),digest(pbuf),'Served candidate pack differs');
 const q=pack.questions.find(x=>x.number===98);
 const frames=pack.listeningPlan.frames.filter(x=>x.groupId===q.groupId);
 const i=frames.findIndex(x=>x.role==='passage'); const passage=frames[i]; assert.ok(i>=0&&passage.duration>10&&passage.src.endsWith('.wav'));
 const legacy=pack.previousListeningPlan?.frames?.find(x=>x.kind==='audio'&&x.src.endsWith('.mp3'))||Object.values(pack.alternateListeningPlans||{}).flatMap(x=>x.frames).find(x=>x.kind==='audio'&&x.src.endsWith('.mp3'));
 assert.ok(legacy?.src,'Candidate must retain a prior MP3');
 await transport(base,site,appSha,[passage.src,legacy.src]);
 const browser=await chromium.launch({headless:false,executablePath:process.env.CHROMIUM_BIN||undefined});
 const ctx=await browser.newContext({acceptDownloads:true});
 await ctx.route('**/*',r=>new URL(r.request().url()).origin===base.origin?r.continue():r.abort());
 const action=(p,a)=>p.locator('[data-action="'+a+'"]');
 const open=async p=>{await p.goto(url('index.html'));await action(p,'test-exam').first().waitFor()};
 const read=p=>p.evaluate(async()=>await new Promise((res,rej)=>{
  const req=indexedDB.open('shift-english-lab-v1',1); req.onerror=()=>rej(req.error);
  req.onsuccess=()=>{const db=req.result; const g=db.transaction('kv').objectStore('kv').get('state');
   g.onsuccess=()=>{res(g.result);db.close()};g.onerror=()=>{rej(g.error);db.close()}};
 }));
 const when=async(p,f)=>{for(let j=0;j<80;j++){const s=await read(p);if(f(s))return s;await p.waitForTimeout(100);}assert.fail('Expected saved state was not observed')};
 const picked=s=>({id:s.active.id,index:s.active.index,answers:s.active.answers,
  audio:s.active.audioUsed[q.groupId],notes:s.notes});
 const resume=p=>p.getByRole('button',{name:'Resume Listening',exact:true});
 const waitAudio=(p,lo,hi)=>p.waitForFunction(({src,lo,hi})=>{
  const a=document.querySelector('#audio-player');return a&&a.getAttribute('src')===src&&!a.paused&&!a.seeking&&!a.error&&a.currentTime>=lo&&a.currentTime<=hi;
 },{src:passage.src,lo,hi},{timeout:12000});
 try {
  const a=await ctx.newPage(),b=await ctx.newPage();
  // B deliberately loads before A imports its synthetic current-version state.
  await open(b);await action(b,'nav-data').click();await action(b,'export-backup').waitFor();
  await open(a);await a.bringToFront();
  const version=await a.evaluate(()=>window.SHIFT_CATALOG.version);
  const now=Date.now(),note='Synthetic two-tab backup guard';
  const state={formatVersion:1,attempts:[],sessions:[],notes:{[q.id]:note},
   active:{id:'test-backup-2tabs',title:'Synthetic current listening',mode:'exam',testIds:['test-01'],questionIds:pack.questions.map(x=>x.id),index:97,
     contentVersion:version,startedAt:now-1000,deadline:now+7200000,examVersion:2,examPhase:'listening',audioEdition:pack.listeningPlan.audioEdition,
     listeningStartedAt:now,sectionDeadline:null,answers:{[pack.questions[0].id]:'A'},audioUsed:{[q.groupId]:{status:'interrupted',unlockAt:0,frame:i,offset:2}}}};
  await a.locator('#backup-input').setInputFiles({name:'synthetic.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({format:'shift-learning-backup',version:1,state}))});
  await a.locator('#confirm-modal').click();await a.waitForFunction(()=>document.getElementById('toast')?.textContent.includes('Learning records restored'));
  await action(a,'resume').click();await resume(a).click();
  await waitAudio(a,passage.start+3,passage.start+15);
  const pick=a.locator('.grouped-question[data-question-id="'+q.id+'"] [data-action=answer][data-option="'+q.answer+'"]');
  await pick.click();await when(a,s=>s?.active?.answers?.[q.id]===q.answer);
  await b.bringToFront();
  try {await a.waitForFunction(()=>document.visibilityState==='hidden',undefined,{timeout:4000});}
  catch {console.error('NOT RUN: selected browser did not produce native tab visibility');process.exitCode=2;return;}
  const latest=await when(a,s=>s?.active?.audioUsed?.[q.groupId]?.status==='interrupted'&&s.active.audioUsed[q.groupId].offset>=3);
  assert.ok(await a.locator('#audio-player').evaluate(x=>x.paused));
  const snapshot=picked(latest);
  const ev=b.waitForEvent('download');await action(b,'export-backup').click();
  const downloaded=await ev;const data=JSON.parse(fs.readFileSync(await downloaded.path(),'utf8'));
  assert.equal(data.format,'shift-learning-backup');assert.equal(data.version,1);
  assert.deepEqual(picked(data.state),snapshot,'Stale tab did not download the newest answers/audio/notes');
  assert.deepEqual(picked(await read(b)),snapshot,'Backup export changed durable progress');
  // Reload while A remains backgrounded to avoid an incidental foreground resume write.
  await a.reload();assert.deepEqual(picked(await read(a)),snapshot);
  await a.bringToFront();
  await Promise.race([action(a,'resume').waitFor(),a.locator('#audio-player').waitFor({state:'attached'})]);
  if(await action(a,'resume').isVisible())await action(a,'resume').click();
  if(await resume(a).isEnabled({timeout:4000}))await resume(a).click();
  await waitAudio(a,passage.start+snapshot.audio.offset-.35,passage.start+snapshot.audio.offset+2.5);
  console.log('PASS: exact loopback bytes/ranges, genuine background pause, stale-tab actual backup download, durable state unchanged and exact resumed offset');
 }finally{await ctx.close();await browser.close();}
}
module.exports={target,transport};
if(require.main===module)run().catch(e=>{console.error(e);process.exitCode=1});
