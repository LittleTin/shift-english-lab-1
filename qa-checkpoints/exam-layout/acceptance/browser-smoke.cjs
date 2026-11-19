// Runs only in an executor that can actually launch Chromium.
// Usage: node browser-smoke.cjs <staging HTTP URL> <local rebuilt site>
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const fs=require('node:fs'), path=require('node:path');
const base=process.argv[2], site=process.argv[3];
assert.ok(base && site,'Supply staging URL and rebuilt site');
const exe=process.env.CHROMIUM_BIN||'/usr/bin/chromium';
const url=relative=>new URL(relative,base).toString();
async function saved(page){
 return page.evaluate(async()=>await new Promise((resolve,reject)=>{
   const a=indexedDB.open('shift-english-lab-v1',1);
   a.onerror=()=>reject(a.error);
   a.onsuccess=()=>{const db=a.result,x=db.transaction('kv').objectStore('kv').get('state');x.onsuccess=()=>{resolve(x.result);db.close()};x.onerror=()=>reject(x.error)};
 }));
}
async function clip(page,src,min=.15){
 return page.waitForFunction(({src,min})=>{const a=document.getElementById('audio-player');return a.getAttribute('src')===src && !a.paused && !a.error && a.currentTime>=min;},{src,min},{timeout:65000});
}
const mediaState=page=>page.locator('#audio-player').evaluate(a=>({src:a.getAttribute('src'),t:a.currentTime,paused:a.paused,error:a.error?.code}));
const button=(page,action,id)=>page.locator('[data-action="'+action+'"]'+(id?'[data-test="'+id+'"]':''));
async function start(page,id,mode){
 await page.goto(url('index.html'));
 if(mode==='test-listening')await button(page,'test-pick',id).click();
 await button(page,mode,id).click();
 if(mode==='test-exam') await page.locator('#confirm-modal').click();
}
async function restore(page,state){
 const value={format:'shift-learning-backup',version:1,state};
 await page.locator('#backup-input').setInputFiles({name:'restore.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});
 await page.locator('#confirm-modal').click();
 await page.waitForFunction(()=>document.getElementById('toast').textContent.includes('Learning records restored'));
}
async function retiredHistory(browser){
 const ctx=await browser.newContext(), page=await ctx.newPage();
 try{
  await page.goto(url('index.html'));
  const when=Date.now()-30000, id='retired-fixture', q=process.env.RETIRED_TEST_ID||'t01-q001';
  const testId='test-01';
  const answer={id:id+':'+q,questionId:q,testId,part:1,topic:'manufacturing',revision:1,selected:'D',correct:true,correctAnswer:'D',at:when+1};
  const session={id,title:'Previous version fixture',mode:'exam',questionIds:[q],answers:{[q]:'D'},startedAt:when,finishedAt:when+5000,correct:1,total:1,answered:1};
  const state={formatVersion:1,attempts:[answer],sessions:[session],notes:{[q]:'Previous note'}};
  await restore(page,state);
  await button(page,'nav-stats').click();
  await button(page,'open-result').click();
  await page.getByText('Original correct answer: D',{exact:false}).waitFor();
  const records=await saved(page);
  assert.equal(records.sessions[0].correct,1);
  assert.equal(records.notes[q],'Previous note');
  // An unfinished old test must still resume on a compatible legacy path.
  // Do not mark success if the site only preserves completed results.
  const exam=JSON.parse(fs.readFileSync(path.join(site,'data','test-01.json')));
  state.active={id:'unfinished-previous',title:'Unfinished previous exam',mode:'exam',testIds:[testId],startedAt:Date.now()-1000,
                deadline:Date.now()+2700000,index:0,questionIds:[q,...exam.questions.slice(1).map(x=>x.id)],
                examVersion:2,examPhase:'listening',audioEdition:'toeic-1',
                answers:{[q]:'D'},audioUsed:{[exam.questions[0].groupId]:{status:'interrupted',unlockAt:0,frame:0,offset:2}}};
  await restore(page,state);
  await button(page,'resume').click();
  await page.getByRole('button',{name:/Resume Listening/}).waitFor();
  assert.equal((await saved(page)).active.answers[q],'D');
  console.log('completed retired results and unfinished former version resumed without regrading');
 }finally{await ctx.close();}
}
(async()=>{
 const browser=await chromium.launch({executablePath:exe,headless:!process.env.HEADED,args:['--disable-dev-shm-usage']});
 try{
 for(const id of ['test-01','test-02','test-03']){
  const pack=JSON.parse(fs.readFileSync(path.join(site,'data',id+'.json')));
  let ctx=await browser.newContext({viewport:{width:390,height:844}});
  let page=await ctx.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await start(page,id,'test-listening');
  const first=pack.questions[0],g=pack.groups.find(x=>x.id===first.groupId);
  const img=page.locator('.scored-graphic img');
  assert.ok(await img.evaluate(x=>x.complete&&x.naturalWidth>0) || await img.evaluate(x=>x.decode().then(()=>true)));
  await button(page,'play-audio').click(); await clip(page,g.audio);
  await button(page,'play-audio').click(); assert.ok((await mediaState(page)).paused);
  await page.locator('#audio-speed').selectOption('1.25');
  await button(page,'play-audio').click(); await clip(page,g.audio);
  assert.equal(await page.locator('#audio-player').evaluate(a=>a.playbackRate),1.25);
  await page.locator('[data-action="answer"]').first().click();
  assert.ok(await page.locator('[data-action="answer"][aria-pressed="true"]').count()>0);
  assert.equal(await page.locator('.rationales').count(),0);
  assert.equal((await saved(page)).active.questionIds.length,100);
  await page.reload(); await page.locator('[data-action="answer"][aria-pressed="true"]').waitFor();
  assert.deepEqual(errors,[]);
  await ctx.close();

  ctx=await browser.newContext({viewport:{width:1360,height:850}});
  page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));
  await start(page,id,'test-exam');
  const plan=pack.listeningPlan.frames.filter(x=>x.groupId===g.id&&x.kind==='audio');
  await button(page,'play-audio').click();
  const seen=[];
  for(const frame of plan){await clip(page,frame.src,.12);seen.push((await mediaState(page)).src);}
  assert.deepEqual(seen,plan.map(x=>x.src));
  assert.equal(await page.locator('#audio-speed,#audio-seek').count(),0);
  // Genuine tab visibility only; do not fake document.hidden. Some headless
  // implementations mark all tabs visible. In that case leave this gate open.
  const other=await ctx.newPage();await other.goto('about:blank');await other.bringToFront();
  const changed=await page.waitForFunction(()=>document.hidden,undefined,{timeout:3000}).then(()=>true,()=>false);
  if(changed){
    await page.waitForFunction(()=>document.getElementById('audio-player').paused);
    const snap=(await saved(page)).active.audioUsed[g.id];
    assert.equal(snap.status,'interrupted');
    const paused=await mediaState(page);
    await page.waitForTimeout(800);
    assert.deepEqual(await mediaState(page),paused);
    await page.bringToFront();await page.waitForFunction(()=>!document.hidden);
    if((await mediaState(page)).paused) await button(page,'play-audio').click();
    await clip(page,plan.at(-1).src,Math.max(.1,snap.offset-.25));
    console.log(id,'real tab pause/resume passed');
  }else console.warn(id,'UNTESTED: this Chromium configuration did not expose true page hiding; repeat headed.');
  await other.close();
  // Periodic checkpoints persist every 2s; prove resumed media is the same
  // actual passage, not the initial directions again.
  await page.waitForFunction(()=>document.getElementById('audio-player').currentTime>2.1);
  const before=(await saved(page)).active.audioUsed[g.id];
  assert.ok(before.frame>=plan.length-1 && before.offset>0,'Saved frame and position are required');
  await page.reload();
  await page.getByRole('button',{name:/Resume Listening/}).click();
  await clip(page,plan.at(-1).src,Math.max(.1,before.offset-.25));
  const next=pack.listeningPlan.frames.find(f=>f.groupId!==g.id&&f.kind==='audio');
  await clip(page,next.src,.1);
  const done=(await saved(page)).active;
  assert.equal(done.audioUsed[g.id].status,'ended');
  assert.ok(done.index>0);
  assert.equal(await page.locator('[data-action="prev-question"]').count(),0);
  assert.deepEqual(errors,[]);
  console.log(id,'real media: practice, speed, image, no-answer disclosure, saved response, formal order, reload, no restart on next group passed');
  await ctx.close();
 }
 await retiredHistory(browser);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
