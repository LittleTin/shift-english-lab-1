(function(){
'use strict';
const catalog=window.SHIFT_CATALOG;
const byId=id=>document.getElementById(id);
const form=byId('lookup'),input=byId('question-uuid'),result=byId('lookup-result'),status=byId('lookup-status');
const UUID=/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/;
const findUuid=raw=>String(raw||'').trim().toLowerCase();
const safeAsset=(url,kind)=>typeof url==='string'&&!url.includes('..')&&
 (kind==='audio'?/^audio\/[a-z0-9_.\/-]+\.(ogg|mp3|wav|m4a)$/i:/^assets\/[a-z0-9_.\/-]+\.(svg|jpe?g|png|webp)$/i).test(url);
const knownRoles={intro:'Introduction',direction:'Directions',example:'Unscored example',cue:'Question number cue',passage:'Formal test: question audio / shared passage',question:'Formal test: spoken question',closing:'Listening closing announcement'};
let lookupVersion=0, cached;
function loadPacks(){
 if(!cached)cached=Promise.all(catalog.tests.map(entry=>{
  if(!/^data\/test-[0-9]+\.js$/.test(entry.path))return Promise.reject(new Error('Invalid test pack path'));
  const ready=window.SHIFT_PACKS.find(p=>p.testId===entry.id);
  if(ready)return ready;
  return new Promise((resolve,reject)=>{
   const script=document.createElement('script');
   script.src=entry.path+(location.protocol==='file:'?'':'?v='+encodeURIComponent(catalog.assetRevision||catalog.version));
   script.onload=()=>{const found=window.SHIFT_PACKS.find(p=>p.testId===entry.id);found?resolve(found):reject(new Error('A built-in test pack is missing'))};
   script.onerror=()=>{script.remove();reject(new Error('A built-in test pack could not be loaded'))};
   document.head.append(script);
  });
 })).then(packs=>{
  const index=new Map();
  for(const [i,p] of packs.entries()){
   const gs=new Map(p.groups.map(g=>[g.id,g]));
   for(const q of p.questions){
    const uuid=window.SHIFT_QUESTION_UUID(q.id);
    if(index.has(uuid))throw new Error('Two questions have the same UUID');
    index.set(uuid,{uuid,q,g:gs.get(q.groupId),p,title:catalog.tests[i].title,testNumber:i+1});
   }
  }
  return index;
 }).catch(e=>{cached=null;throw e});
 return cached;
}
function el(tag,text='',className=''){
 const node=document.createElement(tag);node.textContent=text;if(className)node.className=className;return node;
}
function href(url,text){
 const a=el('a',text);a.href=url;a.target='_blank';a.rel='noopener';return a;
}
function practiceRange(g){
 if(!g||!safeAsset(g.audio,'audio'))return null;
 const start=Number.isFinite(g.audioStart)&&g.audioStart>=0?g.audioStart:0;
 const end=Number.isFinite(g.audioEnd)&&g.audioEnd>start?g.audioEnd:null;
 const isolated=g.audio===`audio/practice-groups/${g.testId}/${g.id}.ogg`&&start===0&&end===g.duration;
 return {url:g.audio,start,end,label:isolated?'Practice / Review: complete group file (from 0 seconds)':'Practice / Review: original audio'};
}
function inspectRanges(q,g,p){
 const out=[];
 const practice=practiceRange(g);
 if(practice)out.push(practice);
 const whole=g&&p.listeningPlan?.groupAudio?.[g.id];
 if(whole&&safeAsset(whole.src,'audio')&&Number.isFinite(whole.duration)&&whole.duration>0){
  out.push({url:whole.src,start:0,end:whole.duration,label:'Formal test: complete group file (from 0 seconds)'});
  return out;
 }
 if(g)for(const f of p.listeningPlan?.frames||[]){
  if(f.kind!=='audio'||f.groupId!==g.id||(f.questionId&&f.questionId!==q.id)||!Object.hasOwn(knownRoles,f.role)||!safeAsset(f.src,'audio'))continue;
  if(!Number.isFinite(f.start)||!Number.isFinite(f.end)||f.start<0||f.end<=f.start)continue;
  out.push({url:f.src,start:f.start,end:f.end,label:knownRoles[f.role]});
 }
 return out;
}
function audioSource(root,r){
 const row=el('div','','inspect-source');
 row.append(el('strong',r.label),el('p',r.end===null?'Original full track':r.start.toFixed(3)+' s to '+r.end.toFixed(3)+' s','hint'),el('code',r.url),el('br'),href(r.url,'Open original audio file'));
 root.append(row)
}
function addPlayers(card,uuid,g,p){
 const row=el('div','','debug-meta');
 for(const [mode,label,available] of [
  ['practice','Open Practice Player',practiceRange(g)],
  ['exam','Open Formal Test Player',g&&p.listeningPlan?.frames?.some(f=>f.groupId===g.id)]
 ]){
  if(!available)continue;
  const a=el('a',label,'btn primary');
  a.href='index.html?'+new URLSearchParams({diagnostic:uuid,mode}).toString();
  row.append(a);
 }
 if(row.firstChild)card.append(el('h3','Reproduce playback with the site player'),row,el('p','Opens the actual exam or practice player at this group. No answers or progress are saved. The file links below are only for inspecting the source.','hint'));
}
function show(found){
 const {q,g,p,uuid,title,testNumber}=found;
 const card=el('section','','panel');
 const head=el('h2','Test '+testNumber+' · Part '+q.part+' · Q'+String(q.number).padStart(3,'0'));
 head.tabIndex=-1;card.append(head,el('p',title),el('p','UUID: '+uuid,'hint'),el('p','Question ID: '+q.id+(g?' · Group: '+g.id:''),'hint'),el('h3',q.prompt),el('p',q.promptZh,'translation'));
 const scopedChart=(
  p.testId==='test-08'&&g?.id==='t08-g059'&&g.image==='assets/scenes/test-08/bench-site-survey-list.jpg'&&g.chartWidthPx===720?'t08-q060':
  p.testId==='test-08'&&g?.id==='t08-g089'&&g.image==='assets/scenes/test-08/paper-scraps-worktop.jpg'&&g.chartWidthPx===1170?'t08-q090':'');
 if(g&&safeAsset(g.image,'image')&&(!scopedChart||q.id===scopedChart)){
  const img=el('img');img.src=g.image;img.alt=g.imageAlt||'Original question image';
  card.append(img,el('p',g.image,'hint'),href(g.image,'Open original image'));
 }
 if(g&&(g.passage||g.passageZh)){
  const source=el('details');source.append(el('summary',q.part<5?'Show transcript':'Show passage'));
  if(g.passage)source.append(el('pre',g.passage));
  if(g.passageZh)source.append(el('pre',g.passageZh,'translation'));
  card.append(source);
 }
 card.append(el('h3','Answer choices'));
 const options=el('ul');
 for(const o of q.options){const line=el('li');line.append(el('strong',o.id+'. '+o.text),el('p',o.zh,'translation'));options.append(line)}
 card.append(options);
 const details=el('details');
 details.append(el('summary','Show answer and explanation'),el('p','Correct answer: '+q.answer),el('p',q.explanationZh));
 for(const o of q.options)if(o.whyZh)details.append(el('p',o.id+'. '+o.whyZh));
 card.append(details);
 const audio=inspectRanges(q,g,p);
 if(audio.length){addPlayers(card,uuid,g,p);card.append(el('h3','Original audio files and playback ranges'));for(const row of audio)audioSource(card,row);}
 result.replaceChildren(card);head.focus({preventScroll:true});
}
function clearResult(){
 for(const a of result.querySelectorAll('audio'))a.pause();
 result.replaceChildren();
}
async function lookup(raw){
 const token=++lookupVersion,uuid=findUuid(raw);clearResult();status.textContent='';
 if(!UUID.test(uuid)){status.textContent='Enter a valid question UUID.';return;}
 input.value=uuid;status.textContent='Looking up question…';
 try{
  const map=await loadPacks();if(token!==lookupVersion)return;
  const found=map.get(uuid);
  if(!found){status.textContent='No built-in question matches this UUID.';return;}
  status.textContent='Question found.';show(found);
 }catch(e){if(token===lookupVersion)status.textContent='Could not load the question bank. Try again or check that all site files are available.'}
}
form.addEventListener('submit',e=>{e.preventDefault();void lookup(input.value)});
const fromLink=new URLSearchParams(location.search).get('uuid');
if(fromLink){input.value=fromLink.substring(0,60);void lookup(input.value)}
})();
