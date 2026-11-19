'use strict';
const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync(process.argv[2],'utf8');
const make=(id,q=`${id}:q`)=>({schemaVersion:1,testId:id,groups:[],questions:[{id:q,testId:id,number:1,part:5,topic:'technology',difficulty:'foundation',prompt:id,promptZh:'題目',explanationZh:'解析',options:['A','B','C','D'].map(id=>({id,text:id,zh:'中',whyZh:'解'})),answer:'A'}]});
const official=make('test-01','official-q'),future=make('test-04');
official.listeningPlan={audioEdition:'toeic-1',frames:[]};
function harness(preloaded=[]){
 const node={addEventListener(){},classList:{add(){},remove(){}},querySelectorAll(){return []}};
 const win={SHIFT_CATALOG:{version:'1.4.2',tests:[{id:'test-01',title:'Official',path:'data/test-01.js'},{id:'test-04',title:'Future',path:'data/test-04.js'}]},SHIFT_PACKS:preloaded.slice(),addEventListener(){}};
 const calls=[];
 const doc={getElementById:()=>node,addEventListener(){},createElement:()=>({}),head:{append(script){calls.push(script.src);win.SHIFT_PACKS.push(script.src.includes('test-01')?official:future);queueMicrotask(script.onload)}}};
 const c=vm.createContext({window:win,document:doc,location:{protocol:'https:'},setInterval(){},setTimeout(){},clearTimeout(){},console:{warn(){},error(){}}});
 const i=src.lastIndexOf('boot().catch(');assert.ok(i>0);
 vm.runInContext(src.slice(0,i)+`this.api={normalizeState,loadTest,allTests,registerPack,installPackIndexes,formalPlan,resume,sessionOutcomes,
  setState(v){state=v},getQuestion(id){return Q.get(id)}};}).call(this);`,c);
 return {a:c.api,calls};
}
const history={formatVersion:1,attempts:[{id:'result:official-q',questionId:'official-q',testId:'test-01',part:5,topic:'technology',at:10,selected:'B',correct:false,correctAnswer:'C'}],sessions:[{id:'result',mode:'practice',title:'Original',questionIds:['official-q'],answers:{'official-q':'B'},startedAt:5,finishedAt:20,correct:0,total:1,answered:1}],stars:{'official-q':true},notes:{'official-q':'Keep me'}};
test('stored scores, remembered answer key, notes and stars survive reserved pack filtering',()=>{
 const {a}=harness(); const s=a.normalizeState({...history,importedPacks:[make('test-01'),make('ordinary')]});
 assert.deepEqual(Array.from(s.importedPacks,p=>p.testId),['ordinary']); assert.equal(s.attempts[0].correctAnswer,'C'); assert.equal(s.sessions[0].correct,0); assert.equal(s.sessions[0].total,1); assert.equal(s.notes['official-q'],'Keep me'); assert.equal(s.stars['official-q'],true);
 a.setState(s);assert.equal(a.sessionOutcomes(s.sessions[0]).get('official-q'),false);
});
test('catalog entries and future installations resolve official factory; ordinary custom remains available',async()=>{
 const {a,calls}=harness();
 a.setState(a.normalizeState({...history,importedPacks:[make('test-01'),make('test-04'),make('ordinary')]}));
 await a.installPackIndexes();
 assert.deepEqual(Array.from(a.allTests(),p=>p.title),['Official','Future','ordinary']);
 assert.equal(a.getQuestion('official-q'),official.questions[0]);assert.equal(a.getQuestion('ordinary:q').testId,'ordinary');
 assert.equal(a.formalPlan({testId:'test-01'},{audioEdition:'toeic-1'}),official.listeningPlan);
 assert.deepEqual(calls,['data/test-01.js?v=1.4.2','data/test-04.js?v=1.4.2']);
});
test('explicit source namespace and globally owned question IDs are enforced before writes',async()=>{
 const {a}=harness([official,future]); a.setState(a.normalizeState({...history,importedPacks:[make('ordinary','official-q'),make('other')]}));
 await a.installPackIndexes();
 assert.deepEqual(Array.from(a.allTests(),p=>p.id),['test-01','test-04','other']);
 assert.equal(a.getQuestion('official-q'),official.questions[0]);
 assert.throws(()=>a.registerPack(make('test-01')),/namespace/);
 assert.throws(()=>a.registerPack(make('unknown'),true),/namespace/);
 assert.throws(()=>a.registerPack(make('colliding','official-q')),/already exists/);
});
test('active compatibility conflict is kept and not silently resumed against other content',async()=>{
 const {a}=harness();
 const active={id:'your-session',mode:'practice',title:'Saved',questionIds:['official-q'],answers:{'official-q':'B'},startedAt:10,testIds:['test-01'],index:0};
 const protectedState=a.normalizeState({...history,active,importedPacks:[make('test-01')]});
 assert.equal(protectedState.active.reservedPackConflict,true);
 assert.equal(protectedState.active.answers['official-q'],'B');
 assert.equal(a.normalizeState(protectedState).active.reservedPackConflict,true);
 a.setState(protectedState);await assert.rejects(a.resume(),/original pack is not available/);
 assert.equal(a.normalizeState({...history,active,importedPacks:[make('ordinary')]}).active.reservedPackConflict,undefined);
});
