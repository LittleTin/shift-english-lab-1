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
 return {url:g.audio,start,end,label:'Practice / Review: original audio'};
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
function addAudio(root,r){
 const row=el('section','','inspect-source'),label=el('strong',r.label);
 const span=el('p',r.end===null?'Original full track':r.start.toFixed(3)+' s to '+r.end.toFixed(3)+' s','hint');
 const reveal=el('button','Load playback range','btn small');reveal.type='button';
 row.append(label,span,el('code',r.url),el('br'),href(r.url,'Open original audio file'),el('br'),reveal);
 reveal.addEventListener('click',()=>{
  const audio=el('audio');audio.controls=true;audio.preload='metadata';audio.setAttribute('aria-label',r.label);
  audio.addEventListener('loadedmetadata',()=>{if(r.start>0&&audio.currentTime<r.start-.015)audio.currentTime=r.start},{once:true});
  audio.addEventListener('play',()=>{
   for(const other of result.querySelectorAll('audio'))if(other!==audio)other.pause();
   if(audio.currentTime<r.start-.015||(r.end!==null&&audio.currentTime>=r.end))audio.currentTime=r.start;
  });
  if(r.end!==null)audio.addEventListener('timeupdate',()=>{
   if(audio.currentTime>=r.end&&!audio.paused){audio.pause();audio.currentTime=r.end;}
  });
  audio.src=r.url+(r.end===null?'':'#t='+r.start+','+r.end);
  reveal.replaceWith(audio);
 });
 root.append(row);
}
function show(found){
 const {q,g,p,uuid,title,testNumber}=found;
 const card=el('section','','panel');
 const head=el('h2','Test '+testNumber+' · Part '+q.part+' · Q'+String(q.number).padStart(3,'0'));
 head.tabIndex=-1;card.append(head,el('p',title),el('p','UUID: '+uuid,'hint'),el('p','Question ID: '+q.id+(g?' · Group: '+g.id:''),'hint'),el('h3',q.prompt),el('p',q.promptZh,'translation'));
 if(g&&safeAsset(g.image,'image')){
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
 if(audio.length){card.append(el('h3','Original audio files and playback ranges'));for(const row of audio)addAudio(card,row);}
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
