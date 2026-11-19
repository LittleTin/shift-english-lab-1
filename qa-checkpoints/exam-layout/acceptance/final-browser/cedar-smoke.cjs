// Additive Cedar release test only. Run alongside (not instead of) the full
// browser/mobile suite. Node --check does not execute the browser.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
const {chromium}=require('playwright');
const [preview,site,oldFile,epochFile]=process.argv.slice(2);
assert.ok(preview&&site&&oldFile&&epochFile,
  'Specify approved staging root URL (trailing /), static site, exact old Test03 JSON, reviewed epoch.json');
const base=new URL(preview);
assert.ok(['http:','https:'].includes(base.protocol)&&base.pathname.endsWith('/')&&!base.search&&!base.hash);
assert.ok(!/(?:github\.io|github\.com)$/i.test(base.hostname),'Refusing GitHub production/hosting domains; use isolated staging');
const url=x=>new URL(x,base).toString();
const sha=b=>createHash('sha256').update(b).digest('hex');
const pin='043b91761f63062708d70f7cda3a6b2046cd4cf9';
const currentPackPath='data/test-03.json';
const oldBytes=fs.readFileSync(oldFile),old=JSON.parse(oldBytes);
const currentBytes=fs.readFileSync(path.join(site,currentPackPath)),current=JSON.parse(currentBytes);
const catalogBytes=fs.readFileSync(path.join(site,'data/catalog.js'));
const epoch=JSON.parse(fs.readFileSync(epochFile));
assert.equal(sha(oldBytes),'849c26f1b903d3f89fbe88e39294caeb2386da2a1f8c2f7e4769b2e40a0d849d');
assert.equal(epoch.priorCommit,pin);
assert.equal(epoch.version,'1.4.1');
assert.ok(epoch.source&&typeof epoch.source==='string','Independent deployment epoch source required');
assert.ok(Number.isSafeInteger(epoch.from)&&Number.isSafeInteger(epoch.until)&&
  epoch.from<epoch.until&&epoch.from<Date.now()&&epoch.until<Date.now());
for(const p of [old,current])assert.equal(p.questions.length,200);
const group=(p,id)=>p.groups.find(g=>g.id===id);
const rows=(p,id)=>p.questions.filter(q=>q.groupId===id);
const former=rows(old,'t03-g069'),modern=rows(current,'t03-g069-r2');
const nums=[176,177,178,179,180];
assert.deepEqual(former.map(q=>q.number),nums);assert.deepEqual(modern.map(q=>q.number),nums);
assert.equal(former.map(q=>q.answer).join(''),'CDCAD');
assert.equal(modern.map(q=>q.answer).join(''),'BDACB');
assert.equal(modern[1].id,'t03-q177-r2');
assert.ok(!group(old,'t03-g069').image);
const svg=group(current,'t03-g069-r2').image;
assert.ok(/^assets\/[a-zA-Z0-9_./-]+\.svg$/.test(svg)&&!svg.split('/').includes('..'));
const graphicSHA='a1b4f915b2635ca9f7161da6665f77627669f2ddf9059e4387ccfde1f76d9264';
assert.equal(sha(fs.readFileSync(path.join(site,svg))),graphicSHA);

const action=(p,a)=>p.locator('[data-action="'+a+'"]');
const question=(p,q)=>p.locator('.grouped-question[data-question-id="'+q.id+'"]');
const option=(p,q,k)=>question(p,q).locator('[data-action=answer][data-option="'+k+'"]');
const canon=s=>s.replace(/\s+/g,' ').trim();
async function open(p){await p.goto(url('index.html'));await action(p,'test-exam').first().waitFor();}
async function state(p){
 return p.evaluate(async()=>await new Promise((res,rej)=>{
  const req=indexedDB.open('shift-english-lab-v1',1);req.onerror=()=>rej(req.error);
  req.onsuccess=()=>{const db=req.result;try{const x=db.transaction('kv').objectStore('kv').get('state');
   x.onsuccess=()=>{res(x.result);db.close()};x.onerror=()=>{rej(x.error);db.close()};
  }catch(e){db.close();rej(e)}};
 }));
}
async function until(p,test){
 for(let i=0;i<60;i++){const s=await state(p);if(test(s))return s;await p.waitForTimeout(100);}
 assert.fail('Expected IndexedDB checkpoint not present');
}
async function restore(p, data){
 await p.locator('#backup-input').setInputFiles({name:'cedar-history.json',mimeType:'application/json',
  buffer:Buffer.from(JSON.stringify({format:'shift-learning-backup',version:1,state:data}))});
 await p.locator('#confirm-modal').click();
 await p.waitForFunction(()=>document.getElementById('toast')?.textContent.includes('Learning records restored'));
}
function cssControl(page){
 return page.locator('#app .feedback,#app .rationales,#app .translation,#app .option-zh,#app .passage-text.zh,#app .option-check');
}
async function checkQuiz(p,rr,g,show){
 await question(p,rr[1]).waitFor();
 assert.deepEqual(await p.locator('.grouped-question').evaluateAll(a=>a.map(e=>e.dataset.questionId)),rr.map(q=>q.id));
 assert.equal(canon(await p.locator('.passage-text').textContent()),canon(g.passage));
 assert.equal(await cssControl(p).count(),0,'Pre-submit answer or translation exists in quiz DOM');
 assert.equal(await p.locator('.scored-graphic img').count(),show?1:0);
 if(show){const img=p.locator('.scored-graphic img');assert.equal(await img.getAttribute('src'),svg);
  assert.ok(await img.evaluate(async x=>{await x.decode();return x.naturalWidth>0;}));}
}
async function finish(p,id,count,len){
 await action(p,'finish-session').click();await p.locator('#confirm-modal').click();
 const out=await until(p,s=>!s?.active&&s?.sessions?.some(x=>x.id===id));
 const rec=out.sessions.find(x=>x.id===id);
 assert.deepEqual([rec.correct,rec.answered,rec.total],[count,2,len]);
 return out;
}
function compareAttempts(s,id,rr,score){
 const values=rr.slice(0,3).map(q=>s.attempts.find(a=>a.id===id+':'+q.id));
 assert.deepEqual(values.map(a=>[a.selected,a.correct,a.correctAnswer]),
  [['C',score,rr[0].answer],['D',true,rr[1].answer],[null,false,rr[2].answer]]);
}
async function inContext(browser,fn,viewport){
 const ctx=await browser.newContext({viewport});
 await ctx.route('**/*',r=>new URL(r.request().url()).origin===base.origin?r.continue():r.abort());
 const p=await ctx.newPage(),errors=[];
 p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url());});
 try { await fn(p);assert.deepEqual(errors,[]); } finally { await ctx.close(); }
}
async function archived(p){
 await open(p);
 const checked=await p.evaluate(()=>window.SHIFT_CATALOG?.resumeSnapshots?.['test-03']);
 assert.ok(checked&&checked.version==='1.4.1');
 assert.equal(checked.from,epoch.from);assert.equal(checked.until,epoch.until);
 const started=epoch.from+Math.floor((epoch.until-epoch.from)/2),id='cedar-old-unfinished',past='cedar-old-completed';
 assert.ok(started>epoch.from&&started<epoch.until);
 const old176=former[0],old177=former[1],deadline=Date.now()+600000;
 const oldIDs=old.questions.map(q=>q.id);
 const data={formatVersion:1,attempts:[{id:past+':'+old176.id,questionId:old176.id,testId:'test-03',part:7,topic:old176.topic,revision:1,selected:'C',correct:true,correctAnswer:'C',at:started}],
  sessions:[{id:past,title:'Historical Cedar results',mode:'exam',questionIds:[old176.id],answers:{[old176.id]:'C'},startedAt:started,finishedAt:started+5000,correct:1,answered:1,total:1}],
  notes:{[old177.id]:'Historical Cedar note'},stars:{[old177.id]:true},
  active:{id,title:'Historical Cedar reading',mode:'exam',contentVersion:'1.4.1',testIds:['test-03'],index:176,questionIds:oldIDs,
   startedAt:started,deadline,sectionDeadline:deadline,examVersion:2,examPhase:'reading',audioEdition:'toeic-1',
   answers:{[old176.id]:'C',[old177.id]:'D'},audioUsed:{}}};
 let imageSeen=0;p.on('request',r=>{if(r.url()===url(svg))imageSeen++;});
 await restore(p,data);
 await action(p,'nav-stats').first().click();
 await action(p,'open-result').and(p.locator('[data-id="'+past+'"]')).click();
 await p.getByText('Original correct answer: C',{exact:false}).waitFor();
 assert.equal((await state(p)).sessions.find(s=>s.id===past).correct,1);
 await open(p);await action(p,'resume').click();await checkQuiz(p,former,group(old,'t03-g069'),false);
 assert.equal(await option(p,old177,'D').getAttribute('aria-pressed'),'true');
 await p.reload();await action(p,'resume').click();await checkQuiz(p,former,group(old,'t03-g069'),false);
 const latest=await state(p);assert.deepEqual(latest.active.questionIds,oldIDs);
 assert.equal(latest.active.sectionDeadline,deadline);
 assert.equal(await option(p,old176,'C').getAttribute('aria-pressed'),'true');
 assert.equal(imageSeen,0);
 const done=await finish(p,id,2,200);
 compareAttempts(done,id,former,true);
 assert.equal(done.sessions.find(s=>s.id===past).correct,1);
 assert.equal(done.notes[old177.id],'Historical Cedar note');assert.equal(done.stars[old177.id],true);
}
async function live(p){
 await open(p);await action(p,'test-pick').and(p.locator('[data-test=test-03]')).click();
 await action(p,'test-reading').and(p.locator('[data-test=test-03]')).click();
 await action(p,'question-grid').click();await action(p,'jump').and(p.locator('[data-index="75"]')).click();
 const g=group(current,'t03-g069-r2');await checkQuiz(p,modern,g,true);
 assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Horizontal overflow');
 const id=(await state(p)).active.id;
 await option(p,modern[0],'C').click();await option(p,modern[1],'D').click();
 await checkQuiz(p,modern,g,true);
 await p.reload();await action(p,'resume').click();await checkQuiz(p,modern,g,true);
 assert.equal(await option(p,modern[0],'C').getAttribute('aria-pressed'),'true');
 const done=await finish(p,id,1,100);compareAttempts(done,id,modern,false);
 for(const q of modern.slice(0,3)){
  await action(p,'view-explanation').and(p.locator('[data-id="'+q.id+'"]')).click();
  assert.equal(canon(await p.locator('.translation').textContent()),canon(q.promptZh));
  assert.equal(canon(await p.locator('.passage-text.zh').textContent()),canon(g.passageZh));
  assert.equal(await p.locator('.rationale').count(),4);
  await action(p,'back-review').first().click();
 }
}
(async()=>{
 for(const [f,expected] of [[currentPackPath,sha(currentBytes)],['data/catalog.js',sha(catalogBytes)],[svg,graphicSHA]]){
  const r=await fetch(url(f),{redirect:'manual'});assert.ok(r.ok&&r.url===url(f));assert.equal(sha(Buffer.from(await r.arrayBuffer())),expected);
 }
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',
  headless:process.env.HEADED!=='1',args:['--disable-dev-shm-usage']});
 try {
  await inContext(browser,archived,{width:1360,height:850});
  await inContext(browser,live,{width:390,height:844});
  await inContext(browser,live,{width:1360,height:850});
  console.log('Cedar code-path probes passed; not a substitute for the complete release runbook or native mobile.');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
