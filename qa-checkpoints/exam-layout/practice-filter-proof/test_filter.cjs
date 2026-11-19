const {test}=require('node:test'),assert=require('node:assert/strict');
const {readFileSync}=require('node:fs'),vm=require('node:vm');
const app=readFileSync(process.argv[2]||require('node:path').join(__dirname,'candidate-app.js'),'utf8');
const begin=app.indexOf('function filteredGroupSelection('),end=app.indexOf('async function startFiltered(',begin);
assert.ok(begin>=0&&end>begin);
const select=vm.runInNewContext('const shuffle=a=>a.slice();'+app.slice(begin,end)+';filteredGroupSelection');
const f={section:'all',part:'all',topic:'all',difficulty:'all',accent:'all',count:10,unseen:false};
const item=(number,{testId='test-01',groupId='g',part=3,difficulty='intermediate',topic='business'}={})=>({number,id:`${testId}-q${number}`,testId,groupId,part,difficulty,topic});
const ids=qs=>Array.from(qs,x=>x.id);
test('hard filters never bring excluded siblings along or split a group',()=>{
 const rows=[item(1),item(2,{difficulty:'advanced'}),item(3,{groupId:'h'}),item(4,{groupId:'h',topic:'daily'})];
 assert.deepEqual(ids(select(rows,{...f,difficulty:'intermediate',topic:'business'})),[]);
 assert.deepEqual(ids(select(rows,{...f,count:1})),ids(rows.slice(0,2)));
});
test('the same raw group ID does not cross test boundaries',()=>{
 const a=item(1),b=item(1,{testId:'test-02'});
 assert.deepEqual(ids(select([a,b],{...f,count:1})),[a.id]);
});
test('unanswered priority remains whole-group and can fill from seen groups',()=>{
 const a=item(1),b=item(2),c=item(3,{groupId:'h'}),d=item(4,{groupId:'i'}),e=item(5,{groupId:'i'});
 const has=id=>[a.id,c.id].includes(id);
 assert.deepEqual(ids(select([a,b,c,d,e],{...f,count:3,unseen:true},undefined,has)),[d.id,e.id,a.id,b.id]);
 assert.deepEqual(ids(select([a,b,c,d,e],{...f,unseen:true},undefined,has)),[d.id,e.id,a.id,b.id,c.id]);
});
test('one accent excludes mixed, unlabelled or wrong-owned groups and nonlistening',()=>{
 const a=item(1),b=item(2),c=item(3,{groupId:'mixed'}),d=item(4,{groupId:'unknown'}),e=item(5,{groupId:'other'}),r=item(6,{groupId:'reading',part:7});
 const get=k=>({g:{testId:'test-01',audioSpeakers:[{locale:'en-US'},{locale:'en-US'}]},mixed:{testId:'test-01',audioSpeakers:[{locale:'en-US'},{locale:'en-GB'}]},unknown:{testId:'test-01'},other:{testId:'test-02',audioSpeakers:[{locale:'en-US'}]},reading:{testId:'test-01',audioSpeakers:[{locale:'en-US'}]}})[k];
 assert.deepEqual(ids(select([a,b,c,d,e,r],{...f,accent:'en-US'},get)),[a.id,b.id]);
});
test('real Test03 mixed-difficulty groups are not partially included',()=>{
 const p=JSON.parse(readFileSync('shift-next/data/test-03.json','utf8'));
 const out=select(p.questions,{...f,difficulty:'intermediate',count:600});
 assert.ok(out.length>0);
 assert.ok(out.every(q=>q.difficulty==='intermediate'));
 for(const q of out){if(!q.groupId)continue;assert.equal(out.filter(v=>v.groupId===q.groupId).length,p.questions.filter(v=>v.groupId===q.groupId).length)}
 assert.equal(out.some(q=>q.groupId==='t03-g032'),false);
});
