// Synthetic local fixture only. Syntax/pretest is not a true browser run.
// Usage: HEADED=1 node browser-smoke.cjs http://127.0.0.1:8769/ path/to/fixture
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createHash}=require('node:crypto');
const {chromium}=require('playwright');
const argv=process.argv.slice(2);
const base=new URL(argv[0]||'about:blank');
assert.equal(base.protocol,'http:');
assert.equal(base.hostname,'127.0.0.1','Loopback fixture only; never point this to production');
assert.equal(base.pathname,'/');
assert.ok(base.port && !base.username && !base.password && !base.search && !base.hash);
const receiptFile=path.join(argv[1]||'', 'fixture.json');
const receiptBytes=fs.readFileSync(receiptFile);
const meta=JSON.parse(receiptBytes);
assert.ok(meta.fixtureOnly && meta.doNotDeploy);
const identity=createHash('sha256').update(receiptBytes).digest('hex');
const site=path.join(argv[1],'site');
const url=p=>new URL(p,base).toString();
const action=(p,a)=>p.locator('[data-action="'+a+'"]');
const question=(p,id)=>p.locator('.grouped-question[data-question-id="'+id+'"]');
const svg=p=>p.locator('.scored-graphic img');
const answers=(p,id,letter)=>question(p,id).locator('[data-action="answer"][data-option="'+letter+'"]');
const failures=[],untested=[];
const packs={};
const tests=['test-01','test-02','test-03'];
for(const t of tests){
 const buf=fs.readFileSync(path.join(site,'data',t+'.json'));
 assert.equal(createHash('sha256').update(buf).digest('hex'),meta.activeDraftMajors[t]);
 packs[t]=JSON.parse(buf);
 assert.equal(packs[t].questions.length,200);
 assert.ok(!('legacyQuestions' in packs[t]));
}
const selected=process.env.TEST_ID ? [process.env.TEST_ID] : tests;
assert.ok(selected.every(id=>tests.includes(id)));

async function fresh(browser, viewport={width:1360,height:850}){
 const ctx=await browser.newContext({viewport,acceptDownloads:true});
 await ctx.route('**/*',r=>new URL(r.request().url()).origin===base.origin?r.continue():r.abort());
 await ctx.addInitScript(()=>{
  window.shiftPlaying=[];
  document.addEventListener('playing',e=>{
   const a=e.target;if(a.id!=='audio-player')return;
   window.shiftPlaying.push({src:a.getAttribute('src'),time:a.currentTime});
  },true);
 });
 const page=await ctx.newPage(), errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url());});
 return {ctx,page,errors};
}
async function isolated(browser,label,fn,v){
 const {ctx,page,errors}=await fresh(browser,v);
 try{await fn(page,ctx);assert.deepEqual(errors,[]);console.log('PASS',label)}
 catch(e){failures.push(label);console.error('FAIL',label,e)}
 finally{await ctx.close()}
}
async function dbState(p){
 return p.evaluate(async()=>await new Promise((res,rej)=>{
  const req=indexedDB.open('shift-english-lab-v1',1);req.onerror=()=>rej(req.error);
  req.onsuccess=()=>{const db=req.result;try{
   const x=db.transaction('kv').objectStore('kv').get('state');
   x.onsuccess=()=>{res(x.result);db.close()};x.onerror=()=>{rej(x.error);db.close()};
  }catch(e){db.close();rej(e)}};
 }));
}
async function untilStored(p,test,ms=7000){
 for(let i=0;i<Math.ceil(ms/100);i++){
  const d=await dbState(p);
  if(test(d))return d;
  await p.waitForTimeout(100);
 }
 throw new Error('Expected IndexedDB checkpoint not observed');
}
async function openApp(p){await p.goto(url('index.html'));await action(p,'test-exam').first().waitFor()}
async function start(p,t,kind){
 await openApp(p);
 if(kind!=='test-exam')await action(p,'test-pick').and(p.locator('[data-test="'+t+'"]')).click();
 await action(p,kind).and(p.locator('[data-test="'+t+'"]')).click();
 if(kind==='test-exam')await p.locator('#confirm-modal').click();
}
async function restore(p, state){
 const payload={format:'shift-learning-backup',version:1,state};
 await p.locator('#backup-input').setInputFiles({name:'synthetic-restore.json',
    mimeType:'application/json',buffer:Buffer.from(JSON.stringify(payload))});
 await p.locator('#confirm-modal').click();
 await p.waitForFunction(()=>document.getElementById('toast')?.textContent.includes('Learning records restored'));
}
async function playing(p,src,min=0,max=Number.MAX_SAFE_INTEGER){
 await p.waitForFunction(({src,min,max})=>{
  const a=document.getElementById('audio-player');
  return a?.getAttribute('src')===src&&!a.paused&&!a.seeking&&!a.error&&a.currentTime>=min&&a.currentTime<=max;
 },{src,min,max},{timeout:22000});
}
async function picture(p, expected){
 await svg(p).waitFor();
 assert.equal(await svg(p).getAttribute('src'),expected);
 await svg(p).evaluate(img=>img.decode());
 assert.ok(await svg(p).evaluate(img=>img.complete&&img.naturalWidth>0));
}
async function nativeTapHide(p,ctx,id,gid,passage){
 const other=await ctx.newPage();await other.goto(url('使用說明.html'));await other.bringToFront();
 const hidden=await p.waitForFunction(()=>document.visibilityState==='hidden',undefined,{timeout:4000,polling:80}).then(()=>true,()=>false);
 if(!hidden){untested.push(id+': genuine tab visibility');await other.close();return;}
 const stopped=(await untilStored(p,s=>s?.active?.audioUsed?.[gid]?.status==='interrupted')).active.audioUsed[gid];
 await p.waitForFunction(()=>document.getElementById('audio-player').paused,undefined,{polling:80});
 const timer=p.locator('#timer');
 const shown=await timer.textContent();
 await p.waitForTimeout(1050);
 assert.equal(await timer.textContent(),shown,'Listening display timer advances while hidden');
 await p.bringToFront();
 await p.waitForFunction(()=>document.visibilityState==='visible');
 const trigger=p.getByRole('button',{name:'Resume Listening',exact:true});
 if(await trigger.isEnabled())await trigger.click();
 await playing(p,passage.src,Math.max(passage.start+.05,passage.start+stopped.offset-.3));
 await other.close();
 console.log('PASS',id,'genuine tab pause, frozen timer and corresponding resume');
}
function activeFixture(test, q, frames,index,offset, ids, started=Date.now()-3000){
 const f=frames[index];assert.ok(offset>=0 && offset<f.duration);
 return {id:'synthetic-session',title:'Synthetic exam continuity',mode:'exam',testIds:[test],questionIds:ids,
   index:ids.indexOf(q.id),startedAt:started,deadline:Date.now()+7200000,examVersion:2,examPhase:'listening',audioEdition:'toeic-1',
   listeningStartedAt:started+1000,sectionDeadline:null,answers:{},audioUsed:{[q.groupId]:{status:'interrupted',unlockAt:0,frame:index,offset}}};
}
async function terminalScore(p){
 await openApp(p);
 const pack=packs['test-01'],q=pack.questions[97], frames=pack.listeningPlan.frames.filter(f=>f.groupId===q.groupId);
 const final=frames.findIndex(f=>f.role==='closing');assert.ok(final>=0);
 const active=activeFixture('test-01',q,frames,final,Math.max(0,frames[final].duration-3),pack.questions.map(x=>x.id));
 active.contentVersion=meta.syntheticVersion;
 active.answers[pack.questions[0].id]=pack.questions[0].answer;
 await restore(p,{formatVersion:1,attempts:[],sessions:[],active});
 await action(p,'resume').click();
 await p.getByRole('button',{name:'Resume Listening',exact:true}).click();
 await playing(p,frames[final].src,frames[final].start+active.audioUsed[q.groupId].offset-.2);
 const reading=pack.questions[100];
 await question(p,reading.id).waitFor({timeout:15000});
 const s=await untilStored(p,s=>s?.active?.examPhase==='reading');
 assert.equal(s.active.audioUsed[q.groupId].status,'ended');
 const remaining=s.active.sectionDeadline-Date.now();
 assert.ok(remaining>4485000&&remaining<=4500000,'Reading timer not initialized to 75 minutes');
 await action(p,'question-grid').click();
 assert.equal(await p.locator('[data-action="jump"][data-index="0"]').count(),0,'Listening is still reachable in reading!');
 await action(p,'close-modal').click();
 assert.equal(await p.locator('.rationales').count(),0);
 await answers(p,reading.id,reading.answer).click();
 await action(p,'finish-session').click();await p.locator('#confirm-modal').click();
 await p.getByText('Raw correct answers: Listening 1 / 100; Reading 1 / 100', {exact:false}).waitFor();
 const d=await untilStored(p,s=>s?.active===null&&s?.sessions?.length===1);
 assert.deepEqual([d.sessions[0].correct,d.sessions[0].answered,d.sessions[0].total],[2,2,200]);
 assert.equal(d.attempts.length,200);
 await action(p,'view-explanation').and(p.locator('[data-id="'+reading.id+'"]')).click();
 await p.locator('.rationales').waitFor();
 assert.equal(await p.locator('.rationale').count(),reading.options.length);
 await p.getByText(reading.promptZh,{exact:true}).waitFor();
 await action(p,'nav-data').click();
 const download=p.waitForEvent('download');await action(p,'export-backup').click();
 const opt=await download;assert.match(opt.suggestedFilename(),/\.json$/i);
 const data=JSON.parse(fs.readFileSync(await opt.path(),'utf8'));
 assert.equal(data.format,'shift-learning-backup');assert.equal(data.state.sessions[0].correct,2);
}
async function retiredAndResumed(p, unknown=false){
 await openApp(p);
 const a=meta.oldResume,q=a.question,rid='synthetic-retired-finished', old= q.id, correct=q.answer;
 assert.ok(!packs['test-01'].questions.some(x=>x.id===old));
 let stamp=Math.min(Date.now()-60000,a.entry.until-5000);
 assert.ok(stamp>a.entry.from);
 const done={id:rid,title:'Synthetic prior completed result',mode:'exam',questionIds:[old],answers:{[old]:correct},
  startedAt:stamp-10000,finishedAt:stamp-5000,correct:1,total:1,answered:1};
 const att={id:rid+':'+old,questionId:old,testId:'test-01',part:q.part,topic:q.topic,revision:q.revision||1,selected:correct,correct:true,correctAnswer:correct,at:stamp-6000};
 const active=activeFixture('test-01',q,[...Array(a.passageIndex).fill(null),a.passage],a.passageIndex,2,a.questionIds,unknown?a.entry.from-1:stamp);
 active.answers[old]=correct;
 await restore(p,{formatVersion:1,attempts:[att],sessions:[done],notes:{[old]:'Synthetic original note'},active});
 if(unknown){
  const before=(await dbState(p)).active;
  await action(p,'resume').click();
  await p.getByText('The original version for this unfinished test cannot be confirmed.',{exact:false}).waitFor();
  assert.deepEqual((await dbState(p)).active,before);
  return;
 }
 await action(p,'nav-stats').click();
 await action(p,'open-result').and(p.locator('[data-id="'+rid+'"]')).click();
 await p.getByText('Original correct answer: '+correct,{exact:false}).waitFor();
 assert.equal((await dbState(p)).sessions[0].correct,1);
 assert.equal((await dbState(p)).notes[old],'Synthetic original note');
 await action(p,'nav-home').last().click();
 await action(p,'resume').click();
 await question(p,old).waitFor();
 await picture(p,a.image);
 assert.equal(await answers(p,old,correct).getAttribute('aria-pressed'),'true');
 await p.getByRole('button',{name:'Resume Listening',exact:true}).click();
 await playing(p,a.passage.src,a.passage.start+1.75,a.passage.start+5);
 const resumed=await untilStored(p,s=>s?.active?.audioUsed?.[a.groupId]?.offset>=2);
 assert.deepEqual(resumed.active.questionIds,a.questionIds);
 assert.equal(resumed.active.answers[old],correct);
 assert.equal(resumed.sessions[0].correct,1);
}
(async()=>{
 const r=await fetch(url('__shift_fixture'));
 assert.equal(r.headers.get('X-Shift-Fixture'),identity,'Fixture identity mismatch; refuse to open browser');
 assert.equal((await r.json()).case,'SHIFT_SYNTHETIC_LOCAL_ONLY');
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',
  headless:process.env.HEADED!=='1',args:['--disable-dev-shm-usage']});
 try{
  for(const t of selected){
   const pack=packs[t],q=pack.questions[0],g=pack.groups.find(x=>x.id===q.groupId);
   await isolated(browser,t+' phone-size practice / asset / replay / persistence',async p=>{
    await start(p,t,'test-listening');await picture(p,g.image);
    assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Horizontal overflow at phone viewport');
    await action(p,'play-audio').click();await playing(p,g.audio,(g.audioStart||0)+.2);
    await action(p,'play-audio').click();await p.waitForFunction(()=>document.getElementById('audio-player').paused);
    await p.locator('#audio-speed').selectOption('1.25');
    await action(p,'play-audio').click();await playing(p,g.audio,(g.audioStart||0)+.2);
    assert.equal(await p.locator('#audio-player').evaluate(a=>a.playbackRate),1.25);
    await answers(p,q.id,q.answer).click();
    assert.equal(await p.locator('.rationales,.feedback').count(),0);
    assert.equal(await answers(p,q.id,q.answer).getAttribute('aria-pressed'),'true');
    const d=await untilStored(p,s=>s?.active?.answers?.[q.id]===q.answer);
    assert.equal(d.active.questionIds.length,100);
    assert.equal(d.active.contentVersion,meta.syntheticVersion);
    await p.reload();await answers(p,q.id,q.answer).and(p.locator('[aria-pressed="true"]')).waitFor();
   },{width:390,height:844});
   await isolated(browser,t+' formal frame order / true visibility / stored offset / automatic next',async(p,ctx)=>{
    await start(p,t,'test-exam');
    const frames=pack.listeningPlan.frames.filter(f=>f.groupId===g.id);
    const plan=frames.filter(f=>f.kind==='audio');
    const last=plan.at(-1),passageIndex=frames.indexOf(last);
    let seen=0;
    await action(p,'play-audio').click();
    for(const frame of plan){
     const h=await p.waitForFunction(({src,start,seen})=>{
      const i=window.shiftPlaying.findIndex((x,j)=>j>=seen&&x.src===src&&Math.abs(x.time-start)<.6);
      return i>=0?i+1:false;
     },{src:frame.src,start:frame.start,seen},{timeout:65000});
     seen=await h.jsonValue();
    }
    assert.equal(await p.locator('#audio-speed,#audio-seek').count(),0);
    await nativeTapHide(p,ctx,t,g.id,last);
    const first=await untilStored(p,s=>s?.active?.audioUsed?.[g.id]?.frame===passageIndex&&s.active.audioUsed[g.id].offset>=2);
    const stored=first.active.audioUsed[g.id];
    await p.reload();
    await p.getByRole('button',{name:'Resume Listening',exact:true}).click();
    await playing(p,last.src,Math.max(last.start+.15,last.start+stored.offset-.25));
    const next=pack.listeningPlan.frames.find(f=>f.groupId!==g.id&&f.kind==='audio');
    await p.waitForFunction(src=>window.shiftPlaying.some(x=>x.src===src),next.src,{timeout:65000});
    const finished=await untilStored(p,s=>s?.active?.audioUsed?.[g.id]?.status==='ended'&&s.active.index>0);
    assert.equal(finished.active.questionIds.length,200);
    assert.equal(await action(p,'prev-question').count(),0);
   });
  }
  if(meta.practiceFilterHelperSha256){
   await isolated(browser,'strict difficulty and complete groups across all three packs',async p=>{
    await openApp(p);await action(p,'nav-practice').click();
    await p.locator('#filter-section').selectOption('listening');
    await p.locator('#filter-part').selectOption('3');
    await p.locator('#filter-difficulty').selectOption('advanced');
    await p.locator('#filter-count').selectOption('100');
    await action(p,'start-filtered').click();
    const active=(await untilStored(p,s=>s?.active?.questionIds?.length)).active;
    const found=new Set(active.questionIds);
    const all=tests.flatMap(t=>packs[t].questions);
    const groups=new Map();
    for(const q of all){const key=JSON.stringify([q.testId,q.groupId||q.id]);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(q);}
    let expected=0;
    for(const rows of groups.values()){
     const eligible=rows.every(q=>q.part===3&&q.difficulty==='advanced');
     const n=rows.filter(q=>found.has(q.id)).length;
     if(eligible){expected+=rows.length;assert.ok(n===0||n===rows.length);}
     else assert.equal(n,0,'Mismatched difficulty or incomplete group');
    }
    assert.ok(expected>0);
    assert.ok(active.questionIds.length<=expected);
    if(expected<=100)assert.equal(active.questionIds.length,expected);
    else assert.ok(active.questionIds.length>=100&&active.questionIds.length<=102);
   });
  }
  await isolated(browser,'terminal playback → 75-minute reading → scoring/review/export',terminalScore);
  await isolated(browser,'prior completed score/note + exact unfinished prior question/audio',p=>retiredAndResumed(p));
  await isolated(browser,'unknown prior epoch stays intact, no guessed resumption',p=>retiredAndResumed(p,true));
  await isolated(browser,'fixture versions and preview assets',async p=>{
   await openApp(p);
   await p.getByText('VERSION '+meta.syntheticVersion,{exact:false}).first().waitFor();
   for(const leaf of ['使用說明.html','語音試聽.html']){
    await p.goto(url(leaf));
    assert.match(await p.locator('[data-site-version]').first().textContent(),new RegExp(meta.syntheticVersion.replaceAll('.','\\.')));
   }
   assert.equal(await p.locator('audio[src]').count(),14);
  });
 }finally{await browser.close();}
 if(failures.length){console.error('FAILED:',failures);process.exitCode=1}
 else if(untested.length){console.error('INCOMPLETE:',untested);process.exitCode=2}
 else console.log('Browser smoke passed for isolated staged fixture only. Not a release acceptance.');
})().catch(e=>{console.error(e);process.exitCode=1});
