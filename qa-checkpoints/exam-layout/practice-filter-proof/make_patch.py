from pathlib import Path
import difflib,sys
src=Path(sys.argv[1])
s=src.read_text()
anchor=s.index('async function startFiltered(override)')
end=s.index('function questionByActive()',anchor)
old=s[anchor:end]
assert old.count('const qs=groupedSelection(pool,Number(f.count));')==1
new="""function filteredGroupSelection(questions,f,getGroup=key=>G.get(key),hasAttempt=id=>!!state.stats[id]){
 const bucket=new Map();
 for(const q of questions){
  const key=JSON.stringify(q.groupId?[q.testId,'group',q.groupId]:[q.testId,'single',q.id]);
  if(!bucket.has(key))bucket.set(key,[]);
  bucket.get(key).push(q)
 }
 const matches=q=>(f.section==='all'||(f.section==='reading'?q.part>4:q.part<5))&&
  (f.part==='all'||q.part===Number(f.part))&&(f.topic==='all'||q.topic===f.topic)&&
  (f.difficulty==='all'||q.difficulty===f.difficulty);
 const unseen=[[],[],[]];
 for(const group of bucket.values()){
  if(!group.every(matches))continue;
  if(f.accent!=='all'){
   const q=group[0],owner=getGroup(q.groupId),voices=owner?.audioSpeakers;
   if(group.some(v=>v.part>4)||owner?.testId!==q.testId||!Array.isArray(voices)||!voices.length||
      !voices.every(v=>v?.locale===f.accent))continue;
  }
  const attempted=f.unseen?group.filter(q=>hasAttempt(q.id)).length:0;
  unseen[attempted===0?0:attempted<group.length?1:2].push(group.slice().sort((a,b)=>a.number-b.number))
 }
 const chosen=[];
 for(const g of unseen.flatMap(shuffle)){
  if(chosen.length>=Number(f.count))break;
  chosen.push(...g)
 }
 return chosen
}
"""
old_pool="let pool=allQuestions().filter(q=>(f.section==='all'||(f.section==='reading'?q.part>4:q.part<5))&&(f.part==='all'||q.part===Number(f.part))&&(f.topic==='all'||q.topic===f.topic)&&(f.difficulty==='all'||q.difficulty===f.difficulty)&&(!f.unseen||!state.stats[q.id])&&accentMatches(q,f.accent));const qs=groupedSelection(pool,Number(f.count));"
assert old_pool in old
new+=old.replace(old_pool,"const qs=filteredGroupSelection(allQuestions(),f);")
tail_start=new.index('const title=f.accent')
tail_end=new.index('await startSession(qs,title)',tail_start)
new=new[:tail_start]+"const label=f.accent!=='all'?ACCENTS[f.accent]+' focused practice':f.topic==='all'?'Daily Practice':TOPICS[f.topic]+' practice session';const short=qs.length<Number(f.count);const title=label+(short||f.accent!=='all'?' · '+qs.length+' questions':'')+(short?' (target '+f.count+'; not enough matching full groups)':'');"+new[tail_end:]
v=s[:anchor]+new+s[end:]
hint='Passages and conversations are selected as complete groups, so the question count may vary.'
assert v.count(hint)==1
v=v.replace(hint,hint+' If a topic or difficulty does not apply to every question in a group, that group is skipped. Prioritizing unanswered questions tries new groups first without splitting them.')
Path(sys.argv[2]).write_text(v)
Path(sys.argv[3]).write_text(''.join(difflib.unified_diff(s.splitlines(True),v.splitlines(True),fromfile='a/assets/app.js',tofile='b/assets/app.js')))
