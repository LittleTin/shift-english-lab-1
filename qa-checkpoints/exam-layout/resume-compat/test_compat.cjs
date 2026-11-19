const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const base=__dirname, previous=path.join(base,'fixture'), active=path.join(base,'../acceptance/rebuilt');
const stamp=1234567890000;
const qId='t01-q001', testId='test-01';
const meta=JSON.parse(fs.readFileSync(path.join(previous,'resume-overlay-manifest.json')));
const app=fs.readFileSync(path.join(base,'app-patched.js'),'utf8');
let media;
function harness(t, mutate){
 const packs=['01','02','03'].map(n=>JSON.parse(fs.readFileSync(path.join(active,'data','test-'+n+'.json'))));
 const doc=new EventTarget();
 const timer=new Set();
 media=new EventTarget();
 Object.assign(media,{paused:true,seeking:false,error:null,src:null,currentTime:0,plays:[],load(){},pause(){this.paused=true},play(){this.paused=false;this.plays.push([this.src,this.currentTime]);return Promise.resolve()},getAttribute(){return this.src},removeAttribute(){this.src=null;}});
 doc.hidden=false;
 doc.getElementById=id=>id==='audio-player'?media:null;
 doc.querySelector=()=>null;
 doc.createElement=()=>({});
 doc.head={append(el){try{vm.runInContext(fs.readFileSync(path.join(previous,el.src),'utf8'),ctx);el.onload()}catch(e){el.onerror()}}};
 const window={SHIFT_CATALOG:{version:'2.0.0-qa',tests:packs.map(p=>({id:p.testId})),resumeSnapshots:meta.catalogEntries},SHIFT_PACKS:packs,scrollTo(){},crypto:require('node:crypto').webcrypto};
 const ctx=vm.createContext({window,document:doc,performance,console,crypto:require('node:crypto').webcrypto,setInterval(fn,n){const i=setInterval(fn,n);timer.add(i);return i},clearInterval(i){timer.delete(i);clearInterval(i)}});
 const at=app.indexOf('boot().catch(');assert.ok(at>0);
 vm.runInContext(app.slice(0,at)+`
  for(const p of window.SHIFT_PACKS)registerPack(p);
  render=()=>{};notify=()=>{};
  globalThis.api={save(x){state=normalizeState(x)},state:()=>state,resume,finish:()=>finishSession(true),formalRun:()=>runFormalGroup(sessionGroup(questionByActive().groupId)),current:questionByActive,group:id=>sessionGroup(id),frames:id=>groupFrames(sessionGroup(id)),activeCount:()=>allQuestions().length,contains:id=>Q.has(id),stop:stopAudio};
 })();`,ctx);
 const s={id:'snapshot-old',title:'Old retained test',mode:'exam',questionIds:[qId,...packs[0].questions.slice(1).map(q=>q.id)],testIds:[testId],index:0,startedAt:stamp,deadline:stamp+100000,answers:{[qId]:'A'},audioEdition:'toeic-1',examPhase:'listening',examVersion:2,audioUsed:{'t01-g001':{status:'started',unlockAt:0,frame:1,offset:0.7}}};
 mutate?.(s,packs);
 ctx.api.save({formatVersion:1,attempts:[],sessions:[],notes:{[qId]:'My prior note'},active:s});
 t.after(()=>{ctx.api.stop();for(const i of timer)clearInterval(i)});
 return {api:ctx.api,packs,media};
}
test('resume original full exam, source and audio position; original ID not added to active pool',async t=>{
 const {api,media}=harness(t,(s,packs)=>{
  // Full sessions started on the older commit also include its older IDs in
  // later positions. Load that immutable deployed list, not an invented mix.
  const sandbox={window:{}};vm.runInNewContext(fs.readFileSync(path.join(previous,meta.catalogEntries[testId].path),'utf8'),sandbox);
  s.questionIds=Array.from(sandbox.window.SHIFT_RESUME_SNAPSHOTS['1.4.1'][testId].questions,q=>q.id);
 });
 assert.equal(api.activeCount(),600);
 assert.equal(api.contains(qId),false);
 await api.resume();
 assert.equal(api.current().id,qId);
 assert.equal(api.group('t01-g001').image,'assets/scenes/warehouse.svg');
 assert.equal(api.activeCount(),600);
 assert.equal(api.contains(qId),false);
 assert.equal(api.state().active.answers[qId],'A');
 assert.equal(api.state().notes[qId],'My prior note');
 void api.formalRun();
 const expected=api.frames('t01-g001')[1];
 assert.ok(!expected.src.startsWith('audio/exams/'));
 assert.ok(fs.existsSync(path.join(previous,expected.src)));
 assert.deepEqual(media.plays[0],[expected.src,expected.start+0.7]);
 await api.finish();
 const rec=api.state().attempts.find(a=>a.questionId===qId);
 assert.equal(rec.correct,true);
 assert.equal(rec.correctAnswer,'A');
 assert.equal(api.state().sessions[0].correct,1);
 assert.equal(api.activeCount(),600);
});
test('new-version sessions stay on current relocated WAV, never old pack',async t=>{
 const {api,packs,media}=harness(t,(s,packs)=>{
  s.questionIds=packs[0].questions.map(q=>q.id);
  s.answers={[s.questionIds[0]]:'B'};
  s.contentVersion='2.0.0-qa';
 });
 await api.resume();
 assert.equal(api.current().id,packs[0].questions[0].id);
 void api.formalRun();
 assert.match(media.plays[0][0],/^audio\/exams\/test-01/);
 assert.equal(media.plays[0][1],0.7);
 assert.equal(api.activeCount(),600);
});
test('unknown version or outside verified epoch is preserved without blind remap',async t=>{
 const {api}=harness(t,s=>{s.startedAt=900000000000});
 const before=JSON.stringify(api.state().active);
 await assert.rejects(api.resume(),/cannot be confirmed/);
 assert.equal(JSON.stringify(api.state().active),before);
 assert.equal(api.activeCount(),600);
});
test('unavailable original ID is preserved even when date fits, never guessed',async t=>{
 const {api}=harness(t,s=>{s.questionIds=['t01-unknown-past'];s.answers={'t01-unknown-past':'A'}});
 const before=JSON.stringify(api.state().active);
 await assert.rejects(api.resume(),/original question version is missing/i);
 assert.equal(JSON.stringify(api.state().active),before);
 assert.equal(api.activeCount(),600);
});
