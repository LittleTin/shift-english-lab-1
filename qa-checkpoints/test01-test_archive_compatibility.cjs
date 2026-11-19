// Node render/state regression tests (no browser or audio decoder required).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const at=f=>path.join(__dirname,'..',f);
const source=fs.readFileSync(at('assets/app.js'),'utf8');
const pack=JSON.parse(fs.readFileSync(at('data/test-01.json'),'utf8'));
function load() {
  const window={addEventListener:()=>{},SHIFT_CATALOG:{tests:[{id:pack.testId}]},SHIFT_PACKS:[pack]};
  const ctx={window,setInterval:()=>0,document:{getElementById:()=>({addEventListener:()=>{}}),addEventListener:()=>{}},console};
  const i=source.indexOf('boot().catch(');
  assert.ok(i>0,'app boot marker missing');
  vm.runInNewContext(source.slice(0,i)+`
    registerPack(window.SHIFT_PACKS[0]);
    globalThis.api={setState(s){state=normalizeState(s)}, getState:()=>state, question:id=>Q.get(id),
      current:allQuestions,quiz:quizPage, results:resultPage,
      review(id,a){reviewDetail={questionId:id,attempt:a};route='answer-review';return reviewDetailPage()},
      frames(id){return groupFrames(G.get(id))}};
  })();`,ctx);
  return ctx.api;
}
function backup(q) {
  const t=1000000000000, id='done';
  const wrong=q.options.find(o=>o.id!==q.answer).id;
  const common={title:'Old Test 01',mode:'exam',questionIds:[q.id],startedAt:t,answers:{[q.id]:wrong}};
  const attempt={id:id+':'+q.id,questionId:q.id,testId:q.testId,selected:wrong,correctAnswer:q.answer,revision:q.revision||1,correct:false,at:t+3000,part:q.part,topic:q.topic};
  return {formatVersion:1,attempts:[attempt],sessions:[{...common,id,correct:0,total:1,answered:1,finishedAt:t+4000}],
    notes:{[q.id]:'Original note'},stars:{[q.id]:true},
    active:{...common,id:'continue',index:0,deadline:t+8000,testIds:[q.testId],examVersion:2,audioEdition:'toeic-1',examPhase:'listening',audioUsed:{[q.groupId]:{status:'started',unlockAt:t+7000,offset:1.5,frame:1}}}};
}
for (const number of [1,3]) test('Q'+number+' restores old image and answer in an unfinished formal session and review',()=>{
  const api=load(),q=pack.legacyQuestions.find(x=>x.number===number&&x.archivedImage);
  const current=pack.questions.find(x=>x.number===number);
  const g=pack.groups.find(x=>x.id===q.groupId);
  assert.notEqual(g.image,q.archivedImage);
  for(const f of [g.image,q.archivedImage,g.audio]) assert.ok(fs.existsSync(at(f)),f);
  api.setState(backup(q));
  const a=api.getState().attempts[0];
  const html=api.quiz();
  assert.ok(html.includes('src="'+q.archivedImage+'"'));
  assert.ok(!html.includes(g.image));
  assert.ok(html.includes('aria-pressed="true"'));
  assert.ok(!html.includes(q.explanationZh));
  assert.ok(!html.includes('Correct answer '+q.answer));
  assert.ok(api.frames(g.id).some(f=>f.kind==='audio'&&fs.existsSync(at(f.src))));
  assert.equal(api.getState().active.audioUsed[g.id].offset,1.5);
  assert.equal(api.getState().active.audioUsed[g.id].status,'interrupted');
  assert.equal(api.getState().notes[q.id],'Original note');
  assert.equal(api.getState().stars[q.id],true);
  const result=api.results();
  assert.ok(result.includes('Incorrect · Your answer '+a.selected));
  assert.ok(!result.includes('The original pack was removed'));
  const old=api.review(q.id,a);
  assert.ok(old.includes('src="'+q.archivedImage+'"'));
  assert.ok(old.includes('Correct answer '+q.answer));
  const updated=api.review(current.id,null);
  assert.ok(updated.includes('src="'+g.image+'"'));
  assert.ok(!updated.includes(q.archivedImage));
});
test('legacy IDs resolve but are hidden from the pool for new sessions',()=>{
  const api=load();
  assert.equal(api.current().length,200);
  const active=new Set(api.current().map(q=>q.id));
  for(const old of pack.legacyQuestions){
    assert.ok(api.question(old.id));
    assert.ok(!active.has(old.id));
    assert.ok(pack.questions.some(q=>q.number===old.number));
  }
});
