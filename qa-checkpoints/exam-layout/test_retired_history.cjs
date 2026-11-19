const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.join(__dirname,'..');
const source=fs.readFileSync(path.join(root,'assets/app.js'),'utf8');
const input=JSON.parse(fs.readFileSync(path.join(root,'data/test-01.json'),'utf8'));
const stamp=1234567890000;
function check(t,attempt) {
  const p={...input};delete p.legacyQuestions;
  const window={addEventListener:()=>{},SHIFT_CATALOG:{tests:[{id:p.testId}]},SHIFT_PACKS:[p]};
  const old=input.legacyQuestions?.find(q=>q.number===1)?.id||'t01-q001-retired-test';
  assert.ok(!p.questions.some(x=>x.id===old));
  const id='attempt-archive1',answers={[old]:'D'};
  const record={id,title:'Old exam',mode:'exam',questionIds:[old],answers,startedAt:stamp,finishedAt:stamp+5000,correct:attempt?.correct?1:0,total:1,answered:1};
  const saved={formatVersion:1,attempts:attempt?[{id:id+':'+old,questionId:old,testId:p.testId,part:1,topic:'manufacturing',revision:1,selected:'D',at:stamp+4000,...attempt}]:[],sessions:[record],notes:{[old]:'Previous note'}};
  const ctx={saved,window,setInterval:()=>0,document:{getElementById:()=>({addEventListener:()=>{}}),addEventListener:()=>{}},console};
  const end=source.indexOf('boot().catch(');assert.ok(end>0);
  vm.runInNewContext(source.slice(0,end)+`registerPack(window.SHIFT_PACKS[0]);state=normalizeState(saved);globalThis.results=resultPage();globalThis.stateJson=JSON.stringify(state);globalThis.count=allQuestions().length;})();`,ctx);
  assert.equal(ctx.count,200);
  assert.match(ctx.results,/Previous question version/);
  assert.match(ctx.results,/Your answer: D/);
  assert.match(ctx.results,/Your original result is unchanged/);
  if(attempt){
    assert.match(ctx.results,new RegExp('Original correct answer: '+attempt.correctAnswer));
    assert.match(ctx.results,new RegExp('>'+(attempt.correct?'Correct':'Incorrect')+'<'));
  } else {
    assert.doesNotMatch(ctx.results,/Original correct answer:/);
    assert.match(ctx.results,/>Not recorded</);
  }
  const loaded=JSON.parse(ctx.stateJson);
  assert.deepEqual(loaded.sessions[0].answers,answers);
  assert.equal(loaded.sessions[0].correct,record.correct);
  assert.equal(loaded.notes[old],'Previous note');
}
test('historical answers, original answer key and score remain when a version is retired',t=>check(t,{correct:true,correctAnswer:'D'}));
test('older history without item-level outcome does not invent an answer key or grade',t=>check(t,null));
