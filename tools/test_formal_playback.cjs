// Run with node --test tools/test_formal_playback.cjs. Uses a media stub to
// exercise visibility and playback failures without waiting for a 45-minute test.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { performance } = require('node:perf_hooks');

const script = fs.readFileSync(require('node:path').join(__dirname, '../assets/app.js'), 'utf8');
const boot = 'boot().catch(';
assert.ok(script.indexOf(boot) > 0);
const exposed = script.slice(0, script.indexOf(boot)) + `
  render=()=>{};
  notify=()=>{};
  globalThis.appTest={
    setSession(s,p){state.active=s;state.importedPacks=[p];p.groups.forEach(g=>G.set(g.id,g));p.questions.forEach(q=>Q.set(q.id,q));route='quiz';},
    getSession:()=>state.active, run:id=>runFormalGroup(G.get(id)), stop:stopAudio, ready:id=>groupReady(G.get(id)),
    remaining:()=>examSeconds(state.active), normalize:s=>normalizeState(s), card:id=>audioCard(G.get(id))
  };
})();`;

class Media extends EventTarget {
  paused=true; seeking=false; ended=false; error=null; currentTime=0;
  calls=[]; rejectNext=false; src=null;
  getAttribute(){return this.src}
  removeAttribute(){this.src=null}
  load(){this.currentTime=0;this.ended=false}
  play(){
    this.calls.push(this.currentTime);
    if(this.rejectNext){
      this.rejectNext=false;
      return Promise.reject(new Error('autoplay denied'));
    }
    this.paused=false;
    return Promise.resolve();
  }
  pause(){
    const notify=!this.paused;
    this.paused=true;
    if(notify)this.dispatchEvent(new Event('pause'));
  }
  time(t){this.currentTime=t;this.dispatchEvent(new Event('timeupdate'))}
}
function fixture(t){
  const audio=new Media(), document=new EventTarget(), timers=new Set();
  document.hidden=false;
  document.getElementById=id=>id==='audio-player'?audio:null;
  document.querySelector=()=>null;
  const ctx={document,console,performance,window:{scrollTo(){}},
    setInterval(fn,n){const timer=setInterval(fn,n);timers.add(timer);return timer},
    clearInterval(timer){timers.delete(timer);clearInterval(timer)}};
  vm.runInNewContext(exposed,ctx);
  const app=ctx.appTest;
  t.after(()=>{app.stop();for(const timer of timers)clearInterval(timer)});
  const s={id:'s1',mode:'exam',examVersion:2,examPhase:'listening',audioEdition:'toeic-1',
    index:0,questionIds:['q1','q2','q3'],audioUsed:{},answers:{},testIds:['t1']};
  const g1={id:'g1',testId:'t1'}, g2={id:'g2',testId:'t1'};
  const clip=(groupId,start,end)=>({src:'audio/clip.mp3',kind:'audio',groupId,start,end,duration:end-start});
  const pack={testId:'t1',groups:[g1,g2],questions:[
    {id:'q1',part:1,groupId:'g1'},{id:'q2',part:2,groupId:'g2'},{id:'q3',part:5}
  ],listeningPlan:{duration:5.2,frames:[
    clip('g1',4,6),{kind:'silence',groupId:'g1',duration:.2},clip('g1',7,8),clip('g2',9,11)
  ]}};
  app.setSession(s,pack);
  const hide=hidden=>{document.hidden=hidden;document.dispatchEvent(new Event('visibilitychange'))};
  return {audio,app,s,hide,pack};
}
const wait=ms=>new Promise(r=>setTimeout(r,ms));

test('switching tabs freezes the timer and resumes at the current position',async t=>{
  const {audio,app,s,hide}=fixture(t);
  void app.run('g1');audio.time(4.8);
  hide(true);
  assert.equal(audio.paused,true);
  assert.equal(s.audioUsed.g1.status,'interrupted');
  assert.equal(app.ready('g1'),false);
  const remaining=app.remaining();
  await wait(40);
  assert.equal(app.remaining(),remaining);
  hide(false);
  assert.deepEqual(audio.calls,[4,4.8]);
  assert.equal(audio.paused,false);
});

test('blocked automatic playback and unexpected media pauses can be retried',async t=>{
  const {audio,app,s,hide}=fixture(t);
  void app.run('g1');audio.time(5.25);
  hide(true);audio.rejectNext=true;hide(false);
  await wait(35);
  assert.match(app.card('g1'),/aria-label="Resume Listening" >/);
  assert.equal(app.ready('g1'),false);
  void app.run('g1');
  assert.equal(audio.calls.at(-1),5.25);
  audio.time(5.5);audio.pause();
  await wait(35);
  assert.equal(s.audioUsed.g1.offset,1.5);
  void app.run('g1');
  assert.equal(audio.calls.at(-1),5.5);
});

test('cutaway during answer time preserves it, then advances without replay; reading starts at 75 minutes',async t=>{
  const {audio,app,s,hide}=fixture(t);
  void app.run('g1');audio.time(6);await wait(15);
  assert.equal(s.audioUsed.g1.frame,1);
  hide(true);await wait(250);
  assert.equal(s.audioUsed.g1.frame,1);
  hide(false);await wait(260);
  assert.equal(audio.calls.at(-1),7);
  audio.time(8);await wait(20);
  assert.equal(s.index,1);
  assert.equal(s.audioUsed.g1.status,'ended');
  assert.equal(audio.calls.at(-1),9);
  await app.run('g1');assert.equal(audio.calls.at(-1),9);
  audio.time(11);await wait(20);
  assert.equal(s.examPhase,'reading');
  assert.equal(s.index,2);
  assert.ok(app.remaining()>4498&&app.remaining()<=4500);
});

test('checkpoint and previous-format attempts retain their saved answers',async t=>{
  const {audio,app,s,pack}=fixture(t);
  const snapshot={formatVersion:1,attempts:[],sessions:[],active:{
    ...s,title:'Practice',startedAt:1,deadline:2,answers:{q1:'C'},audioUsed:{g1:{status:'started',unlockAt:0,frame:2,offset:.5}}
  }};
  const saved=app.normalize(snapshot).active;
  assert.equal(saved.answers.q1,'C');
  assert.equal(saved.audioUsed.g1.status,'interrupted');
  app.setSession(saved,pack);void app.run('g1');
  assert.equal(audio.calls.at(-1),7.5);
  app.stop();
  snapshot.active.audioUsed.g1={status:'interrupted',unlockAt:2};
  const legacy=app.normalize(snapshot).active;
  app.setSession(legacy,pack);void app.run('g1');
  assert.equal(audio.calls.at(-1),4);
  assert.equal(legacy.answers.q1,'C');
});
