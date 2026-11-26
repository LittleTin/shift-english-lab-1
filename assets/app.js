(function(){
'use strict';
const VERSION=window.SHIFT_CATALOG?.releaseLabel||window.SHIFT_CATALOG?.version||'';
const SYNC_MODULE_URL='./shift-sync.mjs?v=account-resume-v2';
const BACKUP_TIME_KEY='shift-english-last-export-v1';
let lastExportAt=0;
const NOTE_DRAFT_KEY='shift-english-note-draft-v1';
const noteTokens=new Map(),noteStatuses=new Map();
let noteGeneration=0;
const TOPICS={technology:'Technology & Development',manufacturing:'Manufacturing & Supply Chain',business:'Business & Office',daily:'Daily Life & Travel'};
const DIFFICULTY={foundation:'Foundation',intermediate:'Intermediate',advanced:'Advanced'};
const PARTS={1:'Photographs',2:'Question–Response',3:'Conversations',4:'Talks',5:'Incomplete Sentences',6:'Text Completion',7:'Reading Comprehension'};
const ICONS={account:'M16 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM4 21v-1a8 8 0 0 1 16 0v1',device:'M6 3h12v18H6zM10 18h4',cloud:'M8 18H6a4 4 0 1 1 1.1-7.85A6 6 0 0 1 19 11a3.5 3.5 0 0 1-.5 7H8',sync:'M20 8a8 8 0 0 0-14-2L3 9m0-5v5h5m-4 7a8 8 0 0 0 14 2l3-3m0 5v-5h-5',home:'M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9',book:'M3 4h6a4 4 0 0 1 3 2 4 4 0 0 1 3-2h6v15h-6a4 4 0 0 0-3 2 4 4 0 0 0-3-2H3zM12 6v15',review:'M3 11a9 9 0 1 1 3 7M3 5v6h6M12 7v5l3 2',star:'m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z',chart:'M4 3v18h17M8 16v-4M13 16V8M18 16V5',folder:'M3 6h7l2 3h9v12H3zM3 6V4h7l2 2h7v3',arrow:'M4 12h16M14 6l6 6-6 6',back:'M20 12H4M10 6l-6 6 6 6',headphones:'M4 14v-3a8 8 0 0 1 16 0v3M4 12H3v8h4v-8zM20 12h1v8h-4v-8z',check:'m5 12 4 4 10-10',close:'m6 6 12 12M18 6 6 18',clock:'M12 8v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',target:'M21 12a9 9 0 1 1-9-9M17 12a5 5 0 1 1-5-5M12 12l8-8M16 4h4v4',chip:'M7 7h10v10H7zM9 2v5M15 2v5M9 17v5M15 17v5M2 9h5M2 15h5M17 9h5M17 15h5',factory:'M3 21V10l6 3V8l6 3V3h5v18zM7 17h1M12 17h1M17 17h1',briefcase:'M3 7h18v14H3zM8 7V3h8v4M3 12l9 4 9-4M10 14h4v4h-4',coffee:'M4 8h12v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3zM16 9h2a3 3 0 0 1 0 6h-2M7 2v3M12 2v3',download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',upload:'M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5',menu:'M4 6h16M4 12h16M4 18h16',play:'m8 5 11 7-11 7z',pause:'M8 5v14M16 5v14',shield:'m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6zM8 12l3 3 5-6',note:'M5 3h14v18H5zM8 8h8M8 12h8M8 16h5',grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',leaf:'M20 3c-12 0-18 6-14 12s16 3 14-12ZM5 20 15 8',bolt:'m13 2-9 12h7l-1 8 10-12h-7z',settings:'M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6',info:'M12 10v7M12 6v1M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0'};
const displayEnglish=(value,fallback='Saved practice session')=>/[\u3400-\u9fff]/.test(String(value||''))?fallback:String(value||fallback);
const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon=(name,cls='')=>'<svg class="icon '+cls+'" viewBox="0 0 24 24" aria-hidden="true"><path d="'+(ICONS[name]||ICONS.book)+'"/></svg>';
const fmt=n=>Number(n||0).toLocaleString('en-US');
const time=s=>{s=Math.max(0,Math.floor(s||0));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
const now=()=>Date.now();
const uid=()=>Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9);
const safeId=s=>typeof s==='string'&&/^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$/.test(s)&&!['constructor','prototype','__proto__'].includes(s);
const safeMedia=p=>typeof p==='string'&&/^(audio|assets)\/[A-Za-z0-9_./-]+\.(mp3|wav|ogg|m4a|svg|png|jpg|jpeg|webp)$/.test(p)&&!p.includes('..');
const catalog=window.SHIFT_CATALOG||{tests:[]};
const officialEntry=id=>catalog.tests.find(t=>t.id===id);
const officialPacks=new Map(), unavailableCustom=new Set();
const app=document.getElementById('app');
const launchParams=new URLSearchParams(location.search);
const diagnostic=launchParams.has('diagnostic');
const diagnosticUuid=(launchParams.get('diagnostic')||'').trim().toLowerCase();
const diagnosticMode=launchParams.get('mode');
const diagnosticBack='question-debug.html'+(/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(diagnosticUuid)?'?uuid='+encodeURIComponent(diagnosticUuid):'');
const player=document.getElementById('audio-player');
const opusPlayable=()=>Boolean(player.canPlayType('audio/ogg; codecs="opus"')||player.canPlayType('audio/ogg'));
const opusRequired=p=>typeof p==='string'&&p.endsWith('.ogg');
const opusUnavailable='This browser does not support Ogg Opus audio. Please use a browser with native Opus playback.';
let storageMode='loading',db=null,saveQueue=Promise.resolve(),toastHandle=null;
let guestBaseline=null,guestActiveRevision=null,guestSavedAnswerKey=null,guestSubmitPending=false,guestRejectedAutoSubmit=null;
let localSaveFailure=false;
const localSaveMessage='The browser could not save your latest changes. Keep this tab open and retry, or download a backup of this tab’s latest progress.';
let state={formatVersion:1,noteDraftEpoch:'initial',settings:{fontScale:1,translation:false},attempts:[],stats:{},stars:{},notes:{},sessions:[],active:null,importedPacks:[],lastBackup:null};
let route='home',mobileNav=false,filterTopic='all',filters={section:'all',part:'all',topic:'all',difficulty:'all',accent:'all',count:20,unseen:false},listFilter='all',listSearch='',listLimit=40;
let archivedIds=new Set();
// Compatibility snapshots are never registered in the active practice pool.
let resumeEnv=null;
const resumeLoads=new Map();
const contentVersion=()=>catalog.version||VERSION;
function pinnedFor(s=state.active){return !!s&&resumeEnv?.sessionId===s.id?resumeEnv:null}
function sessionQuestion(id,s=state.active){return pinnedFor(s)?.questions.get(id)||Q.get(id)}
function sessionGroup(id,s=state.active){return pinnedFor(s)?.groups.get(id)||G.get(id)}
function quizGroup(id){return route==='quiz'?sessionGroup(id):G.get(id)}
async function loadResumeSnapshot(id,s){
 const entry=catalog.resumeSnapshots?.[id];
 if(!entry||!Number.isSafeInteger(entry.from)||!Number.isSafeInteger(entry.until)||s.startedAt<entry.from||s.startedAt>=entry.until||
    (s.contentVersion&&s.contentVersion!==entry.version)||!/^data\/resume\/[A-Za-z0-9_-]+\/test-[0-9]{2}\.js$/.test(entry.path))
  throw new Error('The original version for this unfinished test cannot be confirmed. Your work is kept. Export a backup before starting another test.');
 const key=entry.path;
 if(!resumeLoads.has(key)){
  const load=new Promise((resolve,reject)=>{
   const script=document.createElement('script');script.src=entry.path;
   script.onload=()=>{try{
     const snapshot=window.SHIFT_RESUME_SNAPSHOTS?.[entry.version]?.[id];
     if(!snapshot||snapshot.testId!==id||snapshot.legacyQuestions!==undefined)throw new Error('The original test snapshot is unavailable'); 
     validatePack(snapshot);resolve(snapshot);
   }catch(e){reject(e)}};
   script.onerror=()=>{script.remove();reject(new Error('The original test archive could not load. Your saved work is unchanged.'))};
   document.head.append(script)
  });
  resumeLoads.set(key,load);
 }
 try{return await resumeLoads.get(key)}catch(e){resumeLoads.delete(key);throw e;}
}
async function prepareResume(s){
 const next={sessionId:s.id,questions:new Map(),groups:new Map(),packs:new Map()};
 if(s.contentVersion!==contentVersion()){
  for(const id of new Set(s.testIds)){
   if(!officialEntry(id))continue;
   const p=await loadResumeSnapshot(id,s);
   next.packs.set(id,p);
   p.groups.forEach(g=>next.groups.set(g.id,g));
   p.questions.forEach(q=>next.questions.set(q.id,q));
  }
 }
 for(const id of s.questionIds){
  const q=next.questions.get(id)||Q.get(id);
  if(!q||next.packs.has(q.testId)&&!next.questions.has(id)||
     (s.answers[id]&&!q.options.some(o=>o.id===s.answers[id])))
   throw new Error('An original question version is missing. Your unfinished test and answers are kept; export a backup before replacing it.');
 }
 if(state.active?.id!==s.id)throw new Error('The active test changed while its archive loaded.');
 resumeEnv=next.packs.size?next:null;
}
let Q=new Map(),G=new Map(),loaded=new Set(),loading=new Map(),busy=false,activeTranscript=null,lastResult=null,reviewDetail=null,currentAudioGroup=null,currentQuestionStart=now();
let persistentError='';
let guestBackupApplying=false;
function showPersistentError(){
 const box=document.getElementById('shift-persistent-error'), message=document.getElementById('shift-persistent-error-message');
 if(box&&message){box.hidden=!persistentError;message.textContent=persistentError;for(const action of ['retry-local-save','export-unsaved-local-backup']){const button=box.querySelector('[data-action="'+action+'"]');if(button)button.hidden=action==='retry-local-save'?!localSaveFailure:!(localSaveFailure||accountActiveConflict)}}
}
function persistentErrorHtml(){
 return '<aside id="shift-persistent-error" class="page-error"'+(persistentError?'':' hidden')+'><p id="shift-persistent-error-message" role="alert">'+esc(persistentError)+'</p>'+
 '<button type="button" class="btn small" data-action="retry-local-save"'+(localSaveFailure?'':' hidden')+'>Retry Save</button>'+
 '<button type="button" class="btn small" data-action="export-unsaved-local-backup"'+((localSaveFailure||accountActiveConflict)?'':' hidden')+'>Backup Unsaved Progress</button>'+
 '<button type="button" class="btn small" data-action="dismiss-page-error">'+icon('close')+' Dismiss</button></aside>'
}
function notify(msg){
 if(!diagnostic&&document.getElementById('shift-persistent-error')&&/\b(?:cannot|unable|failed|missing|could not|not available|not found|blocked|interrupted|invalid)\b/i.test(msg)){
  persistentError=msg;showPersistentError();return
 }
 const el=document.getElementById('toast');el.textContent=msg;el.classList.add('visible');clearTimeout(toastHandle);toastHandle=setTimeout(()=>el.classList.remove('visible'),3500)
}
function modal(html){document.getElementById('modal-content').innerHTML=html;document.getElementById('modal').showModal()}
function closeModal(){document.getElementById('modal').close()}
function confirmBox(title,body,onConfirm,label='Confirm'){modal('<h2>'+esc(title)+'</h2><p>'+esc(body)+'</p><div class="btn-row"><button class="btn" id="cancel-modal">Cancel</button><button class="btn primary" id="confirm-modal">'+esc(label)+'</button></div>');document.getElementById('cancel-modal').onclick=closeModal;document.getElementById('confirm-modal').onclick=async()=>{closeModal();await onConfirm()}}
function normalizeState(s){
if(!s||s.formatVersion!==1||!Array.isArray(s.attempts)||!Array.isArray(s.sessions))throw new Error('Invalid learning-record format');
const validTime=x=>Number.isFinite(x)&&x>=0&&x<8640000000000000;
const r={formatVersion:1,noteDraftEpoch:safeId(s.noteDraftEpoch)?s.noteDraftEpoch:'initial',settings:{fontScale:[1,1.1,1.2].includes(s.settings?.fontScale)?s.settings.fontScale:1,translation:false},attempts:[],stats:{},stars:{},notes:{},sessions:[],active:null,importedPacks:[],lastBackup:validTime(s.lastBackup)?s.lastBackup:null};
const ids=new Set();for(const a of s.attempts){if(!a||!safeId(a.id)||!safeId(a.questionId)||!safeId(a.testId)||!validTime(a.at)||typeof a.correct!=='boolean'||!['A','B','C','D',null].includes(a.selected)||![1,2,3,4,5,6,7].includes(a.part)||!Object.hasOwn(TOPICS,a.topic))throw new Error('The answer history contains invalid fields');if(!ids.has(a.id)){r.attempts.push({id:a.id,questionId:a.questionId,testId:a.testId,revision:Number.isSafeInteger(a.revision)&&a.revision>0?a.revision:1,correctAnswer:['A','B','C','D'].includes(a.correctAnswer)?a.correctAnswer:undefined,part:a.part,topic:a.topic,selected:a.selected,correct:a.correct,at:a.at,seconds:Number.isFinite(a.seconds)?Math.max(0,Math.min(3600,a.seconds)):0});ids.add(a.id)}}
r.attempts.sort((a,b)=>a.at-b.at);for(const a of r.attempts){const st=r.stats[a.questionId]||(r.stats[a.questionId]={attempts:0,wrong:0,streak:0});st.attempts++;st.wrong+=a.correct?0:1;st.streak=a.correct?st.streak+1:0;st.lastCorrect=a.correct;st.lastAt=a.at;st.testId=a.testId;st.part=a.part;st.topic=a.topic;st.due=a.at+(a.correct?(st.streak<2?3:7):1)*86400000;st.needsReview=st.wrong>0&&st.streak<2}
for(const[k,v]of Object.entries(s.stars||{}))if(safeId(k)&&v)r.stars[k]=true;
for(const[k,v]of Object.entries(s.notes||{}))if(safeId(k)&&typeof v==='string')r.notes[k]=v.slice(0,20000);
function session(x,active=false){if(!x||!safeId(x.id)||!['practice','exam'].includes(x.mode)||typeof x.title!=='string'||!Array.isArray(x.questionIds)||!x.questionIds.length||x.questionIds.length>5000||!x.questionIds.every(safeId)||new Set(x.questionIds).size!==x.questionIds.length||!validTime(x.startedAt)||!x.answers||typeof x.answers!=='object')throw new Error('Invalid practice-session format');const answerIds=new Set(x.questionIds),answers={},submitted={};for(const[k,v]of Object.entries(x.answers)){if(!answerIds.has(k)||!['A','B','C','D'].includes(v))throw new Error('Invalid saved answer option');answers[k]=v}for(const[k,v]of Object.entries(x.submitted||{}))if(answerIds.has(k)&&v===true)submitted[k]=true;
const y={id:x.id,title:x.title.slice(0,250),mode:x.mode,questionIds:x.questionIds.slice(),answers,submitted,startedAt:x.startedAt};
if(active){if(!Array.isArray(x.testIds)||!x.testIds.every(safeId)||!Number.isSafeInteger(x.index)||x.index<0||x.index>=x.questionIds.length||(x.mode==='exam'&&!validTime(x.deadline)))throw new Error('Invalid unfinished-session format');y.testIds=x.testIds.slice();if(safeId(x.contentVersion))y.contentVersion=x.contentVersion;y.index=x.index;y.deadline=x.mode==='exam'?x.deadline:null;y.examVersion=x.examVersion===2?2:1;if(['azure-1','toeic-1'].includes(x.audioEdition))y.audioEdition=x.audioEdition;y.examPhase=x.examPhase==='reading'?'reading':'listening';y.listeningStartedAt=validTime(x.listeningStartedAt)?x.listeningStartedAt:null;y.sectionDeadline=validTime(x.sectionDeadline)?x.sectionDeadline:(y.examVersion===2&&y.examPhase==='listening'&&!y.listeningStartedAt?null:y.deadline);if(y.examVersion===2&&y.examPhase==='listening'&&y.listeningStartedAt&&Number.isFinite(x.listeningRemaining)&&x.listeningRemaining>=0&&x.listeningRemaining<=86400)y.listeningRemaining=x.listeningRemaining;if(y.examVersion===2&&y.examPhase==='reading'&&x.readingStartsOnReturn===true){y.readingStartsOnReturn=true;y.sectionDeadline=null}y.audioUsed={};for(const[k,v]of Object.entries(x.audioUsed||{})){if(safeId(k)&&v&&['started','ended','interrupted'].includes(v.status)&&validTime(v.unlockAt))y.audioUsed[k]={status:v.status==='started'?'interrupted':v.status,unlockAt:v.unlockAt,...(Number.isSafeInteger(v.frame)&&v.frame>=0&&Number.isFinite(v.offset)&&v.offset>=0?{frame:v.frame,offset:v.offset}:{})}}const m=x.practiceMedia;if(x.mode==='practice'&&m&&safeId(m.groupId)&&Number.isFinite(m.offset)&&m.offset>=0&&m.offset<=86400&&[.75,1,1.25].includes(m.rate)&&typeof m.paused==='boolean')y.practiceMedia={groupId:m.groupId,offset:m.offset,rate:m.rate,paused:m.paused}}else{if(!Number.isSafeInteger(x.correct)||!Number.isSafeInteger(x.total)||!Number.isSafeInteger(x.answered)||x.total!==x.questionIds.length||x.correct<0||x.correct>x.total||x.answered<0||x.answered>x.total||!validTime(x.finishedAt))throw new Error('Score fields must contain valid numbers');y.correct=x.correct;y.total=x.total;y.answered=x.answered;y.finishedAt=x.finishedAt}return y}
r.sessions=s.sessions.map(x=>session(x));if(s.active)r.active=session(s.active,true);
const blocked=new Set(),testIds=new Set();
for(const p of s.importedPacks||[]){
 if(officialEntry(p?.testId)){blocked.add(p.testId);continue}
 validatePack(p);
 if(testIds.has(p.testId))throw new Error('The backup contains duplicate test ID');
 testIds.add(p.testId);r.importedPacks.push(p)
}
if(r.active&&(s.active?.reservedPackConflict===true||r.active.testIds.some(id=>blocked.has(id))))r.active.reservedPackConflict=true;
return r}

const blankWorkspace=()=>normalizeState({formatVersion:1,attempts:[],sessions:[]});
async function readWorkspace(owner){
 const key=scopedKey('state',owner),fallback=scopedKey('shift-english-lab-v1',owner);
 const stored=storageMode==='indexeddb'&&db?await new Promise((resolve,reject)=>{
  const req=db.transaction('kv').objectStore('kv').get(key);req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error)
 }):storageMode==='localstorage'?JSON.parse(localStorage.getItem(fallback)):null;
 const result=stored?normalizeState(stored):blankWorkspace();
 if(!owner&&typeof stored?.guestActiveRevision==='string')Object.defineProperty(result,'guestActiveRevision',{value:stored.guestActiveRevision});
 if(owner)Object.defineProperty(result,'accountActiveRevision',{value:stored?.accountActiveRevision??null});
 if(owner)result.syncSent=Object.fromEntries(Object.entries(stored?.syncSent||{}).filter(([id,value])=>records.UUID.test(id)&&value===true));
 return result
}
const records=window.SHIFT_SYNC_RECORDS;
const syncConfig=window.SHIFT_SYNC_CONFIG;
const syncConfigured=!!(records&&syncConfig?.url&&syncConfig?.publishableKey&&/^https?:$/.test(location.protocol));
let accountBaseline=null,accountActiveRevision=null,accountActiveConflict=false;
const accountActiveWarning='This session could not be saved because it changed in another tab. Back up any unsaved edits, then reload to resume.';
let syncOwner=null,syncCore=null,syncOnline=null,syncPasswordOpen=false,syncStatus='',syncPageCursor=null,syncLastFull=0,syncEpoch=0;
const scopedKey=(key,owner=syncOwner)=>records&&owner?records.key(key,owner):key;
const accountActionBusy=()=>route!=='data'||diagnostic;
const AUTH_TAB_KEY='shift:/shift-english-lab-1/:auth-refresh/v1', LAST_PAGE_TAB_KEY='shift:last-page:v1';
let authRestoreStatus='',authRestorePromise=null,authHint='',authOperation='',authTabSaved=false;
function tabRead(key){try{return sessionStorage.getItem(key)}catch{return null}}
function tabWrite(key,value){
 try{if(value===null)sessionStorage.removeItem(key);else sessionStorage.setItem(key,value);return true}catch{return false}
}
function refreshReceipt(value){
 if(!value){tabWrite(AUTH_TAB_KEY,null);authTabSaved=false;renderAuthStatus();return}
 authTabSaved=tabWrite(AUTH_TAB_KEY,JSON.stringify({version:1,...value}));
}
function headerAuthState(){
 if(!syncConfigured)return {text:'Guest',detail:'Offline guest workspace',css:'guest'};
 if(authRestoreStatus==='checking')return {text:'Checking…',detail:'Checking sign-in',css:'pending'};
 if(authRestoreStatus==='waiting')return {text:navigator.onLine===false?'Offline':'Sign-in pending',detail:'Sign-in will be checked after reconnecting or leaving practice',css:'pending'};
 if(authRestoreStatus==='expired')return {text:'Sign in again',detail:'Sign-in expired',css:'pending'};
 if(syncOwner&&syncCore?.getScope()?.userId===syncOwner)return navigator.onLine===false
  ?{text:'Signed in · Offline',detail:'Signed in, offline',css:'pending'}:{text:'Signed in',detail:'Signed in',css:'signed'};
 if(syncOwner)return {text:'Sign in again',detail:'Sign-in expired',css:'pending'};
 return {text:'Not signed in',detail:'Not signed in',css:'guest'};
}
function authHeaderLabel(a){return a.text+(a.detail!==a.text?' · '+a.detail:'')+' · Open Data & Settings'}
function authHeaderHtml(){
 const a=headerAuthState();
 return '<button type="button" id="shift-auth-badge" class="auth-badge '+a.css+'" data-action="nav-data" aria-label="'+esc(authHeaderLabel(a))+'">'+icon('account','auth-account-icon')+'<span>'+esc(a.text)+'</span></button>'
}
function renderAuthStatus(){
 const b=document.getElementById('shift-auth-badge'); if(!b)return;
 const a=headerAuthState();
 b.className='auth-badge '+a.css;b.setAttribute('aria-label',authHeaderLabel(a));b.lastElementChild.textContent=a.text
}
function setAuthOperation(op){
 authOperation=op;
 const form=document.getElementById(op==='password'?'shift-sync-password-form':'shift-sync-login-form');
 if(form)form.setAttribute('aria-busy',op?'true':'false');
 for(const b of document.querySelectorAll('#account-sync button[data-action^="sync-"], #account-sync button[type="submit"]'))b.disabled=!!op
}
const statusKind=msg=>/error|failed|could not|unable|invalid|expired|stopped|does not|cannot|not match/i.test(msg)?'error':/syncing|signing|checking|offline|pending/i.test(msg)?'waiting':'ok';
const authStatusHtml=()=>'<p class="auth-feedback" data-kind="'+statusKind(syncStatus)+'" role="status" aria-live="polite" aria-atomic="true" id="shift-sync-status"'+(syncStatus?'':' hidden')+'>'+esc(syncStatus)+'</p>';
async function restoreSavedAccount(){
 if(!syncConfigured||syncOwner||authRestorePromise||storageMode!=='indexeddb')return authRestorePromise;
 const raw=tabRead(AUTH_TAB_KEY);if(!raw)return;
 let saved;
 try{saved=JSON.parse(raw);if(saved?.version!==1)throw Error('bad version')}catch{refreshReceipt(null);return}
 if(route==='quiz'){authRestoreStatus='waiting';authHint='Sign-in will be checked after you leave this guest practice.';renderAuthStatus();return}
 if(navigator.onLine===false){authRestoreStatus='waiting';authHint='Offline. Sign-in will be checked when you reconnect.';return}
 authRestoreStatus='checking';renderAuthStatus();
 const splash=app.querySelector('.boot p');if(splash){splash.setAttribute('role','status');splash.textContent='Checking your sign-in…'}
 const p=(async()=>{
  try{
   const c=await getSyncCore();
   const id=(await c.restoreWithRefresh(saved)).userId;
   try{await switchWorkspace(id,true)}catch(error){
    const fresh=c.exportAuthState();c.clear();
    if(error.message==='keep_guest_workspace'&&fresh){
     refreshReceipt({userId:fresh.userId,refreshToken:fresh.refreshToken,projectOrigin:fresh.projectOrigin});
     authRestoreStatus='waiting';authHint=route==='quiz'?'Sign-in will be checked after you leave this guest practice.':'Sign-in will be checked after you finish editing.';return
    }
    throw error
   }
   authRestoreStatus='';authHint=authTabSaved?'':'This browser cannot retain sign-in after refresh.';
  }catch(error){
   if(['network','service_unavailable','rate_limited'].includes(error?.code)){
    authRestoreStatus='waiting';authHint='Could not check sign-in. Reconnect or sign in again.';
   }else{
    refreshReceipt(null);authRestoreStatus='expired';authHint='Your sign-in expired. Sign in again to reopen your saved account workspace.'
   }
  }
 })();
 authRestorePromise=p;
 try{await p}finally{if(authRestorePromise===p)authRestorePromise=null;renderAuthStatus()}
}
function allowPassiveRepaint(){
 const el=document.activeElement;
 return !document.getElementById('modal')?.open&&(!el||el===document.body||!el.matches('input,textarea,select,button,a,summary,[contenteditable]'))
}
function refreshResumeSlot(){
 const slot=document.getElementById('home-resume-slot');
 if(!slot||slot.contains(document.activeElement))return;
 slot.innerHTML=resumeBanner()
}
function updateCheckpointRegion(){
 const el=document.querySelector('.checkpoint-region');
 if(el)el.outerHTML=checkpointUi()
}
async function recheckAuthOnReconnect(){
 if(syncOwner){void startSync();void syncCheckpoint();renderAuthStatus();return}
 if(authRestoreStatus!=='waiting'||authOperation||guestBackupApplying||route==='quiz'||route==='data'&&!allowPassiveRepaint())return;
 await restoreSavedAccount();
 if(route==='quiz')return; // Do not switch or redraw an active local quiz.
 if(allowPassiveRepaint())render();
 if(syncOwner){refreshResumeSlot();void startSync();void syncCheckpoint()}
}
async function exportKeptProgress(){
 if(!syncOwner)return;
 const meta=await checkpointMeta(syncOwner),items=meta?.kept;
 if(!Array.isArray(items)||!items.length){setSyncStatus('There is no preserved alternate practice on this device.');return}
 const value=items.at(-1).checkpoint;
 if(!value)return;
 const original=normalizeState({formatVersion:1,attempts:[],sessions:[],active:value,
  importedPacks:state.importedPacks.filter(p=>value.testIds.includes(p.testId))});
 const blob=new Blob([JSON.stringify({format:'shift-learning-backup',version:1,exportedAt:new Date().toISOString(),state:original})],{type:'application/json'});
 const href=URL.createObjectURL(blob),a=document.createElement('a');a.href=href;a.download='shift-preserved-practice.json';a.click();
 setTimeout(()=>URL.revokeObjectURL(href),1000);setSyncStatus('Preserved practice backup downloaded.');
}
function historyNotice(){
 const local='Your current practice and completed history sync to this account. Notes, saved questions, and custom packs stay in this browser. Guest practice is kept separate. Refreshing this tab keeps your sign-in if it can be verified. New tabs or browsers may require sign-in.';
 if(!syncConfigured)return '';
 const h='<h2>'+icon('shield')+' Account &amp; Sync</h2>';
 const status=authStatusHtml();
 const hint=authHint?'<p class="auth-feedback" data-kind="'+statusKind(authHint)+'">'+esc(authHint)+'</p>':'';
 if(syncOwner){
  return '<section class="panel" id="account-sync" style="margin-bottom:20px">'+h+
  '<p>Account workspace. '+local+'</p>'+hint+(syncPasswordOpen?'':status)+'<div class="btn-row">'+btn(icon('sync')+' Sync Now','sync-now','primary')+
  btn('Copy Guest History','sync-import-guest')+btn('Change Password','sync-change-password')+btn('Sign Out','sync-logout')+'</div><details><summary>Practice recovery</summary><p>Download the most recent alternate practice preserved on this browser.</p>'+btn(icon('download')+' Download preserved practice','sync-keep-download')+'</details>'+
  (syncPasswordOpen?'<form id="shift-sync-password-form" novalidate><p>Set a password unique to SHIFT. If you forget it, contact the person who opened your account.</p>'+
  '<div class="field"><label for="shift-sync-current-password">Current password</label><input id="shift-sync-current-password" name="currentPassword" type="password" autocomplete="current-password" maxlength="256" required></div>'+
  '<div class="field"><label for="shift-sync-new-password">New password</label><input id="shift-sync-new-password" name="newPassword" type="password" autocomplete="new-password" minlength="12" maxlength="72" required></div>'+
  '<div class="field"><label for="shift-sync-confirm-password">Confirm new password</label><input id="shift-sync-confirm-password" name="confirmPassword" type="password" autocomplete="new-password" minlength="12" maxlength="72" required></div>'+
  '<button class="btn primary" type="submit">Save Password</button>'+status+'</form>':'')+'</section>';
 }
 return '<section class="panel" id="account-sync" style="margin-bottom:20px">'+h+
 '<p>Keep practicing as a guest, or sign in with an account provided by the administrator. Sign in on each device to resume your account practice and sync completed history. An unfinished guest test does not block sign-in. To resume it after signing in, sign out and return to Practice Home. Guest records are not uploaded unless you choose Copy Guest History, which copies completed records only.</p>'+
 hint+'<form id="shift-sync-login-form" novalidate><div class="field"><label for="shift-sync-email">Email</label><input id="shift-sync-email" name="email" type="email" autocomplete="username" maxlength="254" aria-describedby="shift-sync-status" required></div>'+
 '<div class="field"><label for="shift-sync-password">Password</label><input id="shift-sync-password" name="password" type="password" autocomplete="current-password" maxlength="256" aria-describedby="shift-sync-status" required></div>'+
 '<button class="btn primary" type="submit">Sign In</button>'+status+'</form><p class="hint">Forgot your password? Contact your account administrator.</p></section>';
}
function setSyncStatus(msg){syncStatus=msg;const el=document.getElementById('shift-sync-status');if(el){el.hidden=!msg;el.dataset.kind=statusKind(msg);el.textContent=msg}}
async function getSyncCore(){
 if(!syncConfigured)throw Error('Account sync is not configured.');
 if(syncCore)return syncCore;
 const m=await import(SYNC_MODULE_URL);
 syncCore=m.createShiftSync({url:syncConfig.url,publishableKey:syncConfig.publishableKey,allowLocal:syncConfig.allowLocal===true,fetchImpl:window.fetch.bind(window),onSessionChange:refreshReceipt});
 return syncCore;
}
function accountMessage(error){
 const k=String(error?.code||'');
 if(/conflict/i.test(k))return 'A record needs attention. Both copies were kept.';
 if(k==='invalid_credentials')return 'Sign-in could not be verified. Check your email and password.';
 if(k==='invalid_password')return 'Choose a different password with at least 12 characters.';
 if(/password_change|reauthentication/i.test(k))return 'Password not changed. Check your current password or contact your account administrator.';
 if(/auth|session|credential|token|unauthor/i.test(k))return 'Sign-in could not be verified. Sign in again.';
 if(/rate|limit/i.test(k))return 'Too many requests. Please wait before trying again.';
 if(/config|publishable/i.test(k))return 'Account sync is not available on this site.';
 return 'Unable to connect. Your learning records remain on this device.';
}
async function switchWorkspace(owner,avoidQuiz=false){
 if(owner===syncOwner)return;
 if(storageMode!=='indexeddb')throw Error('Local account records cannot be safely opened.');
 // Leave any unfinished test in its original workspace. Drain pending writes
 // before opening a different owner; do not re-save this tab's stale snapshot.
 await saveQueue;
 if(localSaveFailure||storageMode!=='indexeddb')throw Error('Local account records cannot be safely opened.');
 const next=await readWorkspace(owner);
 if(guestBackupApplying)throw Error('keep_guest_workspace');
 if(avoidQuiz&&(route==='quiz'||route==='data'&&!allowPassiveRepaint()||document.getElementById('modal')?.open))throw Error('keep_guest_workspace');
 const previous={state,owner:syncOwner,Q,G,loaded,officialPacks:new Map(officialPacks),
  archived:new Set(archivedIds),unavailable:new Set(unavailableCustom),lastResult,reviewDetail,resumeEnv,lastExportAt};
 clearTimeout(checkpointTimer);checkpointTimer=undefined;checkpointLoop=null;checkpointConflict=null;checkpointFeedback='';checkpointSyncAt=0;checkpointSignature='';
 syncEpoch++;syncPageCursor=null;syncLastFull=0;syncOnline=null;syncStatus='';lastExportAt=0;
 stopAudio();reviewDetail=null;lastResult=null;resumeEnv=null;noteGeneration++;noteTokens.clear();noteStatuses.clear();
 state=next;syncOwner=owner;
 const priorAccount=[accountBaseline,accountActiveRevision,accountActiveConflict];
 accountBaseline=owner?JSON.parse(JSON.stringify(next)):null;
 accountActiveRevision=next.accountActiveRevision??null;
 accountActiveConflict=false;
 const priorGuest=[guestBaseline,guestActiveRevision,guestSavedAnswerKey];
 if(!owner)seedGuest(state,state);
 try{await installPackIndexes();await restoreNoteDraft();if(storageMode!=='indexeddb')throw Error('Storage unavailable')}
 catch(error){
  [guestBaseline,guestActiveRevision,guestSavedAnswerKey]=priorGuest;
  [accountBaseline,accountActiveRevision,accountActiveConflict]=priorAccount;
  state=previous.state;syncOwner=previous.owner;Q=previous.Q;G=previous.G;loaded=previous.loaded;
  officialPacks.clear();for(const [key,value] of previous.officialPacks)officialPacks.set(key,value);
  archivedIds.clear();for(const key of previous.archived)archivedIds.add(key);
  unavailableCustom.clear();for(const key of previous.unavailable)unavailableCustom.add(key);
  lastResult=previous.lastResult;reviewDetail=previous.reviewDetail;resumeEnv=previous.resumeEnv;lastExportAt=previous.lastExportAt;
  throw error
 }
}
let checkpointModule,checkpointTimer,checkpointLoop,checkpointSyncAt=0,checkpointApplying=false,checkpointFeedback='',checkpointConflict=null,checkpointSignature='';
async function checkpointLibrary(){return checkpointModule??=(await import('./shift-active-checkpoint.mjs?v=1'))}
function setCheckpointFeedback(message){
 checkpointFeedback=message;
 const box=document.getElementById('checkpoint-feedback');
 if(box){box.textContent=message;box.hidden=!message;box.dataset.kind=statusKind(message)}
}
function checkpointUi(){
 if(!syncOwner)return '';
 const rem=checkpointConflict?'<div class="checkpoint-conflict" role="group" aria-label="Choose which practice progress to resume"><strong>Practice progress differs on another device.</strong><p>Both copies are kept. Choose before continuing; this browser will not overwrite the other copy automatically.</p><div class="btn-row">'+btn(icon('cloud')+' Use cloud progress','checkpoint-cloud','primary')+(checkpointConflict.finished?'':btn(icon('device')+' Keep this device’s progress','checkpoint-local'))+'</div></div>':'';
 return '<aside class="checkpoint-region" aria-label="Practice progress sync">'+rem+
   '<p id="checkpoint-feedback" class="checkpoint-feedback" data-kind="'+statusKind(checkpointFeedback)+'" role="status" aria-live="polite" aria-atomic="true"'+(checkpointFeedback?'':' hidden')+'>'+esc(checkpointFeedback)+'</p></aside>'
}
function nextCheckpointMeta(observed,expected,updated){
 const prior=observed||{};
 // Compare the whole earlier record, including the pending ID and kept copies.
 // A delayed response must not replace a pending mutation from another tab.
 if(!records.same(prior,expected||{}))return null;
 if((updated.base?.revision??-1)<(prior.base?.revision??-1))return null;
 return updated
}
async function checkpointMeta(owner,update){
 if(!owner||!db||storageMode!=='indexeddb')throw Error('checkpoint_storage');
 const key=scopedKey('checkpoint-meta',owner);
 return new Promise((resolve,reject)=>{
  const tx=db.transaction('kv',update?'readwrite':'readonly'),store=tx.objectStore('kv');
  let value=null;
  tx.oncomplete=()=>resolve(value);tx.onabort=()=>reject(tx.error||Error('checkpoint_storage'));
  const req=store.get(key);
  req.onsuccess=()=>{
   try{
    if(!update){value=req.result??null;return}
    value=nextCheckpointMeta(req.result,update.expected,update.updated);
    if(value)store.put(value,key);
   }catch(error){tx.onabort=()=>reject(error);tx.abort()}
  }
 })
}
function scheduleCheckpoint(delay=500){
 if(!syncOwner||!syncConfigured||!syncCore?.getScope()||storageMode!=='indexeddb'||localSaveFailure||accountActiveConflict||checkpointApplying||checkpointConflict)return;
 if(navigator.onLine===false){setCheckpointFeedback('Offline. Practice progress is saved on this device and will sync when you reconnect.');return}
 if(checkpointTimer!==undefined)return;
 checkpointTimer=setTimeout(()=>{checkpointTimer=undefined;void syncCheckpoint()},delay)
}
async function syncCheckpoint(choice=null){
 if(!syncOwner||storageMode!=='indexeddb'||localSaveFailure||accountActiveConflict||checkpointConflict&&!choice||navigator.onLine===false)return;
 if(checkpointLoop){if(choice)return;return checkpointLoop}
 const owner=syncOwner,epoch=syncEpoch,active=syncCore?.getScope();
 if(active?.userId!==owner)return;
 const current=()=>owner===syncOwner&&epoch===syncEpoch&&active===syncCore?.getScope()&&!accountActiveConflict;
 const currentDurable=async()=>{
  await saveQueue;
  if(!current()||localSaveFailure)return false;
  const durable=await readWorkspace(owner);
  return current()&&!localSaveFailure&&durable.accountActiveRevision===accountActiveRevision;
 };
 let localAtStart,applied=false;
 const task=(async()=>{
  try{
   const lib=await checkpointLibrary();
   await saveQueue;
   if(!await currentDurable())return;
   let meta=await checkpointMeta(owner)||{};
   const cap=()=>lib.captureCheckpoint(state.active?normalizeState({formatVersion:1,attempts:[],sessions:[],active:state.active}).active:null);
   const local=localAtStart=cap();let base=meta.base;
   const remote=await syncCore.readActiveCheckpoint(active);
   if(!await currentDurable())return;
   remote.checkpoint=lib.parseCheckpoint(remote.checkpoint,normalizeState);
   if(remote.mutationId&&meta.pending?.mutationId===remote.mutationId)base=remote;
   const newerLocal=cap();
   // User actions and audio never wait for the network. A working local session
   // might have advanced between the GET and the decision.
   const same=lib.sameCheckpoint;
   const mark=async value=>{
    if(!current())return false;
    const committed=await checkpointMeta(owner,{expected:meta,updated:value});
    if(!committed){if(await currentDurable())scheduleCheckpoint();return false}
    meta=committed;
    return current()
   };
   let resolution=lib.checkpointDecision({base,remote,local:newerLocal,inTest:route==='quiz'});
   if(choice){
    if(checkpointConflict?.finished&&choice==='cloud')resolution='take';
    else if(!checkpointConflict||checkpointConflict.revision!==remote.revision||
       !same(checkpointConflict.checkpoint,remote.checkpoint))resolution='conflict';
    else resolution=choice==='cloud'?'take':'push';
   }
   if(resolution==='conflict'){
    const was=!!checkpointConflict;
    checkpointConflict={revision:remote.revision,checkpoint:remote.checkpoint};
    setCheckpointFeedback('Sync paused for this practice. Choose which progress to keep.');
    if(!was||choice)updateCheckpointRegion();
    return
   }
   if(resolution==='stale')throw Error('checkpoint_stale');
   if(resolution==='ack'){if((!meta.base||meta.base.revision!==remote.revision||meta.pending)&&!await mark({...meta,base:remote,pending:null}))return;if(!current())return;checkpointConflict=null;checkpointSyncAt=now();setCheckpointFeedback('Practice progress is synced.');if(choice){updateCheckpointRegion();if(route==='home')document.querySelector('.resume-main')?.focus()}return}
   if(resolution==='take'){
    // External changes cannot take over an open quiz unless explicitly selected.
    if(!current()||!same(cap(),newerLocal))return;
    if(newerLocal&&choice){
     const kept=[...(Array.isArray(meta.kept)?meta.kept:[]),{at:now(),checkpoint:newerLocal}].slice(-4);
     if(!await mark({...meta,kept}))return;
     if(!current()||!same(cap(),newerLocal))return;
    }
    checkpointApplying=true;
    const wasQuiz=route==='quiz',previousActive=state.active,previousResume=resumeEnv;
    try{
     stopAudio();state.active=remote.checkpoint?normalizeState({formatVersion:1,attempts:[],sessions:[],active:remote.checkpoint}).active:null;
     resumeEnv=null;
     if(route==='quiz')route='home';
     try{if(await persist(true)===false)throw Error('account_workspace_conflict')}catch(error){
      if(owner===syncOwner&&epoch===syncEpoch){state.active=previousActive;resumeEnv=previousResume;if(wasQuiz)route='quiz'}
      throw error
     }
     if(!await mark({...meta,base:remote,pending:null})){if(wasQuiz&&current())render();return}
     if(!current())return;
     applied=true;checkpointConflict=null;checkpointSyncAt=now();
     setCheckpointFeedback(state.active?'Practice progress is ready to resume.':'Practice progress is synced.');
     if(wasQuiz)render();else{updateCheckpointRegion();refreshResumeSlot()}
     if(choice==='cloud'&&route==='home')document.querySelector('.resume-main')?.focus();
    }finally{checkpointApplying=false}
    return
   }
   const value=newerLocal;
   if(choice==='local'&&remote.checkpoint){
    const kept=[...(Array.isArray(meta.kept)?meta.kept:[]),{at:now(),checkpoint:remote.checkpoint}].slice(-4);
    if(!await mark({...meta,kept}))return;
   }
   const prev=meta.pending;
   const pending=prev?.revision===remote.revision&&same(prev.checkpoint,value)?prev:
     {revision:remote.revision,mutationId:crypto.randomUUID(),checkpoint:value};
   // Durably keep the mutation ID; a lost success response is safe to retry.
   if(!await currentDurable()||!same(cap(),value))return;
   if(!await mark({...meta,base:remote,pending}))return;
   if(!await currentDurable()||!same(cap(),value))return;
   const result=await syncCore.writeActiveCheckpoint(pending,active);
   if(!current())return;
   if(result==='conflict'||result==='already_completed'){
    // Another tab may already have superseded this exact RPC while it waited.
    if(!await currentDurable()||!records.same(await checkpointMeta(owner)||{},meta)||!current())return;
    // Never mark stale or already-submitted data synced; preserve its local copy.
    checkpointConflict=result==='already_completed'
      ?{finished:true,revision:remote.revision,checkpoint:remote.checkpoint}
      :{revision:-1,checkpoint:null};
    setCheckpointFeedback(result==='already_completed'
      ?'This practice was already submitted. Older progress was kept on this device, not uploaded.'
      :'Newer progress was saved on another device. Refresh the progress choice.');
    updateCheckpointRegion();
    return
   }
   const ack={revision:remote.revision+1,mutationId:pending.mutationId,checkpoint:value};
   if(!await mark({...meta,base:ack,pending:null}))return;
   if(!current())return;
   checkpointConflict=null;checkpointSyncAt=now();
   const more=!same(cap(),value);
   setCheckpointFeedback(more?'Saving practice progress…':'Practice progress is synced.');
   if(choice)updateCheckpointRegion();
   if(more)scheduleCheckpoint();
  }catch(error){
   if(current())setCheckpointFeedback(error?.message==='checkpoint_unsupported'
    ?'This practice can only be saved on this device.'
    :'Practice progress remains on this device. Sync will retry when available.')
  }
 })();
 checkpointLoop=task;
 try{await task}finally{
  if(checkpointLoop===task)checkpointLoop=null;
  if(current()&&!applied&&localAtStart!==undefined&&!checkpointConflict){
   const lib=await checkpointLibrary();
   try{if(!lib.sameCheckpoint(lib.captureCheckpoint(state.active?normalizeState({formatVersion:1,attempts:[],sessions:[],active:state.active}).active:null),localAtStart))scheduleCheckpoint()}catch{}
  }
 }
}
async function startSync(full=false){
 if(!syncOwner||storageMode!=='indexeddb')return;
 if(navigator.onLine===false){setSyncStatus('Offline. Completed records will sync after reconnecting.');return}
 const owner=syncOwner,epoch=syncEpoch;
 if(syncOnline)return syncOnline;
 const p=(async()=>{
  const inWorkspace=()=>syncOwner===owner&&syncEpoch===epoch;
  const current=()=>inWorkspace()&&syncCore?.getScope()?.userId===owner;
  const scope=syncCore?.getScope();
  if(!current()){setSyncStatus('Your sign-in expired. Sign out, then sign in again to resume sync.');return}
  setSyncStatus('Syncing completed history…');
  let conflicts=0,invalid=0,skips=0,changed=false;
  try{
   await saveQueue;
   const durable=await readWorkspace(owner);
   if(!current())return;
   const fromOtherTabs=records.localUnion(state,durable,normalizeState);
   Object.assign(state,fromOtherTabs);
   changed ||= !!fromOtherTabs.sessions;
   const allAttempts=new Map(state.attempts.map(a=>[a.id,a]));
   for(const s of state.sessions.slice()){
    if(!current())return;
    if(state.syncSent?.[s.id])continue;
    const r=records.record(s,allAttempts,s.id);
    if(!r){skips++;continue}
    let result;
    try{result=await syncCore.saveCompletedSession(r,scope)}
    catch(error){if(['invalid_session','request_failed'].includes(error?.code)){skips++;continue}throw error}
    if(!current())return;
    if(result==='conflict'){conflicts++;continue}
    const prior=state.syncSent;
    state.syncSent={...prior,[s.id]:true};
    try{await persist(true,true)}catch(error){if(current())state.syncSent=prior;throw error}
   }
   const runFull=full||!syncLastFull||now()-syncLastFull>=15*60000;
   let cursor=runFull?null:syncPageCursor, count=0;
   do{
    const page=await syncCore.listCompletedSessions({scope,cursor,limit:100});
    if(!current())return;
    if(page.rows.length){
     const merged=records.safeRows(state,page.rows,normalizeState,owner);
     const prior={sessions:state.sessions,attempts:state.attempts,stats:state.stats,syncSent:state.syncSent};
     state.sessions=merged.sessions;state.attempts=merged.attempts;state.stats=merged.stats;state.syncSent=merged.syncSent;
     conflicts+=merged.conflicts;invalid+=merged.invalid;changed ||= merged.imported>0;
     try{await persist(true,true)}catch(error){
      // Keep newly read records in memory for backup, without claiming a durable receipt.
      if(current())state.syncSent=prior.syncSent;
      throw error
     }
    }
    if(page.nextCursor)syncPageCursor=page.nextCursor;
    cursor=page.nextCursor;count++;
   }while(cursor&&count<1000);
   if(current()){
    if(runFull&&!cursor)syncLastFull=now();
    setSyncStatus(conflicts?'Some records conflict. Both copies were kept.':invalid?'Some cloud records could not be read. Other eligible history synced.':skips?'Synced eligible records. Incomplete or oversized records stayed on this device.':cursor?'This batch synced. Choose Sync Now to continue.':'Completed history is synced.');
    if(changed&&['home','review','stats'].includes(route)&&!busy&&allowPassiveRepaint())render();
   }
  }catch(error){if(inWorkspace())setSyncStatus(storageMode!=='indexeddb'?'Local saving failed. Export a backup before switching accounts.':accountMessage(error))}
 })();
 syncOnline=p;
 try{return await p}finally{if(syncOnline===p)syncOnline=null}
}
async function syncGuestPreview(){
 const guest=await readWorkspace(null);
 const owner=syncOwner,epoch=syncEpoch;
 const byId=new Map(guest.attempts.map(a=>[a.id,a]));
 if(!guest.sessions.length){notify('No completed history was found in the guest workspace.');return}
 confirmBox('Copy guest history to your account?','Copies eligible completed sessions and their answers from this browser into your signed-in account and uploads them to Supabase. The guest copy stays on this device. Notes, saved questions, unfinished tests, and custom packs are not copied.',async()=>{
  if(owner!==syncOwner||epoch!==syncEpoch)return;
  const m=await import(SYNC_MODULE_URL);
  const staged=[];
  for(const s of guest.sessions){
   const id=records.UUID.test(s.id)?s.id:await m.combineCompletedSessionId('shift-en-lab/guest-session-v1',s.id);
   const r=records.record(s,byId,id);
   if(r)staged.push({id,user_id:owner,completed_at:r.completedAt,payload:r.payload});
  }
  if(owner!==syncOwner||epoch!==syncEpoch)return;
  if(staged.length){
   const local=records.safeRows(state,staged,normalizeState,owner);
   // These are local additions, not a read receipt from the server.
   state.sessions=local.sessions;state.attempts=local.attempts;state.stats=local.stats;
   await persist(true,true);
   if(local.conflicts)notify('Some existing account records differ. Matching IDs were not overwritten.');
  }
  if(staged.length!==guest.sessions.length)notify('Incomplete or oversized guest records remained in the guest workspace.');
  await startSync();
 },'Copy & Sync')
}
async function syncAccountAction(actionId){
 if(accountActionBusy()||authOperation||authRestoreStatus==='checking')return;
 if(!syncOwner)return;
 if(actionId==='sync-change-password'){
  syncPasswordOpen=!syncPasswordOpen;render();
  if(syncPasswordOpen)document.getElementById('shift-sync-current-password')?.focus();
  return
 }
 if(actionId==='sync-now'){void startSync(true);void syncCheckpoint();return}
 if(actionId==='sync-import-guest')return syncGuestPreview();
 if(actionId==='sync-keep-download')return exportKeptProgress();
 if(actionId==='sync-logout'){
  setSyncStatus('Signing out…');
  try{await switchWorkspace(null)}catch{setSyncStatus('Sign-out was stopped to protect local records.');return}
  syncPasswordOpen=false;authHint='';
  const remote=syncCore?.logout();void remote?.catch(()=>{});
  syncStatus='Signed out. Any unfinished guest test can be resumed from Practice Home.';render();
 }
}
document.addEventListener('submit',e=>{
 const form=e.target;
 if(!['shift-sync-login-form','shift-sync-password-form'].includes(form.id))return;
 e.preventDefault();
 if(accountActionBusy())return;
 if(authOperation||authRestoreStatus==='checking')return setSyncStatus('The account is still being checked. Please wait.');
 if(busy)return setSyncStatus('The page is still loading. Please try again in a moment.');
 if(!form.checkValidity()){
  const field=form.querySelector(':invalid');
  setSyncStatus(field?.name==='email'?'Enter a valid email address.':form.id==='shift-sync-login-form'?'Enter your password.':'Check all password fields. New passwords need at least 12 characters.');
  field?.focus();return
 }
 const change=form.id==='shift-sync-password-form';
 const value=new FormData(form);
 const fields=['password','currentPassword','newPassword','confirmPassword'];
 for(const key of fields){const input=form.elements.namedItem(key);if(input)input.value=''}
 void withBusy(async()=>{
  setAuthOperation(change?'password':'login');
  try{
   if(storageMode!=='indexeddb')return setSyncStatus('Sign-in requires available IndexedDB browser storage. Guest practice can still use this browser.');
   const c=await getSyncCore();
   if(change){
    const scope=c.getScope();
    if(!syncOwner||scope?.userId!==syncOwner)return setSyncStatus('Sign in again before changing your password.');
    const next=String(value.get('newPassword')||'');
    if(next!==value.get('confirmPassword'))return setSyncStatus('The two new passwords do not match.');
    const current=String(value.get('currentPassword')||'');
    if([...next].length<12||new TextEncoder().encode(next).byteLength>72||next===current)return setSyncStatus('Choose a different password with at least 12 characters and at most 72 UTF-8 bytes.');
    await c.changePassword(current,next,scope);
    syncPasswordOpen=false;syncStatus='Password changed.';render();
   }else{
    if(syncOwner)return;
    authRestoreStatus='';authHint='';renderAuthStatus();
    setSyncStatus('Signing in…');
    const id=(await c.signInWithPassword(String(value.get('email')||'').trim(),String(value.get('password')||'')))?.userId;
    if(!id)throw Error('Authentication did not create a session.');
    try{await switchWorkspace(id)}catch{c.clear();return setSyncStatus('Signed in but could not open local account records. Your current workspace was kept. Try again.');}
    syncPasswordOpen=false;authHint=authTabSaved?'':'This browser cannot retain sign-in after refresh.';syncStatus='Signed in.';render();void startSync();void syncCheckpoint();
   }
  }catch(error){setSyncStatus(accountMessage(error))}
  finally{setAuthOperation('');for(const key of fields)value.delete(key)}
 })
});
window.addEventListener('offline',()=>{renderAuthStatus();if(syncOwner)setCheckpointFeedback('Offline. Practice progress is saved on this device and will sync when you reconnect.')});
window.addEventListener('online',()=>{void recheckAuthOnReconnect()});
document.addEventListener('focusout',e=>{if(authRestoreStatus==='waiting'&&e.target.closest('#account-sync'))setTimeout(()=>void recheckAuthOnReconnect(),0)});
if(syncConfigured){setInterval(()=>{if(!document.hidden&&syncOwner)void startSync()},60000);
 setInterval(()=>{if(!document.hidden&&syncOwner&&now()-checkpointSyncAt>=12000)void syncCheckpoint()},12000);
}

const GUEST_STATE_KEY='shift-english-lab-v1';
const TAB_GUEST_STATE_KEY='shift/guest-tab-state/v1';
const tabOnlyWarning='Guest progress is saved only in this tab. Export a backup before closing it. For shared storage, export first, then open the site in a new tab.';
const guestStorage=()=>storageMode==='tabstorage'||storageMode==='memory'&&typeof navigator.locks?.request!=='function'?sessionStorage:localStorage;
const guestStorageKey=owner=>storageMode==='tabstorage'?TAB_GUEST_STATE_KEY:scopedKey(GUEST_STATE_KEY,owner);
const guestCanPersist=()=>['indexeddb','localstorage','tabstorage'].includes(storageMode);
const guestSaveLabel=()=>storageMode==='tabstorage'?'Saved in this tab only':'Saved in this browser';
async function initStorage(){
 // A tab-only snapshot is an independent workspace, not a cache of a new
 // shared workspace. Reopening working storage must not hide this tab's work.
 try{
  const tab=sessionStorage.getItem(TAB_GUEST_STATE_KEY);
  if(tab){
   const stored=JSON.parse(tab),saved=normalizeState(stored);
   state=saved;seedGuest(state,stored);storageMode='tabstorage';return
  }
 }catch(e){console.warn('Could not reopen this tab’s saved records',e)}
 try{
  db=await new Promise((resolve,reject)=>{const req=indexedDB.open(GUEST_STATE_KEY,1);req.onupgradeneeded=()=>req.result.createObjectStore('kv');req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);req.onblocked=()=>reject(new Error('The database is in use by another tab'))});
  const stored=await new Promise((resolve,reject)=>{const r=db.transaction('kv').objectStore('kv').get('state');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
  if(stored)state=normalizeState(stored);
  seedGuest(state,stored);
  storageMode='indexeddb';db.onversionchange=()=>{db.close();storageMode='memory';notify('Storage has changed. Export a backup and reopen the app.')};
  await persist();return
 }catch(e){console.warn('IndexedDB unavailable',e)}
 let legacy=null;
 try{legacy=localStorage.getItem(GUEST_STATE_KEY)}catch{}
 if(typeof navigator.locks?.request==='function')try{
  localStorage.setItem('shift-probe','1');localStorage.removeItem('shift-probe');
  const stored=legacy?JSON.parse(legacy):null;if(stored)state=normalizeState(stored);
  seedGuest(state,stored);storageMode='localstorage';return
 }catch(e){console.warn('Shared backup storage unavailable',e)}
 // Without Web Locks a shared localStorage read-modify-write is unsafe.
 // Keep old shared records readable, never overwrite them, and continue only
 // in this tab's independent cache (including on reload).
 try{
  const stored=legacy?JSON.parse(legacy):null;
  if(stored)state=normalizeState(stored);
  sessionStorage.setItem(TAB_GUEST_STATE_KEY,legacy||JSON.stringify(state));
  // Read legacy recovery data once; never clear or modify the shared draft.
  try{
   const raw=localStorage.getItem(NOTE_DRAFT_KEY);
   const draft=raw?JSON.parse(raw):null;
   if(!sessionStorage.getItem(NOTE_DRAFT_KEY)&&validNoteDraft(draft)&&draft.epoch===guestEpoch(state))
    sessionStorage.setItem(NOTE_DRAFT_KEY,raw)
  }catch(e){console.warn('Could not copy the legacy note draft to this tab',e)}
  seedGuest(state,stored);storageMode='tabstorage';
 }catch(e){storageMode='memory'}
}
function seedGuest(current,stored){
 guestBaseline=JSON.parse(JSON.stringify(current));
 guestActiveRevision=stored?.guestActiveRevision??null;
 guestSavedAnswerKey=guestAnswerKey(current.active)
}
const guestEpoch=s=>s?.noteDraftEpoch||'initial';
const guestEqual=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const guestAnswerKey=a=>JSON.stringify(Object.entries(a?.answers||{}).sort(([x],[y])=>x.localeCompare(y)));
const guestChangedElsewhere='Changes could not be saved because guest records were restored or cleared in another tab. Reload this tab before making more changes.';
const guestSessionElsewhere='This unfinished session could not be saved because it changed in another tab. Open Practice Home in that tab to continue.';
function applyGuestWrite(stored,{base,next,mode}){
 // Only an explicit, confirmed replace may discard another tab's history.
 if(mode==='restore'||mode==='clear'){
  const replacement=mode==='clear'&&stored?{...next,importedPacks:stored.importedPacks||[]}:next;
  const revision=uid();
  return {value:{...replacement,guestActiveRevision:revision},activeCommit:[revision,guestAnswerKey(replacement.active)]}
 }
 if(!base)return {};
 if(guestEpoch(base)!==guestEpoch(stored))return {warning:guestChangedElsewhere,blocked:true};
 const durable=stored||base;
 const starting=mode?.type==='start';
 if(starting&&(durable.active?.id??null)!==mode.replacedId)
  return {warning:'The new session could not be opened because another tab started or finished a session. Reopen Practice Home and try again.',blocked:true};
 const sameRevision=(durable.guestActiveRevision??null)===guestActiveRevision;
 const activeChanged=!guestEqual(base.active,next.active);
 const ownsActive=base.active?.id===durable.active?.id&&sameRevision;
 const finishing=!!base.active&&!next.active;
 // Moving the resume pointer does not make a stale earlier revision valid.
 // A displaced session can be scored only from its last durable revision,
 // with no answer edits made after the last acknowledged save in this tab.
 const lineage=Array.isArray(durable.guestSupersededSessions)?durable.guestSupersededSessions:[];
 const prior=finishing?lineage.find(x=>x.id===base.active.id):null;
 const canon=finishing&&(ownsActive||(prior&&prior.revision===guestActiveRevision&&guestAnswerKey(base.active)===guestSavedAnswerKey));
 const rejectFinish=finishing&&(!canon||durable.sessions.some(s=>s.id===base.active.id));
 const warning=activeChanged&&(!ownsActive&&!starting&&(!finishing||rejectFinish))?guestSessionElsewhere:null;
 if(rejectFinish)return {warning:guestSessionElsewhere,blocked:true};
 const result={...durable};
 let changed=false;
 for(const key of ['settings','stars','notes']){
  const before=base[key]||{},after=next[key]||{},merged={...(durable[key]||{})};
  for(const id of new Set([...Object.keys(before),...Object.keys(after)])){
   if((key==='stars'?!!before[id]===!!after[id]:guestEqual(before[id],after[id])))continue;
   if(!Object.hasOwn(after,id)||key==='stars'&&!after[id])delete merged[id];else merged[id]=after[id];
   changed=true
  }
  result[key]=merged
 }
 const packsBefore=new Map(base.importedPacks.map(p=>[p.testId,p]));
 const updated=next.importedPacks.filter(p=>packsBefore.get(p.testId)!==p&&!guestEqual(packsBefore.get(p.testId),p));
 if(updated.length){
  const packs=new Map((durable.importedPacks||[]).map(p=>[p.testId,p]));
  for(const p of updated)packs.set(p.testId,p);
  result.importedPacks=[...packs.values()];changed=true
 }
 // Guest history is append-only except after explicit replacement. Include even
 // standalone attempt records supported by old backups, not only session rows.
 if(next.attempts.length>base.attempts.length||next.sessions.length>base.sessions.length){
  const attempts=new Map(durable.attempts.map(x=>[x.id,x]));
  const sessions=new Map(durable.sessions.map(x=>[x.id,x]));
  for(const a of next.attempts.slice(base.attempts.length))if(!attempts.has(a.id))attempts.set(a.id,a);
  for(const s of next.sessions.slice(base.sessions.length))if(!sessions.has(s.id))sessions.set(s.id,s);
  const sorted=[...sessions.values()].sort((a,b)=>a.finishedAt-b.finishedAt||a.id.localeCompare(b.id));
  const history=normalizeState({formatVersion:1,attempts:[...attempts.values()],sessions:sorted});
  Object.assign(result,{attempts:history.attempts,sessions:history.sessions,stats:history.stats});
  changed=true
 }
 // Only explicit starts displace the resume target. Preserve the previous
 // revision for eligibility, not its unfinished content. Forgotten sessions
 // fail closed rather than allowing a stale completion after the ledger cap.
 if(starting&&durable.active){
  const displaced={id:durable.active.id,revision:durable.guestActiveRevision??null};
  result.guestSupersededSessions=[...lineage.filter(x=>x.id!==displaced.id),displaced].slice(-128);
 }
 if(finishing&&prior)result.guestSupersededSessions=lineage.filter(x=>x.id!==base.active.id);
 let activeCommit;
 if(activeChanged&&(starting||ownsActive)){
  result.active=next.active;result.guestActiveRevision=uid();
  activeCommit=[result.guestActiveRevision,guestAnswerKey(next.active)];
  changed=true
 }
 return {value:changed?result:undefined,warning,activeCommit}
}
function applyAccountWrite(stored,before,next,revision,historyOnly,conflicted){
 const durable=stored||blankWorkspace();
 if(historyOnly)return {value:{...durable,...records.localUnion(durable,next,normalizeState)}};
 if(!before)throw Error('Account workspace not ready');
 const activeChanged=!guestEqual(before.active,next.active);
 const finishing=!!before.active&&!next.active&&next.sessions.some(s=>s.id===before.active.id);
 const owns=(durable.active?.id??null)===(before.active?.id??null)&&(durable.accountActiveRevision??null)===revision;
 if((activeChanged||finishing)&&(!owns||conflicted))return {blocked:true};
 const result={...durable,...records.localUnion(durable,next,normalizeState)};
 for(const key of ['settings','stars','notes']){
  const old=before[key]||{},edited=next[key]||{},merged={...(durable[key]||{})};
  for(const id of new Set([...Object.keys(old),...Object.keys(edited)])){
   if(guestEqual(old[id],edited[id]))continue;
   if(!Object.hasOwn(edited,id)||key==='stars'&&!edited[id])delete merged[id];else merged[id]=edited[id];
  }
  result[key]=merged;
 }
 const priorPacks=new Map(before.importedPacks.map(p=>[p.testId,p]));
 const packs=new Map((durable.importedPacks||[]).map(p=>[p.testId,p]));
 for(const p of next.importedPacks)if(!guestEqual(priorPacks.get(p.testId),p))packs.set(p.testId,p);
 result.importedPacks=[...packs.values()];
 if(!guestEqual(before.lastBackup,next.lastBackup))result.lastBackup=next.lastBackup;
 if(activeChanged){result.active=next.active;result.accountActiveRevision=uid()}
 return {value:result,activeChanged};
}
// Imported packs are immutable data. Preserve their unchanged references only
// across guest progress snapshots in IndexedDB; never change the saved format.
const immutableGuestPacks=new WeakSet();
function makeImmutableGuestPack(pack){
 if(!pack||typeof pack!=='object')return false;
 if(immutableGuestPacks.has(pack))return true;
 const seen=new WeakSet(),todo=[pack],objects=[];
 while(todo.length){
  const v=todo.pop(),type=typeof v;
  if(v===null||type==='string'||type==='boolean'||type==='number'&&Number.isFinite(v)&&!Object.is(v,-0))continue;
  if(type!=='object'||seen.has(v))return false;
  if(Array.isArray(v)){
   if(Object.getPrototypeOf(v)!==Array.prototype||Object.keys(v).length!==v.length)return false
  }else if(Object.getPrototypeOf(v)!==Object.prototype)return false;
  seen.add(v);objects.push(v);
  for(const k of Reflect.ownKeys(v)){
   if(Array.isArray(v)&&k==='length')continue;
   const d=Object.getOwnPropertyDescriptor(v,k);
   if(typeof k!=='string'||!d?.enumerable||!Object.hasOwn(d,'value'))return false;
   if(Array.isArray(v)&&(!/^(0|[1-9][0-9]*)$/.test(k)||Number(k)>=v.length))return false;
   todo.push(d.value)
  }
 }
 // Validate the entire graph before freezing anything. Stored records from
 // older formats that aren't plain JSON use the ordinary snapshot path.
 for(const v of objects)Object.freeze(v);
 immutableGuestPacks.add(pack);
 return true
}
function captureGuestProgress(source){
 const {importedPacks,...progress}=source;
 if(!Array.isArray(importedPacks)||!importedPacks.length||!importedPacks.every(makeImmutableGuestPack))return null;
 const next=JSON.parse(JSON.stringify(progress));
 next.importedPacks=importedPacks.slice();
 return next
}
function persist(strict=false,historyOnly=false,guestMode=null,guestSubmission=null,restoreSnapshot=null){
 if(guestSubmitPending&&!guestSubmission&&!syncOwner)return strict?Promise.reject(new Error('Finish saving the current session before restoring a backup')):Promise.resolve();
 if(diagnostic||storageMode==='loading'||storageMode==='memory'){
  if(guestSubmission){localSaveFailure=true;notify(localSaveMessage);updateStorageBadge()}
  return strict?Promise.reject(new Error('Local saving unavailable')):Promise.resolve(guestSubmission?false:undefined)
 }
 if(!historyOnly&&!restoreSnapshot)saveListeningCountdown();
 const owner=syncOwner,source=restoreSnapshot||guestSubmission||state;
 const captured=!owner&&!guestSubmission&&!historyOnly&&!guestMode&&storageMode==='indexeddb'?captureGuestProgress(source):null;
 const snapshot=captured?null:JSON.stringify(source);
 const guestWrite=owner?null:{base:null,next:captured||JSON.parse(snapshot),mode:guestMode};
 // Capture the user action at call time, but compare against this tab's last
 // committed state at transaction time. A rejected write is never our baseline.
 let guestWarning=null,guestBlocked=false,activeCommit=null,writeMode=null,accountOutcome=null;
 const mergeGuest=stored=>{
  const outcome=applyGuestWrite(stored,guestWrite);
  guestWarning=outcome.warning;guestBlocked=!!outcome.blocked;activeCommit=outcome.activeCommit;
  return outcome.value
 };
 const writeOnce=()=>new Promise((resolve,reject)=>{
  guestWarning=null;guestBlocked=false;activeCommit=null;
  writeMode=storageMode;
  if(storageMode==='indexeddb'&&db){
   const tx=db.transaction('kv','readwrite'),store=tx.objectStore('kv'),key=scopedKey('state',owner);
   tx.oncomplete=resolve;
   // Wait until abort completes before retrying; each replay uses a new transaction.
   tx.onabort=()=>reject(tx.error||new DOMException('Saving was interrupted','AbortError'));
   if(!owner){
    const request=store.get(key);
    request.onsuccess=()=>{
     try{const value=mergeGuest(request.result);if(value)store.put(value,key)}
     catch(error){try{tx.onabort=()=>reject(error);tx.abort()}catch{reject(error)}}
    };
    return
   }
   const next=JSON.parse(snapshot);
   const req=store.get(key);
   req.onsuccess=()=>{
    try{
     accountOutcome=applyAccountWrite(req.result,accountBaseline,next,accountActiveRevision,historyOnly,accountActiveConflict);
     if(accountOutcome.value)store.put(accountOutcome.value,key);
    }catch(error){try{tx.onabort=()=>reject(error);tx.abort()}catch{reject(error)}}
   };
  }else{
   const mode=storageMode;
   const write=()=>{
    if(mode!==storageMode)throw Error('Storage changed before the write');
    const store=guestStorage(),key=guestStorageKey(owner);
    if(owner)throw Error('Account storage unavailable');
    else{
     const raw=store.getItem(key),value=mergeGuest(raw?JSON.parse(raw):null);
     if(value)store.setItem(key,JSON.stringify(value))
    }
   };
   if(mode==='tabstorage'){try{write();resolve()}catch(e){reject(e)}}
   else if(mode==='localstorage'&&typeof navigator.locks?.request==='function'){
    navigator.locks.request('shift-guest-localstorage-write',write).then(resolve,reject)
   }else reject(Error('Safe shared storage is unavailable'))

  }
 });
 const timeout=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 const operation=saveQueue.catch(()=>{}).then(async()=>{
  if(guestWrite)guestWrite.base=guestBaseline;
  for(let attempt=0;;attempt++){
   try{await writeOnce();break}
   catch(error){
    const transient=['AbortError','UnknownError','TimeoutError'].includes(error?.name);
    if(attempt>=3||!transient||writeMode!=='indexeddb'||storageMode!=='indexeddb')throw error;
    await timeout([40,100,240][attempt]);
   }
  }
  if(accountOutcome?.blocked){
   accountActiveConflict=true;
   clearTimeout(checkpointTimer);checkpointTimer=undefined;
   notify(accountActiveWarning);
   return false;
  }
  if(owner&&!historyOnly){
   accountBaseline=JSON.parse(snapshot);
   if(accountOutcome?.activeChanged)accountActiveRevision=accountOutcome.value.accountActiveRevision;
  }
  if(guestBlocked)return false;
  if(guestWrite)guestBaseline=guestWrite.next;
  if(activeCommit)[guestActiveRevision,guestSavedAnswerKey]=activeCommit;
  if(localSaveFailure&&!historyOnly&&!guestWarning){
   localSaveFailure=false;if(persistentError===localSaveMessage){persistentError='';showPersistentError()}updateStorageBadge();
  }
  return true
 }).catch(error=>{
  console.error(error);localSaveFailure=true;notify(localSaveMessage);updateStorageBadge();
  if(strict)throw error;
  return false
 });
 saveQueue=operation;
 return operation.then(saved=>{
  if(guestWarning)notify(guestWarning);
  if(!saved)return false;
  if(guestMode==='restore')return true;
  if(!guestSubmission&&!historyOnly&&!checkpointApplying&&!accountActiveConflict&&owner&&owner===syncOwner&&storageMode==='indexeddb'){
  const a=state.active,u=a?.audioUsed?.[currentAudioGroup],m=a?.practiceMedia;
  const signature=JSON.stringify(a?[a.id,a.index,a.answers,a.submitted,a.examPhase,a.readingStartsOnReturn,!!a.listeningStartedAt,u?.status,m?.groupId,m?.paused,m?.rate]:null);
  if(checkpointSignature!==signature||now()-checkpointSyncAt>=8000){
   if(signature!==checkpointSignature&&a&&navigator.onLine!==false)setCheckpointFeedback('Saving practice progress…');
   checkpointSignature=signature;scheduleCheckpoint()
  }
 }})
}
function readNoteDraft(){try{const raw=guestStorage().getItem(scopedKey(NOTE_DRAFT_KEY));return raw?JSON.parse(raw):null}catch(e){return null}}
function removeNoteDraft(token){try{if(readNoteDraft()?.token===token)guestStorage().removeItem(scopedKey(NOTE_DRAFT_KEY))}catch(e){}}
function noteStatusText(id){return noteStatuses.get(id)||(storageMode==='memory'?'Temporary storage only. Please export a backup.':state.notes[id]?guestSaveLabel():'Changes are saved automatically in this browser')}
function setNoteStatus(id,text){noteStatuses.set(id,text);const el=document.getElementById('note-save-status'),input=document.getElementById('question-note');if(el&&input?.dataset.id===id)el.textContent=text;const grouped=document.querySelector('[data-note-status="'+id+'"]');if(grouped)grouped.textContent=text}
function clearNoteDraft(keepEpoch=false){noteGeneration++;noteTokens.clear();noteStatuses.clear();if(!keepEpoch)state.noteDraftEpoch=uid();try{guestStorage().removeItem(scopedKey(NOTE_DRAFT_KEY))}catch(e){}}
function saveNoteInput(id,text){
if(diagnostic||!safeId(id))return;
const token=uid(),generation=noteGeneration,draft={version:1,token,epoch:state.noteDraftEpoch||'initial',questionId:id,text:String(text).slice(0,20000),at:now()};
state.notes[id]=draft.text;noteTokens.set(id,token);let cached=false;
try{guestStorage().setItem(scopedKey(NOTE_DRAFT_KEY),JSON.stringify(draft));cached=true}catch(e){}
setNoteStatus(id,'Saving…');
persist().then(saved=>{if(generation!==noteGeneration||noteTokens.get(id)!==token)return;if(saved===false){setNoteStatus(id,localSaveFailure||storageMode==='memory'?'Not saved. Keep this tab open and retry, or export a backup.':'Not saved. Reload after changes in another tab.');return}if(guestCanPersist()){removeNoteDraft(token);setNoteStatus(id,guestSaveLabel())}else setNoteStatus(id,cached?'Draft cached. Please export a backup.':'Not saved permanently. Please export a backup.')});
}
function validNoteDraft(draft){return !!draft&&draft.version===1&&safeId(draft.token)&&safeId(draft.questionId)&&typeof draft.text==='string'&&draft.text.length<=20000}
async function restoreNoteDraft(){
const draft=readNoteDraft();
if(!validNoteDraft(draft))return false;
if(draft.epoch!==(state.noteDraftEpoch||'initial')){removeNoteDraft(draft.token);return false}
const generation=noteGeneration;state.notes[draft.questionId]=draft.text;noteTokens.set(draft.questionId,draft.token);setNoteStatus(draft.questionId,'Restoring your note…');
const saved=await persist();
if(saved===false||generation!==noteGeneration||noteTokens.get(draft.questionId)!==draft.token)return false;
if(guestCanPersist()){removeNoteDraft(draft.token);setNoteStatus(draft.questionId,guestSaveLabel())}else setNoteStatus(draft.questionId,'Draft restored. Please export a backup.');
return true;
}
function storageBadgeWarning(){return localSaveFailure||storageMode==='memory'||storageMode==='tabstorage'}
function storageBadgeLabel(){return localSaveFailure?'Latest changes not saved':storageMode==='tabstorage'?'Saved in this tab only':storageMode==='memory'?'Temporary storage · Back up now':'Records saved locally'}
function updateStorageBadge(){const b=document.getElementById('storage-badge');if(b){b.innerHTML=icon(storageBadgeWarning()?'info':'shield')+storageBadgeLabel();b.classList.toggle('warn',storageBadgeWarning())}}
function validatePack(p){
if(!p||p.schemaVersion!==1||!safeId(p.testId)||!Array.isArray(p.questions)||!Array.isArray(p.groups)||p.questions.length<1||p.questions.length>5000)throw new Error('Invalid pack format. Expected schemaVersion: 1 and questions/groups.');
const gs=new Map(),ids=new Set(),numbers=new Set();if(p.listeningPlan){const frames=p.listeningPlan.frames;if(!Array.isArray(frames)||frames.length>5000||frames.some(f=>!f||!safeId(f.groupId)||!Number.isFinite(f.duration)||f.duration<=0||f.duration>2700||!['audio','silence'].includes(f.kind)||(f.kind==='audio'&&(!safeMedia(f.src)||!Number.isFinite(f.start)||f.start<0||!Number.isFinite(f.end)||f.end<=f.start||Math.abs(f.end-f.start-f.duration)>.2))))throw new Error('Invalid formal-listening plan')}
for(const g of p.groups){
if(!g||!safeId(g.id)||gs.has(g.id)||g.testId!==p.testId||![1,2,3,4,5,6,7].includes(g.part)||typeof g.passage!=='string'||typeof g.passageZh!=='string')throw new Error('Invalid group content, test ownership, or ID value:'+(g?.id||'unknown'));
if((g.audioStart!==undefined||g.audioEnd!==undefined)&&(!Number.isFinite(g.audioStart)||g.audioStart<0||!Number.isFinite(g.audioEnd)||g.audioEnd<=g.audioStart))throw new Error('Invalid audio segment');
if(g.audio&&!safeMedia(g.audio))throw new Error('Unsafe or unsupported audio path');
if(g.image&&!safeMedia(g.image))throw new Error('Unsafe or unsupported image path');
gs.set(g.id,g);
}
for(const q of p.questions){
if(!q||!safeId(q.id)||ids.has(q.id)||q.testId!==p.testId||![1,2,3,4,5,6,7].includes(q.part)||typeof q.prompt!=='string'||typeof q.promptZh!=='string'||typeof q.explanationZh!=='string'||!q.explanationZh.trim()||!Object.hasOwn(TOPICS,q.topic)||!Object.hasOwn(DIFFICULTY,q.difficulty)||!Array.isArray(q.options)||q.options.length!==(q.part===2?3:4))throw new Error('Invalid question:'+(q?.id||'unknown'));
if(!Number.isSafeInteger(q.number)||q.number<1||numbers.has(q.number))throw new Error('Question numbers must be unique positive integers within a test:'+q.id);
if(q.groupId&&!gs.has(q.groupId))throw new Error('Missing question group:'+q.groupId);
if(q.groupId&&gs.get(q.groupId).part!==q.part)throw new Error('The question and its group have different Part values:'+q.id);
if(q.tags&&(!Array.isArray(q.tags)||q.tags.some(t=>typeof t!=='string')))throw new Error('Invalid question tags:'+q.id);
const opts=new Set();
for(const o of q.options){if(!o||!['A','B','C','D'].includes(o.id)||opts.has(o.id)||typeof o.text!=='string'||typeof o.zh!=='string'||typeof o.whyZh!=='string'||!o.whyZh.trim())throw new Error('Missing option translation or explanation:'+q.id);opts.add(o.id)}
if(!opts.has(q.answer))throw new Error('Answer option does not exist:'+q.id);
if(q.vocabulary&&!Array.isArray(q.vocabulary))throw new Error('Invalid vocabulary format');
ids.add(q.id);numbers.add(q.number);
}
for(const plan of [p.listeningPlan,p.previousListeningPlan,...Object.values(p.alternateListeningPlans||{})]){
 if(plan?.groupAudio!==undefined)validateContinuousAudio(plan,gs);
}
return p;
}
function validateContinuousAudio(plan,groups){
 const map=plan.groupAudio,frames=plan.frames;
 if(!map||typeof map!=='object'||Array.isArray(map)||!Array.isArray(frames)||!frames.length)
  throw new Error('Invalid continuous formal-audio plan');
 const totals=new Map(),answers=new Set();let last=null,cursor=0;
 for(const f of frames){
  if(!f||!groups.has(f.groupId)||groups.get(f.groupId).part>4||!Number.isFinite(f.duration)||f.duration<=0||
     !Number.isFinite(f.at)||Math.abs(f.at-cursor)>.00005||!['audio','silence'].includes(f.kind))
   throw new Error('Invalid continuous formal-audio timeline');
  if(f.groupId!==last&&totals.has(f.groupId))throw new Error('Formal groups must be contiguous');
  totals.set(f.groupId,(totals.get(f.groupId)||0)+f.duration);
  if(f.role==='answer'){
   if(f.kind!=='silence'||!safeId(f.questionId)||answers.has(f.questionId))
    throw new Error('Formal answer windows need unique question IDs and silence');
   answers.add(f.questionId);
  }
  cursor+=f.duration;last=f.groupId;
 }
 const sources=new Set();
 if(Object.keys(map).length!==totals.size||!Number.isFinite(plan.duration)||plan.duration<=0||
    Math.abs(cursor-plan.duration)>.00005||answers.size!==100)throw new Error('Continuous formal listening requires all groups, 100 answers, and a matching declared duration');
 const sampleBound=plan.sampleRate!==undefined||plan.totalSamples!==undefined;
 let physicalSamples=0;
 if(sampleBound&&(plan.sampleRate!==48000||!Number.isSafeInteger(plan.totalSamples)||plan.totalSamples<=0||
    Math.abs(plan.duration-plan.totalSamples/48000)>1e-9))throw new Error('Invalid formal listening sample clock');
 for(const [id,duration] of totals){
  const m=Object.hasOwn(map,id)&&map[id];
  if(!m||!safeMedia(m.src)||!m.src.toLowerCase().endsWith('.ogg')||sources.has(m.src)||
     !Number.isFinite(m.duration)||Math.abs(m.duration-duration)>.00005)
   throw new Error('Invalid continuous formal-audio file for '+id);
  if(sampleBound){
   if(!Number.isSafeInteger(m.totalSamples)||m.totalSamples<=0||
      Math.abs(m.duration-m.totalSamples/48000)>1e-9)throw new Error('Invalid formal group sample count for '+id);
   physicalSamples+=m.totalSamples;
  }
  sources.add(m.src);
 }
 if(sampleBound&&physicalSamples!==plan.totalSamples)throw new Error('Formal listening group sample total mismatch');
}
function registerPack(p,official=false){
 validatePack(p);
 if(Boolean(officialEntry(p.testId))!==official)throw new Error('Pack is outside its catalog namespace.');
 const legacy=p.legacyQuestions||[];
 if(legacy.length){
  if(!official)throw new Error('Only built-in packs may include archived questions');
  validatePack({...p,questions:legacy});
 }
 const ids=new Set(p.questions.map(q=>q.id));
 for(const q of legacy)if(ids.has(q.id))throw new Error('Archived question ID conflict');
 for(const q of [...p.questions,...legacy])if(Q.has(q.id)&&Q.get(q.id).testId!==p.testId)throw new Error('Question ID already exists: '+q.id);
 for(const g of p.groups)if(G.has(g.id)&&G.get(g.id).testId!==p.testId)throw new Error('Group ID already exists: '+g.id);
 for(const[id,q]of Q)if(q.testId===p.testId){Q.delete(id);archivedIds.delete(id)}
 for(const[id,g]of G)if(g.testId===p.testId)G.delete(id);
 for(const q of legacy){Q.set(q.id,q);archivedIds.add(q.id)}
 for(const g of p.groups)G.set(g.id,g);
 for(const q of p.questions){Q.set(q.id,q);archivedIds.delete(q.id)}
 if(official)officialPacks.set(p.testId,p);
 loaded.add(p.testId)
}
async function loadTest(id){
 const t=officialEntry(id);
 if(t?officialPacks.has(id):loaded.has(id))return;
 if(loading.has(id))return loading.get(id);
 if(!t){
  const p=state.importedPacks.find(x=>x.testId===id&&!unavailableCustom.has(id));
  if(!p)throw new Error('Test pack not found: '+id);
  registerPack(p);return;
 }
 const promise=new Promise((resolve,reject)=>{
  const script=document.createElement('script');
  script.src=t.path+(location.protocol==='file:'?'':'?v='+encodeURIComponent(catalog.assetRevision||catalog.version||VERSION));
  script.onload=()=>{try{
   const p=(window.SHIFT_PACKS||[]).find(p=>p.testId===id);
   if(!p)throw new Error('The test-pack file has no content');
   registerPack(p,true);resolve()
  }catch(e){reject(e)}};
  script.onerror=()=>{script.remove();reject(new Error('Unable to load '+t.path+'. Extract the entire folder before opening index.html.'))};
  document.head.append(script)
 });
 loading.set(id,promise);try{await promise}finally{loading.delete(id)}
}
async function loadAllOfficial(){for(const t of catalog.tests)await loadTest(t.id)}
async function installPackIndexes(){
 Q=new Map();G=new Map();loaded=new Set();archivedIds.clear();officialPacks.clear();unavailableCustom.clear();
 for(const p of window.SHIFT_PACKS||[])if(officialEntry(p.testId))registerPack(p,true);
 if(!state.importedPacks.length)return;
 await loadAllOfficial();
 for(const p of state.importedPacks){
  try{registerPack(p)}catch(e){unavailableCustom.add(p.testId);console.warn('Custom pack not loaded:',p.testId,e.message)}
 }
}
async function loadAll(){for(const t of allTests())await loadTest(t.id)}
function customTest(p){return {id:p.testId,title:p.title||p.testId,subtitle:'Custom pack',reading:p.questions.filter(q=>q.part>4).length,listening:p.questions.filter(q=>q.part<5).length,imported:true}}
function allTests(){return catalog.tests.concat(state.importedPacks.filter(p=>!officialEntry(p.testId)&&!unavailableCustom.has(p.testId)).map(customTest))}
function allQuestions(){return [...Q.values()].filter(q=>!archivedIds.has(q.id))}
function relatedQuestions(q){if(!q.groupId)return [q];return allQuestions().filter(x=>x.groupId===q.groupId&&x.number!==q.number).concat(q).sort((a,b)=>a.number-b.number)}
function statsSummary(){const a=state.attempts;const correct=a.filter(x=>x.correct).length;const wrongIds=Object.keys(state.stats).filter(id=>state.stats[id].needsReview);return {attempts:a.length,correct,accuracy:a.length?Math.round(correct/a.length*100):null,unique:Object.keys(state.stats).length,wrongIds,stars:Object.keys(state.stars).filter(k=>state.stars[k]).length}}
function shuffle(arr){const a=arr.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
function topicIcon(t){return {technology:'chip',manufacturing:'factory',business:'briefcase',daily:'coffee'}[t]||'book'}
function heading(title,sub,eyebrow='YOUR LEARNING SPACE'){return '<div class="page-heading"><div><p class="eyebrow">'+esc(eyebrow)+'</p><h1 class="page-title">'+esc(title)+'</h1><p class="page-sub">'+esc(sub)+'</p></div><span class="date-label">'+new Intl.DateTimeFormat('en-US',{month:'long',day:'numeric',weekday:'long'}).format(new Date())+'</span></div>'}
function btn(text,action,cls='',extra=''){return '<button class="btn '+cls+'" data-action="'+action+'" '+extra+'>'+text+'</button>'}
function shell(content){
 if(diagnostic){
  app.innerHTML='<div class="workspace" data-playback-diagnostic><header class="topbar"><a class="btn small" href="'+diagnosticBack+'">'+icon('back')+' Question Debug</a><span class="status-pill">Diagnostic · No records saved</span></header><main class="main" id="main" tabindex="-1">'+content+'</main></div>';
  return
 }
 const narrow=window.matchMedia?.('(max-width:760px)').matches;document.querySelector('.skip-link')?.toggleAttribute('inert',!!(narrow&&mobileNav));const s=statsSummary();const nav=[['home','home','Practice Home'],['practice','book','Practice by Topic'],['review','review','Review Mistakes',s.wrongIds.length],['favorites','star','Saved Questions',s.stars],['stats','chart','Learning History'],['data','folder','Data & Settings']];const title={home:'Practice Home',practice:'Practice by Topic',review:'Review Mistakes',favorites:'Saved Questions',stats:'Learning History',data:'Data & Settings',quiz:'Practice in Progress',result:'Results','answer-review':'Answer Explanation'}[route];app.innerHTML='<div class="layout"><div class="mobile-overlay '+(mobileNav?'open':'')+'" data-action="menu-close"></div><aside id="shift-sidebar" class="sidebar '+(mobileNav?'open':'')+'" '+(narrow&&!mobileNav?'inert':narrow&&mobileNav?'role="dialog" aria-modal="true" aria-label="Site navigation"':'')+'><button class="sidebar-close" data-action="menu-close" aria-label="Close navigation">'+icon('close')+'</button><a href="#" class="brand" data-action="nav-home"><span class="brand-symbol">S<span>↗</span></span><span><span class="brand-name">SHIFT</span><span class="brand-sub" style="display:block">ENGLISH LAB</span></span></a><div class="nav-label">MY PRACTICE SPACE</div><nav aria-label="Main navigation">'+nav.map(([r,i,t,c])=>'<button class="nav-item '+(route===r?'active':'')+'" data-action="nav-'+r+'" '+(route===r?'aria-current="page"':'')+'>'+icon(i)+'<span>'+t+'</span>'+(c?'<span class="nav-count">'+c+'</span>':'')+'</button>').join('')+'</nav><div class="sidebar-bottom"><span class="local-dot"></span>Practice at your own pace<p>Technology · Manufacturing · Everyday Life<br>Build your English, one question at a time.</p><p>VERSION '+esc(VERSION)+'</p></div></aside><div class="workspace" '+(narrow&&mobileNav?'inert':'')+'><header class="topbar"><div class="breadcrumbs"><button class="mobile-menu" data-action="menu" aria-controls="shift-sidebar" aria-expanded="'+(mobileNav?'true':'false')+'" aria-label="Open menu">'+icon('menu')+'</button><span>Learning Space /</span><strong>'+title+'</strong></div><div class="top-actions"><span class="status-pill '+(storageBadgeWarning()?'warn':'')+'" id="storage-badge">'+icon(storageBadgeWarning()?'info':'shield')+storageBadgeLabel()+'</span>'+authHeaderHtml()+'</div></header>'+(storageMode==='memory'?'<div class="storage-alert">This browser cannot save your data. Export your learning records from Data & Settings before leaving.</div>':storageMode==='tabstorage'?'<div class="storage-alert" role="status">'+tabOnlyWarning+'</div>':'')+'<main class="main" id="main" tabindex="-1">'+persistentErrorHtml()+checkpointUi()+content+'<footer class="footer-note"><span>Original English practice content · Not ETS official questions or score assessment</span><span>SHIFT ENGLISH LAB · VERSION '+esc(VERSION)+'</span></footer></main></div></div>';document.documentElement.style.setProperty('--text-scale',state.settings.fontScale||1)}
function heroArt(){return '<svg viewBox="0 0 260 200" aria-hidden="true"><circle cx="138" cy="94" r="75" fill="#dfe8cc"/><path d="M22 163h207" stroke="#a4b391" stroke-width="1.5"/><g transform="rotate(-9 112 100)"><rect x="57" y="49" width="110" height="124" rx="8" fill="#46664b"/><rect x="63" y="43" width="110" height="124" rx="7" fill="#fafbf1" stroke="#a5b693"/><path d="M81 69h64M81 80h44M81 111h64M81 122h56M81 133h44" stroke="#bdc9aa" stroke-width="4" stroke-linecap="round"/><rect x="81" y="91" width="29" height="9" rx="3" fill="#ddac7a"/><path d="m131 92 5 5 10-12" fill="none" stroke="#5b8052" stroke-width="3" stroke-linecap="round"/></g><rect x="164" y="115" width="53" height="47" rx="10" fill="#cca47b"/><path d="M217 126h7a10 10 0 0 1 0 20h-7" fill="none" stroke="#cca47b" stroke-width="6"/><path d="M181 106c-10-11 8-13 0-25M197 104c-9-10 9-14 0-25" stroke="#9dab89" fill="none" stroke-width="2" stroke-linecap="round"/><path d="m201 41 4 9 10 2-8 7 1 10-8-5-9 4 2-10-7-7 10-1z" fill="#e8bd80"/><path d="m33 86 8 8m-8 0 8-8" stroke="#8ca47d" stroke-width="2"/></svg>'}
function resumeBanner(){
 const active=state.active;if(!active)return '';
 const exam=active.mode==='exam',title='Resume '+(exam?'Formal Test':'Practice');
 const count=Object.keys(active.answers).length;
 return '<section class="resume-banner" aria-labelledby="resume-title"><span class="resume-icon">'+icon(exam?'clock':'book')+'</span><div><p class="eyebrow">CONTINUE WHERE YOU LEFT OFF</p><h2 id="resume-title">'+esc(displayEnglish(active.title))+'</h2><p>Question '+(active.index+1)+' of '+active.questionIds.length+' · '+count+' answered</p></div>'+
   btn(icon('play')+' '+title,'resume','primary resume-main')+'</section>'
}
function homePage(){const s=statsSummary(),total=allTests().reduce((a,t)=>a+t.reading+t.listening,0);let out=heading('A little English, every day.','From the workplace to everyday life, make every practice session count.','A LITTLE PRACTICE, EVERY DAY');out+='<div id="home-resume-slot">'+resumeBanner()+'</div>';out+='<section class="hero"><div><span class="tag">'+icon('leaf')+' Focused practice · Around 20 questions</span><h2>Start small.<br>Make progress today.</h2><p>Focus on your answers first. See your score and explanations after submission.</p><div class="btn-row">'+btn('Start Reading Practice '+icon('arrow'),'quick-reading','primary')+btn(icon('headphones')+' Listening Practice','quick-listening')+'<a class="btn" href="語音試聽.html?v='+encodeURIComponent(VERSION)+'">Compare Listening Voices</a></div></div><div class="hero-art">'+heroArt()+'</div></section>';out+='<div class="stats-grid">'+[['book',fmt(total),'Available questions','questions'],['check',fmt(s.unique),'Questions practiced','questions'],['target',s.accuracy===null?'—':s.accuracy,'Overall accuracy',s.accuracy===null?'':'%'],['review',fmt(s.wrongIds.length),'Questions to review','questions']].map(([i,v,l,u])=>'<div class="stat"><div class="stat-icon">'+icon(i)+'</div><div><div class="stat-value">'+v+'<small>'+u+'</small></div><div class="stat-label">'+l+'</div></div></div>').join('')+'</div><div class="home-columns"><section><div class="section-heading"><h2>Choose a test and start practicing</h2><span>'+allTests().length+' original tests</span></div><div class="test-list">';out+=allTests().map((t,i)=>'<article class="test-card"><div class="test-card-top"><div class="test-number">SET<b>'+String(i+1).padStart(2,'0')+'</b></div><div><h3>'+esc(displayEnglish(t.title,'Custom test pack'))+'</h3><p>'+esc(displayEnglish(t.subtitle,'Custom practice material'))+'</p></div></div><div class="test-card-footer"><div class="test-meta"><span>'+icon('book')+' Reading '+t.reading+'</span><span>'+icon('headphones')+' Listening '+t.listening+'</span></div><div class="btn-row">'+btn('Section Practice','test-pick','small','data-test="'+esc(t.id)+'"')+btn('Full Test '+icon('arrow'),'test-exam','primary small','data-test="'+esc(t.id)+'"')+'</div></div></article>').join('');out+='</div></section><aside class="home-side"><div><div class="section-heading"><h2>Review is progress, too</h2></div><div class="review-card"><div class="stat-icon">'+icon('review')+'</div><h3>'+(s.wrongIds.length?'There are '+s.wrongIds.length+' questions ready for another try':'Turn mistakes into learning notes')+'</h3><p>'+(s.wrongIds.length?'Revisit confusing points, read the option explanations, and try again.':'Incorrect answers are collected here automatically. Understanding matters more than memorizing.')+'</p>'+btn('Open Review List '+icon('arrow'),'nav-review')+'</div></div><div class="mini-card"><h3>'+icon('shield')+' '+(syncOwner?'Your account workspace':'Your learning stays on your device')+'</h3><p>'+(syncOwner?'Current practice and completed history sync to this account.':'No sign-in needed. Progress is saved in this browser. The website needs a connection for new test content; use an extracted copy of the complete package for offline practice.')+'</p></div></aside></div><div class="section-heading"><h2>Start with a familiar setting</h2>'+btn('All Topics '+icon('arrow'),'nav-practice','ghost small')+'</div><div class="topics-row">'+Object.entries(TOPICS).map(([id,label])=>'<button class="topic-card" data-action="topic" data-topic="'+id+'">'+icon(topicIcon(id))+'<b>'+label+'</b><small>'+({technology:'Specifications · Testing · Development',manufacturing:'Quality · Delivery · Production',business:'Meetings · Email · Collaboration',daily:'Transport · Dining · Travel'}[id])+'</small></button>').join('')+'</div>';return out}
function selectOptions(map,value,allLabel='All'){return '<option value="all" '+(value==='all'?'selected':'')+'>'+allLabel+'</option>'+Object.entries(map).map(([k,v])=>'<option value="'+esc(k)+'" '+(String(value)===k?'selected':'')+'>'+esc(v)+'</option>').join('')}
const ACCENTS={"en-US":"American English","en-GB":"British English","en-CA":"Canadian English","en-AU":"Australian English","en-IN":"Indian English","en-HK":"Hong Kong English","en-SG":"Singaporean English","en-PH":"Philippine English","en-NZ":"New Zealand English","en-IE":"Irish English","en-KE":"Kenyan English","en-NG":"Nigerian English","en-TZ":"Tanzanian English","en-ZA":"South African English"};
function accentMatches(q,accent){if(accent==='all')return true;const speakers=G.get(q.groupId)?.audioSpeakers;return q.part<5&&Array.isArray(speakers)&&speakers.length>0&&speakers.every(v=>v?.locale===accent)}
function practicePage(){return heading('Practice at your own pace.','Choose a question type, topic, and difficulty. Related questions stay together.','PRACTICE BY TOPIC')+'<section class="panel"><h2>Set up this practice session</h2><div class="filters"><div class="field"><label for="filter-section">Practice section</label><select id="filter-section">'+selectOptions({reading:'Reading Practice',listening:'Listening Practice'},filters.section,'Reading + Listening')+'</select></div><div class="field"><label for="filter-part">Question type</label><select id="filter-part">'+selectOptions(Object.fromEntries(Object.entries(PARTS).map(([k,v])=>[k,'Part '+k+' · '+v])),filters.part,'All question types')+'</select></div><div class="field"><label for="filter-accent">Listening accent focus</label><select id="filter-accent">'+selectOptions(ACCENTS,filters.accent,'Any accent (including mixed)')+'</select></div><div class="field"><label for="filter-topic">Topic</label><select id="filter-topic">'+selectOptions(TOPICS,filters.topic,'All topics')+'</select></div><div class="field"><label for="filter-difficulty">Difficulty</label><select id="filter-difficulty">'+selectOptions(DIFFICULTY,filters.difficulty,'All difficulties')+'</select></div><div class="field"><label for="filter-count">Target question count</label><select id="filter-count">'+[10,20,40,100].map(n=>'<option value="'+n+'" '+(filters.count===n?'selected':'')+'>'+n+' questions approximately</option>').join('')+'</select></div></div><label class="check-row"><input type="checkbox" id="filter-unseen" '+(filters.unseen?'checked':'')+'>Prioritize questions not yet answered</label><p class="hint">Passages and conversations are selected as complete groups, so the question count may vary. If a topic or difficulty does not apply to every question in a group, that group is skipped. Prioritizing unanswered questions tries new groups first without splitting them. An accent filter includes only groups whose voices all have that accent label. Mixed and unlabeled groups are excluded; a shortfall is shown rather than filled with other accents. Labels describe synthetic voice models, not official accent certification. Submit the session to see your score and explanations.</p><div class="btn-row" style="margin-top:24px">'+btn('Start This Practice '+icon('arrow'),'start-filtered','primary')+'</div></section><div class="topics-row">'+Object.entries(TOPICS).map(([id,label])=>'<button class="topic-card" data-action="topic" data-topic="'+id+'">'+icon(topicIcon(id))+'<b>'+label+'</b><small>Choose this topic</small></button>').join('')+'</div>'}
async function withBusy(fn){if(busy||guestSubmitPending||guestBackupApplying)return;busy=true;try{await fn()}catch(e){console.error(e);notify(e.message||'Something went wrong. Please try again.')}finally{busy=false}}
async function navigate(dest){const fromDrawer=mobileNav;if(route==='quiz'||route==='answer-review'){stopAudio();await persist()}mobileNav=false;route=dest;syncListeningCountdown(state.active);if(listening())void persist();activeTranscript=null;listLimit=40;if(['review','favorites'].includes(dest)){shell('<div class="loading">Loading your learning records…</div>');await loadAll()}render();window.scrollTo({top:0,behavior:'instant'});if(fromDrawer)document.getElementById('main')?.focus({preventScroll:true});if(authRestoreStatus==='waiting'&&navigator.onLine!==false)void recheckAuthOnReconnect()}
function render(){if(!diagnostic)try{tabWrite(LAST_PAGE_TAB_KEY,route==='data'?'data':null);if(route==='quiz'&&state.active)sessionStorage.setItem(scopedKey('shift-last-quiz'),state.active.id);else sessionStorage.removeItem(scopedKey('shift-last-quiz'))}catch(e){}if(route==='home')shell(homePage());else if(route==='practice')shell(practicePage());else if(route==='review'||route==='favorites')shell(listPage());else if(route==='stats')shell(statsPage());else if(route==='data')shell(dataPage());else if(route==='quiz')renderQuizWithChartPosition();else if(route==='result')shell(resultPage());else if(route==='answer-review')shell(reviewDetailPage());syncAudioUI()}
function groupedSelection(pool,count){const units=new Map();for(const q of pool){const key=q.groupId||q.id;if(!units.has(key))units.set(key,[]);units.get(key).push(q)}const chosen=[];for(const unit of shuffle([...units.values()])){if(chosen.length>=count)break;const qs=unit[0].groupId?relatedQuestions(unit[0]).map(q=>unit.find(x=>x.number===q.number)||q):unit;chosen.push(...qs)}return chosen}
async function startSession(questions,title,mode='practice',startId=null){if(accountActiveConflict){notify(accountActiveWarning);return}if(!questions.length){notify('No questions match these filters. Try changing your selection.');return}
 const workspaceOwner=syncOwner;
 const guest=!workspaceOwner&&guestCanPersist();
 const durableActive=guest?(await backupSnapshot()).active:null;
 const begin=async()=>{
 if(syncOwner!==workspaceOwner){notify('The session could not be opened because the account workspace changed. Please try again.');return}
 const previous=state.active,previousResume=resumeEnv;
 const unique=[...new Map(questions.map(q=>[q.id,q])).values()];resumeEnv=null;state.active={id:syncOwner?crypto.randomUUID():'session-'+uid(),contentVersion:contentVersion(),title,mode,questionIds:unique.map(q=>q.id),testIds:[...new Set(unique.map(q=>q.testId))],index:Math.max(0,unique.findIndex(q=>q.id===startId)),answers:{},submitted:{},startedAt:now(),deadline:mode==='exam'?now()+120*60000:null,examVersion:mode==='exam'?2:1,audioEdition:FORMAL_EDITION,examPhase:'listening',sectionDeadline:null,listeningStartedAt:null,audioUsed:{}};if(await persist(false,false,guest?{type:'start',replacedId:durableActive?.id??null}:null)===false){
  state.active=previous;resumeEnv=previousResume;
  return
 }route='quiz';currentQuestionStart=now();activeTranscript=null;stopAudio();render();window.scrollTo({top:0,behavior:'instant'})};if(state.active||durableActive){confirmBox('Start a new practice session?',durableActive&&durableActive.id!==state.active?.id?'Another tab has an unfinished session. Starting a new one replaces the session offered when you reopen Practice Home. Submitted records and notes are kept.':'You have an unfinished session. Starting a new one replaces that unfinished progress. Submitted answers and notes are kept.',begin,'Start New Session')}else return begin()}
function answeredQuestionIds(attempts){
 const ids=new Set();
 for(const a of attempts)if(['A','B','C','D'].includes(a.selected))ids.add(a.questionId);
 return ids
}
function filteredGroupSelection(questions,f,getGroup=key=>G.get(key),hasAnswered){
 if(f.unseen&&!hasAnswered){
  const answered=answeredQuestionIds(state.attempts);
  hasAnswered=id=>answered.has(id)
 }
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
  const attempted=f.unseen?group.filter(q=>hasAnswered(q.id)).length:0;
  unseen[attempted===0?0:attempted<group.length?1:2].push(group.slice().sort((a,b)=>a.number-b.number))
 }
 const chosen=[];
 for(const g of unseen.flatMap(shuffle)){
  if(chosen.length>=Number(f.count))break;
  chosen.push(...g)
 }
 return chosen
}
async function startFiltered(override){await loadAll();const f=Object.assign({},filters,override||{});if(!Object.hasOwn(ACCENTS,f.accent))f.accent='all';if(f.accent!=='all'){f.section='listening';if(Number(f.part)>4)f.part='all'}const qs=filteredGroupSelection(allQuestions(),f);const label=f.accent!=='all'?ACCENTS[f.accent]+' focused practice':f.topic==='all'?'Daily Practice':TOPICS[f.topic]+' practice session';const short=qs.length<Number(f.count);const title=label+(short||f.accent!=='all'?' · '+qs.length+' questions':'')+(short?' (target '+f.count+'; not enough matching full groups)':'');await startSession(qs,title)}
function questionByActive(){return state.active?sessionQuestion(state.active.questionIds[state.active.index]):null}
function recordAnswer(q,selected,sessionId,seconds,workspace=state){const id=sessionId+':'+q.id;if(workspace.attempts.some(a=>a.id===id))return;const correct=selected===q.answer;workspace.attempts.push({id,questionId:q.id,testId:q.testId,revision:q.revision||1,correctAnswer:q.answer,part:q.part,topic:q.topic,selected,correct,at:now(),seconds:Math.min(3600,Math.max(0,Math.round(seconds||0)))});const st=workspace.stats[q.id]||(workspace.stats[q.id]={attempts:0,wrong:0,streak:0});st.attempts++;if(!correct)st.wrong++;st.streak=correct?st.streak+1:0;st.lastCorrect=correct;st.lastAt=now();st.testId=q.testId;st.part=q.part;st.topic=q.topic;st.due=now()+(correct?(st.streak<2?3:7):1)*86400000;st.needsReview=st.wrong>0&&st.streak<2}

let audioRun=0,formalRunning=false,formalElapsed=0,formalRole='',captureFormal=null,formalPaused=false,formalMedia=null;
const LISTENING_TAB_KEY='shift-formal-listening-refresh-v1';
function frameSignature(f,g,s=state.active){
 if(!f)return null;
 const parts=[f.kind,f.role,f.src||null,f.start??null,f.end??null,Number(f.duration)];
 const m=continuousGroupAudio(g,s);
 if(m)parts.push(m.src,m.duration);
 return JSON.stringify(parts);
}
function saveListeningTabPoint(){
 if(diagnostic||!formalRunning||route!=='quiz'||!listening()||!currentAudioGroup)return;
 captureFormal?.();
 const s=state.active,g=sessionGroup(currentAudioGroup,s),u=s.audioUsed?.[currentAudioGroup];
 if(!g||u?.status!=='started')return;
 const frames=groupFrames(g),f=frames[u.frame];if(!f)return;
 try{sessionStorage.setItem(scopedKey(LISTENING_TAB_KEY),JSON.stringify({
  id:s.id,startedAt:s.startedAt,version:s.contentVersion??null,edition:s.audioEdition,index:s.index,
  question:s.questionIds[s.index],group:g.id,frame:u.frame,offset:u.offset,signature:frameSignature(f,g,s)
 }))}catch{}
}
function restoreListeningTabPoint(s){
 let x;try{const raw=sessionStorage.getItem(scopedKey(LISTENING_TAB_KEY));sessionStorage.removeItem(scopedKey(LISTENING_TAB_KEY));x=JSON.parse(raw)}catch{return false}
 if(!listening(s)||!x||x.id!==s.id||x.startedAt!==s.startedAt||x.version!==(s.contentVersion??null)||
    x.edition!==s.audioEdition||x.index!==s.index||x.question!==s.questionIds[s.index])return false;
 const q=sessionQuestion(s.questionIds[s.index],s),g=q?.groupId&&sessionGroup(q.groupId,s);
 if(g?.id!==x.group)return false;
 const frames=groupFrames(g),f=frames[x.frame],u=s.audioUsed?.[g.id]; 
 if(!u||u.status==='ended'||!Number.isSafeInteger(x.frame)||x.frame<0||!f||
    x.signature!==frameSignature(f,g,s)||!Number.isFinite(x.offset)||x.offset<0||x.offset>Number(f.duration))return false;
 const old=resumePosition(u,frames);
 if(x.frame<old.frame||(x.frame===old.frame&&x.offset<=old.offset))return false;
 s.audioUsed[g.id]={...u,status:'interrupted',frame:x.frame,offset:x.offset};return true;
}
window.addEventListener?.('pagehide',()=>{saveListeningTabPoint();if(listening()&&route==='quiz')void persist()});

function formal(s=state.active){return !!s&&s.mode==='exam'&&s.examVersion===2}
function listening(s=state.active){return formal(s)&&s.examPhase==='listening'}
function groupQuestions(q=questionByActive()){const s=state.active;if(!q||!s)return [];return s.questionIds.map(id=>sessionQuestion(id,s)).filter(x=>x&&(q.groupId?x.groupId===q.groupId:x.id===q.id))}
const FORMAL_EDITION='toeic-1';
const FORMAL_STAGE_TITLES={intro:'Listening Test',direction:'Part Directions',example:'Part 1 · Unscored Example',closing:'Listening Complete'};
function formalPlan(g,s=state.active){
 const p=pinnedFor(s)?.packs.get(g.testId)||(officialEntry(g.testId)?officialPacks.get(g.testId):state.importedPacks.find(p=>p.testId===g.testId&&!unavailableCustom.has(p.testId)));
 if(!p||!officialEntry(g.testId))return p?.listeningPlan;
 return p.listeningPlan?.audioEdition===s?.audioEdition?p.listeningPlan:
   p.alternateListeningPlans?.[s?.audioEdition]||p.previousListeningPlan||p.listeningPlan;
}
function groupFrames(g){return (formalPlan(g)?.frames||[]).filter(f=>f.groupId===g.id)}
function continuousGroupAudio(g,s=state.active){
 const map=g&&formalPlan(g,s)?.groupAudio;
 return map&&Object.hasOwn(map,g.id)?map[g.id]:null;
}
function currentFormalStage(g,s=state.active){
 if(!g||!listening(s)||s.audioEdition!==FORMAL_EDITION)return '';
 if(formalRunning&&currentAudioGroup===g.id)return Object.hasOwn(FORMAL_STAGE_TITLES,formalRole)?formalRole:'';
 const u=s.audioUsed?.[g.id];
 if(u?.status==='ended')return '';
 const frames=groupFrames(g),head=frames[resumePosition(u,frames).frame]?.role;
 if(u)return Object.hasOwn(FORMAL_STAGE_TITLES,head)?head:'';
 return head==='intro'||head==='direction'?head:'';
}
function syncFormalStage(g){
 const stage=currentFormalStage(g), panel=document.querySelector('.formal-stage');
 if(!panel)return;
 panel.hidden=!stage;
 const title=panel.querySelector('h3');
 if(stage&&title.textContent!==FORMAL_STAGE_TITLES[stage])title.textContent=FORMAL_STAGE_TITLES[stage];
 panel.querySelector('.formal-example').hidden=stage!=='example';
 const lead=panel.querySelector('.formal-lead');
 lead.hidden=stage==='example';
 if(stage==='closing')lead.textContent='The reading section will begin next.';
 for(const x of document.querySelectorAll('.group-questions,.scored-graphic')) x.hidden=!!stage;
}

function mediaStart(g){return Number.isFinite(g?.audioStart)?Math.max(0,g.audioStart):0}
function mediaDuration(g){return Number.isFinite(g?.audioEnd)?Math.max(0,g.audioEnd-mediaStart(g)):g?.duration||0}
function groupSeconds(g){return groupFrames(g).reduce((v,f)=>v+(Number(f.duration)||0),0)}
function resumePosition(u,frames){
 const frame=Number.isSafeInteger(u?.frame)&&u.frame>=0&&u.frame<=frames.length?u.frame:0;
 const duration=Number(frames[frame]?.duration)||0;
 return {frame,offset:Math.max(0,Math.min(duration,Number(u?.offset)||0))};
}
function savedGroupElapsed(g,u){
 const frames=groupFrames(g);
 if(u?.status==='ended')return groupSeconds(g);
 const {frame,offset}=resumePosition(u,frames);
 return frames.slice(0,frame).reduce((sum,f)=>sum+(Number(f.duration)||0),offset);
}
function listeningDurationLabel(plan){
 const seconds=Number.isFinite(plan?.duration)&&plan.duration>0?Math.ceil(plan.duration):2700;
 const m=Math.floor(seconds/60),r=seconds%60;
 return m+' min'+(r?' '+r+' sec':'');
}
function listeningTimelineSeconds(s,g=sessionGroup(questionByActive()?.groupId,s)){
 if(!g)return 2700;
 const plan=formalPlan(g,s),frames=plan?.frames||[],first=frames.findIndex(f=>f.groupId===g.id);
 const before=first<0?0:frames.slice(0,first).reduce((sum,f)=>sum+(Number(f.duration)||0),0);
 return (Number(plan?.duration)||2700)-before-(formalRunning&&currentAudioGroup===g.id?formalElapsed:savedGroupElapsed(g,s.audioUsed?.[g.id]));
}
// Advance the listening display only as the media timeline advances visibly.
let formalCountdown=null;
function countdownFor(s){
 if(formalCountdown?.session!==s){
  const media=Math.max(0,listeningTimelineSeconds(s));
  const saved=Number.isFinite(s.listeningRemaining)?s.listeningRemaining:media;
  formalCountdown={session:s,left:Math.max(media,saved),position:media,charging:route==='quiz'&&!document.hidden,lastSave:performance.now()};
 }
 return formalCountdown;
}
function listeningCountdownLeft(c){
 const media=Math.max(0,listeningTimelineSeconds(c.session));
 const position=Math.min(c.position,media),travelled=c.position-position;
 if(c.charging)c.left=Math.max(position,c.left-travelled);
 c.position=position;
 return c.left;
}
function syncListeningCountdown(s){
 if(!listening(s)||!s.listeningStartedAt)return;
 const c=countdownFor(s);listeningCountdownLeft(c);
 c.charging=route==='quiz'&&!document.hidden;
}
function saveListeningCountdown(){
 const s=state.active,c=formalCountdown;
 if(c?.session===s&&listening(s)){
  s.listeningRemaining=listeningCountdownLeft(c);c.lastSave=performance.now();
 }
}
function examSeconds(s){
 if(!listening(s))return formal(s)&&s.readingStartsOnReturn?75*60:((formal(s)?s.sectionDeadline:s.deadline)-now())/1000;
 return listeningCountdownLeft(countdownFor(s));
}
function timerText(s,left=examSeconds(s)){return time(formal(s)?Math.ceil(left):left)}
function updateExamClock(left){
 const s=state.active,el=document.getElementById('timer');
 if(!el||!s||s.mode!=='exam'||listening(s)&&!s.listeningStartedAt)return;
 left??=examSeconds(s);
 el.innerHTML=icon('clock')+' '+timerText(s,left);el.classList.toggle('urgent',left<300);
}
const formalExpiryNotices=new WeakMap();
function formalClockExpired(s){
 if(diagnostic||!formal(s))return false;
 if(formalExpiryNotices.has(s))return true;
 if(listening(s)){
  if(!s.listeningStartedAt)return false;
  const last=s.questionIds.findLast(id=>sessionQuestion(id,s)?.part<5);
  return !!last&&s.audioUsed?.[sessionQuestion(last,s)?.groupId]?.status==='ended';
 }
 return !s.readingStartsOnReturn&&Number.isFinite(s.sectionDeadline)&&now()>=s.sectionDeadline;
}
function closeFormalExpiryNotice(){
 const d=document.getElementById('modal'),title=document.getElementById('formal-expiry-title');
 if(title){if(d.open)d.close();d.removeAttribute('closedby');d.removeAttribute('aria-labelledby');d.removeAttribute('aria-describedby');title.removeAttribute('id')}
}
function showFormalExpiryNotice(s,pending){
 if(route!=='quiz'||pending.listening&&document.hidden)return;
 if(pending.until===null){
  pending.until=now()+5000;
  setTimeout(advanceExpiredFormalPhase,5000);
 }
 const d=document.getElementById('modal');
 let title=document.getElementById('formal-expiry-title');
 if(!title){
  if(d.open)closeModal();
  d.setAttribute('closedby','none');
  const what=pending.listening?'Listening':'Reading';
  const next=pending.listening?'Reading will start automatically in 5 seconds.':'Your test will be submitted and scored in 5 seconds.';
  modal('<h2 id="formal-expiry-title" tabindex="-1">'+what+' · Time is up</h2><p id="formal-expiry-message">You can no longer answer or change answers in this section. '+next+'</p>');
  d.setAttribute('aria-labelledby','formal-expiry-title');d.setAttribute('aria-describedby','formal-expiry-message');
  title=document.getElementById('formal-expiry-title');title?.focus({preventScroll:true});
 }else if(!d.open){
  d.showModal();title.focus({preventScroll:true});
 }
}
function beginFormalExpiry(s){
 if(diagnostic||!formal(s)||s!==state.active)return;
 const old=formalExpiryNotices.get(s);
 if(old){if(!old.transitioning)showFormalExpiryNotice(s,old);return;}
 const pending={listening:listening(s),until:listening(s)?null:now()+5000,transitioning:false};
 formalExpiryNotices.set(s,pending);
 if(pending.listening){
  stopAudio();const c=countdownFor(s);c.left=0;c.position=0;c.charging=false;s.listeningRemaining=0;
  if(!diagnostic)void persist();
 }
 updateExamClock(0);showFormalExpiryNotice(s,pending);
 if(!pending.listening)setTimeout(advanceExpiredFormalPhase,5000);
}
function advanceExpiredFormalPhase(){
 const s=state.active,pending=s&&formalExpiryNotices.get(s);
 if(!pending||pending.transitioning||pending.until===null||now()<pending.until||busy||guestSubmitPending)return;
 pending.transitioning=true;
 void withBusy(async()=>{
  try{
   if(state.active!==s)return;
   closeFormalExpiryNotice();
   if(pending.listening&&s.questionIds.some(id=>sessionQuestion(id,s)?.part>=5)){
    await enterReading();formalExpiryNotices.delete(s);
   }else{
    await loadAll();await finishSession(true);
   }
  }catch(e){pending.transitioning=false;throw e;}
 });
}
document.getElementById('modal').addEventListener('cancel',e=>{if(document.getElementById('formal-expiry-title'))e.preventDefault()});
document.getElementById('modal').addEventListener('keydown',e=>{
 if(e.key==='Escape'&&document.getElementById('formal-expiry-title')){e.preventDefault();e.stopPropagation()}
},true);
function groupReady(g){return state.active?.audioUsed?.[g?.id]?.status==='ended'}
function stopAudio(keepNativeSource=false){
 stopPracticeRangeTimer();
 if(savePracticeMedia(true))void persist();
 captureFormal?.();captureFormal=null;formalMedia=null;formalPaused=false;
 audioRun++;cancelPracticePosition();formalRunning=false;formalRole='';
 const u=state.active?.audioUsed?.[currentAudioGroup];
 if(u?.status==='started'){u.status='interrupted';void persist()}
 // In a continuous formal start, avoid an extra empty-resource reset.
 if(keepNativeSource){if(!player.paused)player.pause()}
 else{player.pause();player.removeAttribute('src');player.load()}
 player.playbackRate=1;currentAudioGroup=null;formalElapsed=0;
}
// If listening ends in the background, the new Reading clock starts on return.
function beginReadingClock(s){
 if(!formal(s)||s.examPhase!=='reading'||!s.readingStartsOnReturn||document.hidden)return false;
 s.sectionDeadline=now()+75*60000;s.deadline=s.sectionDeadline;delete s.readingStartsOnReturn;
 return true;
}
async function enterReading(){const s=state.active;if(!formal(s)||s.examPhase==='reading')return;stopAudio();const idx=s.questionIds.findIndex(id=>sessionQuestion(id,s)?.part>=5);if(idx<0)return finishSession(true);s.examPhase='reading';s.index=idx;s.sectionDeadline=null;s.readingStartsOnReturn=true;beginReadingClock(s);await persist();if(route==='quiz')render();notify('Listening is complete. Reading lasts 75 minutes. Listening answers are now locked.')}
function questionReference(id){
 const uuid=window.SHIFT_QUESTION_UUID(id);
 return '<div class="question-reference"><span>UUID: <code dir="ltr">'+uuid+'</code></span><button type="button" class="copy-question-uuid" data-action="copy-question-uuid" aria-label="Copy question UUID '+uuid+'">Copy</button></div>';
}
async function copyQuestionUuid(el){
 const code=el.parentElement.querySelector('code');
 if(!code)return;
 const uuid=code.textContent;
 try{await navigator.clipboard.writeText(uuid);notify('Question UUID copied.');return}catch(e){}
 const selection=window.getSelection();
 if(!selection)return notify('Select and copy the UUID shown on the question.');
 const previous=Array.from({length:selection.rangeCount},(_,i)=>selection.getRangeAt(i).cloneRange());
 const range=document.createRange();range.selectNodeContents(code);
 selection.removeAllRanges();selection.addRange(range);
 try{
  if(document.execCommand('copy')){
   selection.removeAllRanges();previous.forEach(r=>selection.addRange(r));
   notify('Question UUID copied.');return;
  }
 }catch(e){}
 notify('Copy unavailable. The UUID is selected for manual copying.');
}
function questionCard(q,s){const selected=s.answers[q.id],hidden=q.part<=2;return '<article class="question-panel grouped-question" data-question-id="'+q.id+'"><div class="panel-head"><span>Part '+q.part+' · Q'+q.number+'</span><span class="tag">'+(selected?'Answered':'Unanswered')+'</span></div><div class="panel-body"><div class="question-top"><span class="question-number">Question '+(s.questionIds.indexOf(q.id)+1)+' of '+s.questionIds.length+'</span><button class="icon-button '+(state.stars[q.id]?'starred':'')+'" data-action="star" data-id="'+q.id+'" aria-label="Save question">'+icon('star')+'</button></div>'+questionReference(q.id)+'<h2 class="question-text">'+(q.part===2?'Listen to the question and three responses, then choose the best answer.':q.part===1?'Look at the picture, listen to four statements, and choose the best answer.':esc(q.prompt))+'</h2><div class="options" role="group" aria-label="Question '+q.number+' answer options">'+q.options.map(o=>'<button class="option '+(o.id===selected?'selected':'')+'" data-action="answer" data-question="'+q.id+'" data-option="'+o.id+'" aria-pressed="'+(o.id===selected)+'"><span class="option-letter">'+o.id+'</span><span class="option-text">'+(hidden?'Choose '+o.id:esc(o.text))+'</span></button>').join('')+'</div><p class="hint">'+(selected?'Selected '+selected+'. You can change this answer before leaving the page.':'Answers, translations, and explanations are hidden until submission.')+'</p>'+(!formal(s)?'<details class="note-box"><summary>My Notes</summary><textarea class="group-note" data-id="'+q.id+'" maxlength="20000" aria-label="Question '+q.number+' notes">'+esc(state.notes[q.id]||'')+'</textarea><div class="word-count" data-note-status="'+q.id+'">'+esc(noteStatusText(q.id))+'</div></details>':'')+'</div></article>'}

function formalStageCard(g,s){
 if(!listening(s)||s.audioEdition!==FORMAL_EDITION)return '';
 const stage=currentFormalStage(g,s);
 return '<div class="formal-stage" '+(stage?'':'hidden')+'><h3 role="status">'+esc(FORMAL_STAGE_TITLES[stage]||'')+'</h3><p class="formal-lead" '+(stage==='example'?'hidden':'')+'>'+esc(stage==='closing'?'The reading section will begin next.':'Listen to the directions before the questions begin.')+'</p><div class="formal-example" '+(stage==='example'?'':'hidden')+'><img class="scene-img" src="assets/scenes/formal-example.svg" alt="Unscored example showing a lamp and mug on a desk"></div></div>';
}

function officialReviewedChart(g){
 return g?.testId==='test-04'&&['t04-g041','t04-g053'].includes(g.id)||
  g?.testId==='test-05'&&g.id==='t05-g092'&&!!officialEntry('test-05')&&
  g.image==='assets/scenes/test-05/dispatch-map.jpg'&&g.chartWidthPx===1020||
  g?.testId==='test-06'&&g.id==='t06-g056'&&!!officialEntry('test-06')&&
  g.image==='assets/scenes/test-06/room-access.jpg'&&g.chartWidthPx===1000||
  g?.testId==='test-07'&&g.id==='t07-r-p7-10'&&!!officialEntry('test-07')&&
  g.image==='assets/scenes/test-07/pilot-results.jpg'&&g.chartWidthPx===1080||
  g?.testId==='test-08'&&!!officialEntry('test-08')&&(
   g.id==='t08-g059'&&g.image==='assets/scenes/test-08/bench-site-survey-list.jpg'&&g.chartWidthPx===720||
   g.id==='t08-g089'&&g.image==='assets/scenes/test-08/paper-scraps-worktop.jpg'&&g.chartWidthPx===1170||
   g.id==='t08-r-p7-10'&&g.image==='assets/scenes/test-08/film-stock.jpg'&&g.chartWidthPx===1080
  )||
  g?.testId==='test-09'&&g.id==='t09-g077'&&!!officialEntry('test-09')&&
  g.image==='assets/scenes/test-09/glove-sorting-worksheet.jpg'&&g.chartWidthPx===1130;
}
function renderQuizWithChartPosition(){
 const old=app.querySelector('details[data-quiz-chart][open]');
 const position=old?.querySelector('[role="region"]');
 const offsets=position?[position.scrollLeft,position.scrollTop]:null;
 shell(quizPage());
 const current=app.querySelector('details[data-quiz-chart]');
 if(offsets&&current&&current.dataset.quizChart===old.dataset.quizChart){
  current.open=true;
  current.querySelector('[role="region"]')?.scrollTo({left:offsets[0],top:offsets[1],behavior:'instant'});
 }
}
function scopedChartZoom(g,sessionId=''){
 if(!officialReviewedChart(g)||!safeMedia(g.image)||!Number.isInteger(g.chartWidthPx)||g.chartWidthPx<600||g.chartWidthPx>2000)return '';
 return '<details class="chart-full-size"'+(sessionId?' data-quiz-chart="'+esc(sessionId+':'+g.id)+'"':'')+'><summary>View full-size chart</summary><div tabindex="0" role="region" aria-label="Scrollable full-size chart" style="overflow:auto;max-width:100%;"><img src="'+esc(g.image)+'" width="'+g.chartWidthPx+'" alt="" style="display:block;width:'+g.chartWidthPx+'px;max-width:none;height:auto;"></div></details>';
}
const LEGACY_REVIEW_CHARTS=new Map([
  ['t01-g039-r2',['test-01',3,'assets/graphics/62a63cbb0721343a21cc04e1.jpg']],
  ['t01-g049',['test-01',4,'assets/graphics/77133f7d456a3b8d9baee605.jpg']],
  ['t02-g032',['test-02',3,'assets/graphics/a6f0fc305dda092a84b50a90.jpg']],
  ['t02-g049',['test-02',4,'assets/graphics/f3d11a89cde8ed5b9c9def99.jpg']],
  ['t03-g035',['test-03',3,'assets/graphics/072d051478b462600b1216a9.jpg']],
  ['t03-g040-r2',['test-03',3,'assets/graphics/9df87449704f079f6bfd2604.jpg']],
  ['t03-g050',['test-03',4,'assets/graphics/d1a2492e3ff12ddac3266bb5.jpg']]
]);
function legacyReviewChart(g){
 const chart=LEGACY_REVIEW_CHARTS.get(g?.id);
 return !!chart&&g.testId===chart[0]&&g.part===chart[1]&&g.image===chart[2]&&
  !!officialEntry(chart[0])&&typeof g.imageAlt==='string'&&g.imageAlt.trim().length>0;
}
function reviewedChartImage(g){
 const alt=officialReviewedChart(g)||legacyReviewChart(g)?g.imageAlt:'Question illustration';
 return '<img class="scene-img" src="'+esc(g.image)+'" alt="'+esc(alt)+'">'+scopedChartZoom(g);
}
function quizPage(){
const s=state.active,q=questionByActive();if(!s||!q)return '<p>Question not found. Please return to the home page.</p>';const g=sessionGroup(q.groupId,s),qs=groupQuestions(q),last=Math.max(...qs.map(x=>s.questionIds.indexOf(x.id))),answered=Object.keys(s.answers).length,locked=listening(s),ready=groupReady(g);
let out='<div class="quiz-top"><div class="quiz-title">'+esc(displayEnglish(s.title))+'<div class="subtitle-small">'+(formal(s)?(locked?'Formal Mode · Listening: '+listeningDurationLabel(formalPlan(g,s))+' · One play only':'Formal Mode · Reading 75 minutes'):s.mode==='exam'?'Legacy 120 minute self-timed test':'Grouped Practice · Replay allowed')+' · Scored after submission</div></div><div class="btn-row">'+(s.mode==='exam'?'<span class="timer" id="timer">'+(listening(s)&&!s.listeningStartedAt?'Ready to start':timerText(s))+'</span>':'')+(!locked?btn(icon('grid')+' Groups','question-grid','small'):'')+'</div></div><div class="progress-track"><div class="progress-fill" style="width:'+(answered/s.questionIds.length*100)+'%"></div></div><div class="quiz-grid '+(!g?'single':'')+'">';
if(g){out+='<section class="passage-panel"><div class="panel-head"><span>Part '+q.part+' · '+(q.part<5?'Listening Material':'Reading Material')+'</span><span>'+qs.length+' related questions</span></div><div class="panel-body">';if(g.image&&safeMedia(g.image))out+='<div class="scored-graphic" '+(currentFormalStage(g,s)?'hidden':'')+'><img class="scene-img" src="'+esc(g.image)+'" alt="'+esc(displayEnglish(g.imageAlt,'Shared question-group illustration'))+'"><p class="image-caption">'+esc(displayEnglish(g.imageCaption,q.part===1?'Answer based on what you can see in the picture':'Shared illustration or chart'))+'</p>'+scopedChartZoom(g,s.id)+'</div>';out+=q.part<5?formalStageCard(g,s)+audioCard(g)+'<p class="hint">Transcripts, Traditional Chinese translations, and accent labels are available on the answer explanation page after submission.</p>':'<h2 class="passage-title">'+esc(displayEnglish(g.title,'Reading passage'))+'</h2><div class="passage-text">'+esc(g.passage)+'</div>';out+='</div></section>'}
out+='<div class="group-questions" '+(currentFormalStage(g,s)?'hidden':'')+'>'+qs.map(x=>questionCard(x,s)).join('')+'<div class="quiz-footer">'+(!locked?btn(icon('back')+' Previous Group','prev-question','',s.index===0||(formal(s)&&sessionQuestion(s.questionIds[s.index-1],s)?.part<5)?'disabled':''):'<span class="hint">Listening plays in order. You cannot return to an earlier group.</span>')+'<div class="btn-row">'+btn(last===s.questionIds.length-1?'Submit & Score':locked?'Next Group (after playback)':'Next Group '+icon('arrow'),last===s.questionIds.length-1?'finish-session':'next-question','primary',locked&&(!ready||formalRunning)?'disabled':'')+(!locked&&last<s.questionIds.length-1?btn('Submit & Score','finish-session','small'):'')+'</div></div><p class="hint">This group: '+qs.length+' questions · Answered so far: '+answered+' / '+s.questionIds.length+' questions</p></div></div>';return out}

function formalAudioPreparing(running){return Boolean(running&&formalPaused&&formalMedia&&!formalMedia.ready())}
function formalAudioLabel(u,running){
 if(formalAudioPreparing(running))return 'Preparing saved listening position';
 return running&&!formalPaused?'Pause Listening':u?'Resume Listening':'Start Formal Listening';
}
function formalAudioStatus(g,u,running){
 if(u?.status==='ended')return 'This group is complete';
 if(running&&!formalPaused)return 'Playing';
 if(formalAudioPreparing(running))return 'Preparing your saved listening position…';
 if(u)return 'Listening paused. Select Resume Listening to continue.';
 return groupFrames(g).length?'Start listening; subsequent groups play automatically':'This pack has no formal-listening plan. Use Practice mode instead.';
}
function audioCard(g){if(listening()&&route==='quiz'){const u=state.active.audioUsed?.[g.id],available=groupFrames(g).length>0;
 const running=formalRunning&&currentAudioGroup===g.id,complete=u?.status==='ended',label=formalAudioLabel(u,running);
 return '<div class="audio-card formal-audio"><button class="audio-play" data-action="play-audio" data-group="'+g.id+'" aria-label="'+label+'" '+(complete||!available||formalAudioPreparing(running)?'disabled':'')+'>'+icon(running&&!formalPaused?'pause':'play')+'</button><strong id="formal-audio-status">'+formalAudioStatus(g,u,running)+'</strong><p class="hint">Switching tabs pauses the countdown, not the audio. Use Pause Listening to stop the audio temporarily. Completed audio cannot be replayed.</p><span id="audio-time">0:00 / '+time(groupSeconds(g))+'</span></div>'}const has=!!g.audio, saved=route==='quiz'&&state.active?.mode==='practice'&&state.active.practiceMedia?.groupId===g.id&&state.active.practiceMedia.offset>0;return '<div class="audio-card"><div class="audio-head"><button class="audio-play" data-action="play-audio" data-group="'+g.id+'" aria-label="'+(saved&&!currentAudioGroup?'Resume Listening Practice':'Play Listening Audio')+'" '+(!has?'disabled':'')+'>'+icon('play')+'</button><div><div class="audio-title">'+(has?(saved&&!currentAudioGroup?'Resume Listening':'Play This Audio'):'No audio is available for this group')+'</div><div class="audio-sub">'+(has?(Array.isArray(g.audioSpeakers)&&g.audioSpeakers.length?'Neural speech · Listen before choosing your answer':'Listening audio · Listen before choosing your answer'):'Add the audio files to the test-pack folder')+'</div></div></div><input class="audio-slider" id="audio-seek" type="range" min="0" max="1000" value="0" aria-label="Audio playback position"><div class="audio-meta"><span id="audio-time">0:00 / '+time(mediaDuration(g))+'</span><select class="audio-speed" id="audio-speed" aria-label="Playback speed">'+[.75,1,1.25].map(x=>'<option value="'+x+'" '+((saved&&!currentAudioGroup?state.active.practiceMedia.rate:player.playbackRate)===x?'selected':'')+'>'+x+'×</option>').join('')+'</select></div></div>'}
function explanation(q,selected,hasComparableResponse=true){const correct=selected===q.answer;return '<div class="feedback '+(correct?'':'wrong')+'"><h3>'+icon(correct?'check':'info')+' '+(!hasComparableResponse?'Current explanation.':correct?'Correct. Keep going.':'Take another look at the key details.')+' Correct answer '+esc(q.answer)+'</h3><p lang="zh-Hant">'+esc(q.explanationZh)+'</p></div>'+(q.evidence?'<div class="evidence">'+esc(q.evidence)+'</div>':'')+'<div class="rationales"><h4>Why is each option right or wrong?</h4>'+q.options.map(o=>'<div class="rationale"><b>'+o.id+'</b><div lang="zh-Hant">'+esc(o.whyZh)+'</div></div>').join('')+'</div>'+((q.vocabulary||[]).length?'<div class="vocabulary"><h4>'+icon('leaf')+' Vocabulary to take with you</h4>'+q.vocabulary.map(v=>'<div class="word"><strong>'+esc(v.term)+'</strong><div lang="zh-Hant">'+esc(v.zh)+'<small>'+esc(v.note||'')+'</small></div></div>').join('')+'</div>':'')}
function audioAccentNote(g){const labels=ACCENTS;const tags=[...new Set((Array.isArray(g.audioSpeakers)?g.audioSpeakers:[]).map(s=>s?.locale).filter(v=>Object.hasOwn(labels,v)))];return tags.length?'<p class="hint">Accents in this group: '+tags.map(t=>labels[t]).join(', ')+'</p>':''}

function syncAudioUI(){if(route!=='quiz'&&route!=='answer-review')return;const q=route==='answer-review'?Q.get(reviewDetail?.questionId):questionByActive(),g=q&&quizGroup(q.groupId),button=document.querySelector('.audio-play'),seek=document.getElementById('audio-seek'),label=document.getElementById('audio-time');if(!g)return;if(listening()&&route==='quiz'){syncFormalStage(g);const u=state.active.audioUsed?.[g.id];const running=formalRunning&&currentAudioGroup===g.id,status=document.getElementById('formal-audio-status');if(button){
 button.disabled=u?.status==='ended'||!groupFrames(g).length||formalAudioPreparing(running);
 const newLabel=formalAudioLabel(u,running);
 if(button.getAttribute('aria-label')!==newLabel){button.setAttribute('aria-label',newLabel);button.innerHTML=icon(running&&!formalPaused?'pause':'play')}
 }if(status)status.textContent=formalAudioStatus(g,u,running);if(label)label.textContent=time(formalRunning?formalElapsed:savedGroupElapsed(g,u))+' / '+time(groupSeconds(g));const next=document.querySelector('[data-action="next-question"]');if(next)next.disabled=!groupReady(g)||formalRunning;return}const active=currentAudioGroup===g.id, recovered=!active&&route==='quiz'&&state.active?.mode==='practice'&&state.active.practiceMedia?.groupId===g.id?state.active.practiceMedia:null;if(button){const changing=active&&(!player.paused||practicePosition);button.innerHTML=icon(changing?'pause':'play');button.setAttribute('aria-label',changing?'Pause Listening Audio':recovered?.offset>0?'Resume Listening Practice':'Play Listening Audio')}if(seek)seek.value=active&&Number.isFinite(player.duration)&&player.duration?Math.round(Math.max(0,player.currentTime-mediaStart(g))/(Number.isFinite(g.audioEnd)?mediaDuration(g):player.duration)*1000):recovered&&mediaDuration(g)>0?Math.round(1000*recovered.offset/mediaDuration(g)):0;if(label)label.textContent=time(active?Math.max(0,player.currentTime-mediaStart(g)):recovered?.offset||0)+' / '+time(Number.isFinite(g.audioEnd)?mediaDuration(g):active&&Number.isFinite(player.duration)?player.duration:mediaDuration(g))}
// Pausing within a live group keeps its source, cursor, and single-play journal.
function bindFormalMedia(token,finish,ready=()=>true){
 let playEpoch=0,confirmed=false;
 const controls={
  ready,
  confirmed(){return confirmed},
  pause(){playEpoch++;player.pause()},
  play(){
   const epoch=++playEpoch;confirmed=false;
   const current=()=>formalMedia===controls&&token===audioRun&&epoch===playEpoch;
   const failed=e=>{if(current())finish(e)};
   player.playbackRate=1;
   try{Promise.resolve(player.play()).then(()=>{if(current()){confirmed=true;if(player.paused)mediaPaused(token)}},failed)}catch(e){failed(e)}
  },
  clear(){if(formalMedia===controls)formalMedia=null;playEpoch++}
 };
 formalMedia=controls;
 return controls;
}
function mediaPaused(token){
 if(token!==audioRun||!player.paused||player.ended||formalPaused)return;
 // OS or browser media interruptions are not resumed by visibility events.
 formalPaused=true;captureFormal?.();syncAudioUI();
}
function toggleFormalAudio(g){
 if(!g||groupReady(g))return;
 if(!formalRunning||currentAudioGroup!==g.id){void runFormalGroup(g);return}
 if(formalPaused&&formalMedia&&!formalMedia.ready())return;
 captureFormal?.();
 formalPaused=!formalPaused;
 if(formalPaused){formalMedia?.pause();void persist()}
 else formalMedia?.play();
 syncAudioUI();
}
function audioFrame(f,token,offset,progress){
 return new Promise((resolve,reject)=>{
  const start=Number(f.start)||0,end=Number(f.end)||start+Number(f.duration),position=start+offset;
  if(!safeMedia(f.src)||!Number.isFinite(end)||end<=start)return reject(new Error('Invalid formal-audio configuration'));
  if(position>=end-.02)return resolve();
  let timer,settled=false,controls;
  const finish=(error)=>{
   if(settled)return;
   settled=true;clearInterval(timer);controls?.clear();
   for(const [event,handler] of events)player.removeEventListener(event,handler);
   if(token===audioRun)player.pause();
   error?reject(error):resolve();
  };
  const check=()=>{
   if(token!==audioRun)return finish();
   if(player.seeking)return;
   const cursor=player.currentTime;
   if(cursor>=position)progress(cursor-start);
   if(cursor>=end-.025)finish();
  };
  captureFormal=()=>{if(!player.seeking&&player.currentTime>=position)progress(player.currentTime-start)};
  const ended=()=>player.currentTime>=end-.15?finish():finish(new Error('Audio ended before the planned position'));
  const failed=()=>finish(new Error('Unable to load the audio file'));
  const paused=()=>{check();if(!settled)mediaPaused(token)};
  const events=[['error',failed],['ended',ended],['pause',paused],['timeupdate',check]];
  try{
   if(player.getAttribute('src')!==f.src||player.error){player.src=f.src;player.load()}
   player.playbackRate=1;player.currentTime=position;
   for(const [event,handler] of events)player.addEventListener(event,handler);
   timer=setInterval(check,25);
   controls=bindFormalMedia(token,finish);
   if(!formalPaused)controls.play();
  }catch(e){finish(e)}
 });
}
// One file includes directions, speech and exact answer silence. The native clock drives
// chapters/UI/journal; a chapter transition never restarts media or uses currentTime=.
function playContinuousGroup(m,token,position,isResume,progress,trustedBuiltIn=false){
 return new Promise((resolve,reject)=>{
  const epsilon=.05;
  let timer,seekTimeout,settled=false,metadata=false,controls;
  let seekPending=isResume&&position>0,seekRequested=false,observedPlayback=false;
  const sourceUrl=new URL(m.src,document.baseURI).href;
  const selected=()=>player.currentSrc===sourceUrl;
  const finish=error=>{
   if(settled)return;
   settled=true;clearInterval(timer);clearTimeout(seekTimeout);controls?.clear();
   for(const [event,handler] of events)player.removeEventListener(event,handler);
   error?reject(error):resolve();
  };
  const validDuration=()=>Number.isFinite(player.duration)&&Math.abs(player.duration-m.duration)<=epsilon;
  const check=()=>{
   if(token!==audioRun)return finish();
   if(settled||!metadata||!selected()||player.seeking||seekPending)return;
   if(player.currentTime<position-.025)return;
   if(trustedBuiltIn&&player.currentTime>m.duration+epsilon)
    return finish(new Error('Continuous group playback exceeded the planned duration'));
   if(!player.paused&&player.currentTime>position+.0001)observedPlayback=true;
   // Never journal completion until the browser dispatches verified EOS.
   progress(Math.min(m.duration-.001,player.currentTime));
  };
  const loaded=()=>{
   if(token!==audioRun)return finish();
   if(!selected())return;
   // Some WebKit versions report an estimated Ogg duration based on early
   // packets. Only exact built-in group URLs use plan + actual cursor/EOS.
   if(!trustedBuiltIn&&!validDuration())return finish(new Error('Unexpected continuous group audio duration'));
   metadata=true;
   if(seekPending&&!seekRequested){
    seekRequested=true;
    try{player.currentTime=position}catch(_){
     return finish(new Error('Unable to resume at the saved audio position'));
    }
   }
   check();
  };
  const ended=()=>{
   if(!selected()||!metadata||settled||!player.ended||(!observedPlayback&&!controls?.confirmed()))return;
   check();if(settled)return;
   if(token!==audioRun)return finish();
   if(seekPending)return finish(new Error('Unable to resume at the saved audio position'));
   if((!trustedBuiltIn&&!validDuration())||player.currentTime<m.duration-epsilon)return finish(new Error('Continuous group audio ended early'));
   if(player.currentTime>m.duration+epsilon)return finish(new Error('Continuous group playback exceeded the planned duration'));
   progress(m.duration);finish();
  };
  const paused=()=>{
   check();
   // Ignore unload/reset notifications before the current play actually
   // starts; an active play rejection still reports its real failure.
   if(!settled&&selected()&&controls?.confirmed())mediaPaused(token);
  };
  const failed=()=>{if(player.error)finish(new Error('Unable to load the continuous audio file'))};
  const seeked=()=>{
   if(seekPending&&seekRequested&&metadata&&selected()&&!player.seeking&&Math.abs(player.currentTime-position)<=.025){
    seekPending=false;clearTimeout(seekTimeout);syncAudioUI();
    // Playback is never initiated here; a fresh tap supplies activation.
   }
   check();
  };
  const events=[['loadedmetadata',loaded],['error',failed],['ended',ended],['pause',paused],['timeupdate',check],['seeked',seeked]];
  try{
   for(const [event,handler] of events)player.addEventListener(event,handler);
   // Assigning src starts native resource selection. A second explicit
   // load can abort pending startup; keep play in the initiating gesture.
   player.src=m.src;player.playbackRate=1;
   // Fresh playback can begin in this gesture. For restored offsets,
   // first confirm the position without ever playing from zero. Request
   // native metadata during this tap; no playback is pending in this branch.
   if(seekPending)player.load();
   // Some in-memory/cached element implementations already know metadata.
   if(player.readyState>=1&&selected())loaded();
   if(settled)return;
   captureFormal=check;controls=bindFormalMedia(token,finish,()=>!seekPending);
   timer=setInterval(check,25);
   if(seekPending){
    formalPaused=true;syncAudioUI();
    seekTimeout=setTimeout(()=>finish(new Error('Unable to resume at the saved audio position')),10000);
   }else if(!formalPaused)controls.play();
  }catch(e){finish(e)}
 });
}
async function runFormalGroup(g,{prepareOnly=false}={}){
 const s=state.active;
 if(!g||!listening(s)||route!=='quiz'||formalRunning||questionByActive()?.groupId!==g.id||formalClockExpired(s))return;
 const frames=groupFrames(g),prior=s.audioUsed?.[g.id],continuous=continuousGroupAudio(g,s);
 if((continuous||frames.some(f=>opusRequired(f.src)))&&!opusPlayable()){notify(opusUnavailable);return;}
 if(prior?.status==='ended'||!frames.length||prepareOnly&&(!continuous||!prior||!(savedGroupElapsed(g,prior)>0)))return;
 stopAudio(Boolean(continuous));
 // Restored continuous audio is prepared silently, before enabling the user's play gesture.
 formalPaused=prepareOnly;
 const token=audioRun,{frame,offset}=resumePosition(prior,frames);
 let elapsed=frames.slice(0,frame).reduce((sum,f)=>sum+(Number(f.duration)||0),0),savedAt=now();
 const u=s.audioUsed[g.id]={status:'started',unlockAt:0,frame,offset};
 currentAudioGroup=g.id;formalRunning=true;formalRole=frames[frame]?.role||'';formalElapsed=elapsed+offset;
 if(!s.listeningStartedAt)s.listeningStartedAt=now();
 syncListeningCountdown(s);void persist();render();
 try{
  if(continuous){
   const starts=[0];for(const f of frames)starts.push(starts[starts.length-1]+f.duration);
   const position=elapsed+offset;
   const progress=cursor=>{
    if(token!==audioRun)return;
    const at=Math.max(formalElapsed,Math.min(continuous.duration,cursor));
    let i=Math.min(u.frame,frames.length-1);
    while(i+1<frames.length&&at>=starts[i+1])i++;
    u.frame=i;u.offset=Math.max(0,Math.min(frames[i].duration,at-starts[i]));
    formalElapsed=at;
    if(formalRole!==frames[i].role){formalRole=frames[i].role;syncFormalStage(g);}
    if(now()-savedAt>=2000){savedAt=now();void persist()}
   };
   if(position>=continuous.duration-.000001)throw new Error('Unable to resume at the saved audio position');
   await playContinuousGroup(continuous,token,position,!!prior,progress,
     Boolean(officialEntry(g.testId))&&continuous.src===`audio/formal-groups/${g.testId}/${g.id}.ogg`);
   if(token!==audioRun)return;
   captureFormal=null;formalElapsed=continuous.duration;u.frame=frames.length;u.offset=0;
  }else for(let i=frame;i<frames.length;i++){
   if(token!==audioRun)return;
   const f=frames[i],duration=Number(f.duration),from=i===frame?offset:0;
   u.frame=i;u.offset=from;formalRole=f.role;syncFormalStage(g);
   const progress=pos=>{
    if(token!==audioRun)return;
    u.offset=Math.max(u.offset,Math.min(duration,pos));
    formalElapsed=elapsed+u.offset;
    if(now()-savedAt>=2000){savedAt=now();void persist()}
   };
   if(f.kind==='silence'){
    let tick=performance.now();
    captureFormal=()=>{
     const next=performance.now(),dt=next-tick;tick=next;
     if(!formalPaused)progress(u.offset+dt/1000);
    };
    await new Promise(resolve=>{const t=setInterval(()=>{
     if(token===audioRun)captureFormal?.();
     if(token!==audioRun||u.offset>=duration){clearInterval(t);resolve()}
    },50)});
   }else{
    captureFormal=null;
    await audioFrame(f,token,from,progress);
   }
   if(token!==audioRun)return;
   captureFormal=null;elapsed+=duration;formalElapsed=elapsed;u.frame=i+1;u.offset=0;
  }
  formalRunning=false;u.status='ended';await persist();
  if(route==='quiz'&&state.active===s&&token===audioRun){
   await moveGroup(1,true);
   const next=sessionGroup(questionByActive()?.groupId,s);
   if(listening(s)&&route==='quiz'&&next)void runFormalGroup(next);
  }
 }catch(e){
  if(token!==audioRun)return;
  stopAudio();
  void persist();render();
  if(!document.hidden){
   const detail=e?.name==='NotAllowedError'?'Playback was blocked by the browser.':e?.name==='NotSupportedError'?'The browser could not play this audio format.':e?.name==='AbortError'?'Playback was interrupted before it could start.':e?.message==='Unexpected continuous group audio duration'?'The browser reported an unexpected audio duration.':e?.message==='Unable to load the continuous audio file'?'The browser could not load the audio file.':e?.message==='Continuous group audio ended early'?'The audio ended before the group was complete.':e?.message==='Continuous group playback exceeded the planned duration'?'Audio exceeded the expected group duration.':e?.message==='Unable to resume at the saved audio position'?'The browser could not verify the saved listening position.':'Listening was paused or interrupted.';
   notify(detail+' Select Resume Listening to try again.');
  }
 }
}
const PRACTICE_SEEK_EPS=.014, PRACTICE_UNDERSHOOT=.004;
let practicePosition=null,practiceRangeTimer=null;
function standalonePractice(g){
 return !!g&&g.audio===`audio/practice-groups/${g.testId}/${g.id}.ogg`&&safeMedia(g.audio)&&
  g.audioStart===0&&Number.isFinite(g.duration)&&g.duration>0&&g.audioEnd===g.duration;
}
function practiceSrc(g){
 if(standalonePractice(g))return g.audio;
 const start=mediaStart(g),end=g.audioEnd;
 return g.audio+(Number.isFinite(end)&&end>start?'#t='+start+','+end:'');
}
function cancelPracticePosition(){
 const p=practicePosition;
 practicePosition=null;
 p?.cancel();
}
function beginPracticePosition(g,target,playAfter){
 const playerSrc=practiceSrc(g),start=mediaStart(g),end=g.audioEnd;
 const token=audioRun,id=g.id;
 const current=()=>token===audioRun&&currentAudioGroup===id&&player.getAttribute('src')===playerSrc;
 const atTarget=()=>player.readyState>=2&&!player.seeking&&player.currentTime>=target-PRACTICE_UNDERSHOOT&&player.currentTime<=target+PRACTICE_SEEK_EPS&&player.currentTime>=start-PRACTICE_UNDERSHOOT;
 const change=player.getAttribute('src')!==playerSrc||player.error;
 if(!change&&atTarget()){
  if(playAfter)Promise.resolve(player.play()).catch(()=>{if(current())notify('Audio cannot play. Select Play again.')});
  return;
 }
 const originalMute=player.muted;let finished=false,timer;
 const state={cancel:()=>finish('cancel')};
 stopPracticeRangeTimer();practicePosition=state;
 function finish(kind){
  if(finished)return;finished=true;
  clearTimeout(timer);
  for(const [e,fn] of listeners)player.removeEventListener(e,fn);
  if(practicePosition===state)practicePosition=null;
  // Stop first: cancellation or failure must not unmute a stale decoded range.
  if(kind!=='ready')player.pause();
  if(kind==='fail'&&current()&&player.readyState>=1){
   try{player.currentTime=target}catch(e){}
  }
  player.muted=originalMute;
  if(kind==='ready')startPracticeRangeTimer();
  if(kind==='fail'&&current())notify('Audio position was not confirmed. Select Play again to start from this question.');
  if(kind!=='cancel')syncAudioUI();
 }
 function verify(){
  if(!current()||finished||player.seeking||player.readyState<2)return;
  if(atTarget()){finish('ready');return}
  // A playing cursor that already moved past the request is not a safe start.
  if(!player.paused&&player.currentTime>target+PRACTICE_SEEK_EPS)finish('fail');
 }
 function onMetadata(){
  if(!current()||finished)return;
  if(!atTarget()&&!player.seeking){try{player.currentTime=target}catch(e){finish('fail');return}}
  verify();
 }
 const onError=()=>{if(current())finish('fail')};
 const listeners=[['loadedmetadata',onMetadata],['seeked',verify],['loadeddata',verify],['canplay',verify],['playing',verify],['error',onError]];
 try{
  player.muted=true;
  if(change){player.pause();player.src=playerSrc;player.load()}
  for(const [e,fn] of listeners)player.addEventListener(e,fn);
  // Set a default early; loadedmetadata repeats it if the browser discarded it.
  try{player.currentTime=target}catch(e){if(player.readyState>=1)throw e}
  timer=setTimeout(()=>finish('fail'),7000);
  // Invoke native play in the user's gesture, but keep it silent until verified.
  if(playAfter)Promise.resolve(player.play()).then(verify,()=>{if(current())finish('fail')});
  verify();
 }catch(e){finish('fail')}
}
function playStandalonePractice(g){
 const token=audioRun,src=g.audio,group=g.id;
 const current=()=>token===audioRun&&currentAudioGroup===group&&player.getAttribute('src')===src;
 const failed=()=>{if(current())notify('Audio cannot play. Select Play again.')};
 try{
  if(!current()||player.ended||player.error||player.currentTime>=g.duration){
   player.pause();
   player.src=src;player.load();
  }
  // A different or completed native file begins at zero without an explicit seek.
  // A user pause or scrub within the same file retains that intentional position.
  Promise.resolve(player.play()).catch(failed);
 }catch(e){failed()}
 syncAudioUI();
}
async function playAudio(groupId){
 const g=quizGroup(groupId);
 if(listening()&&route==='quiz'){toggleFormalAudio(g);return}
 if(!g?.audio){notify('No audio is available for this question.');return}
 if(opusRequired(g.audio)&&!opusPlayable()){notify(opusUnavailable);return}
 if(practicePosition){cancelPracticePosition();syncAudioUI();return}
 if(currentAudioGroup===groupId&&!player.paused){player.pause();syncAudioUI();return}
 const changed=currentAudioGroup!==groupId||player.getAttribute('src')!==practiceSrc(g);
 if(changed){
  player.pause();currentAudioGroup=groupId;
  const saved=route==='quiz'&&state.active?.mode==='practice'?state.active.practiceMedia:null;
  if(saved?.groupId===groupId){
   player.playbackRate=saved.rate;
   const start=mediaStart(g),lim=Number.isFinite(g.audioEnd)?g.audioEnd:start+(Number(g.duration)||0);
   if(saved.offset>0&&lim>start&&saved.offset<lim-start-.035){beginPracticePosition(g,start+saved.offset,true);syncAudioUI();return}
  }
 }
 if(standalonePractice(g)){playStandalonePractice(g);return}
 const start=mediaStart(g),end=g.audioEnd;
 const target=changed||player.currentTime<start||Number.isFinite(end)&&player.currentTime>=end-.035?start:player.currentTime;
 beginPracticePosition(g,target,true);
 syncAudioUI();
}
function scrubPractice(g,value){
 if(!g?.audio||currentAudioGroup!==g.id||!Number.isFinite(player.duration))return;
 const start=mediaStart(g),limit=Number.isFinite(g.audioEnd)?g.audioEnd:player.duration;
 const target=Math.min(Math.max(start,limit-.035),start+Math.min(1,Math.max(0,value/1000))*Math.max(0,limit-start));
 const playing=!player.paused;
 cancelPracticePosition();
 beginPracticePosition(g,target,playing);
 syncAudioUI();
}
let lastPracticeMediaSave=0;
function savePracticeMedia(force=false){
 const s=state.active;if(diagnostic||route!=='quiz'||s?.mode!=='practice'||!currentAudioGroup||player.readyState<1||player.seeking||practicePosition)return false;
 const q=questionByActive(),g=q?.groupId===currentAudioGroup?quizGroup(currentAudioGroup):null;
 if(!g?.audio||player.getAttribute('src')!==practiceSrc(g))return false;
 const at=now();if(!force&&at-lastPracticeMediaSave<2000)return false;
 const rate=[.75,1,1.25].includes(player.playbackRate)?player.playbackRate:1;
 const offset=player.ended?0:Math.min(86400,Math.max(0,player.currentTime-mediaStart(g)));
 const next={groupId:g.id,offset,rate,paused:player.paused||player.ended};
 if(s.practiceMedia&&s.practiceMedia.groupId===next.groupId&&Math.abs(s.practiceMedia.offset-next.offset)<.05&&
    s.practiceMedia.rate===next.rate&&s.practiceMedia.paused===next.paused)return false;
 s.practiceMedia=next;lastPracticeMediaSave=at;return true
}
function practiceRangeGroup(){
 if(formalRunning||listening()&&route==='quiz'||practicePosition||!currentAudioGroup||player.paused||player.ended)return null;
 const g=quizGroup(currentAudioGroup);
 return g?.audio&&!standalonePractice(g)?g:null;
}
function stopPracticeRangeTimer(){
 if(practiceRangeTimer!==null){clearInterval(practiceRangeTimer);practiceRangeTimer=null}
}
function startPracticeRangeTimer(){
 if(practiceRangeTimer===null&&practiceRangeGroup())practiceRangeTimer=setInterval(checkPracticeRange,15);
}
function checkPracticeRange(){
 const g=practiceRangeGroup();
 if(!g){stopPracticeRangeTimer();return}
 const at=player.currentTime, start=mediaStart(g), end=g.audioEnd;
 if(at<start-PRACTICE_UNDERSHOOT||Number.isFinite(end)&&at>=end-.025){
  stopPracticeRangeTimer();player.pause();try{player.currentTime=start}catch(e){}syncAudioUI();
 }
}

async function moveGroup(delta,automatic=false){const s=state.active,q=questionByActive();if(!s||!q)return;const qs=groupQuestions(q),indices=qs.map(x=>s.questionIds.indexOf(x.id)),start=Math.min(...indices),end=Math.max(...indices);if(listening(s)&&(delta<0||!groupReady(sessionGroup(q.groupId,s))||formalRunning))return;let target=delta>0?end+1:start-1;if(target<0||target>=s.questionIds.length){if(automatic&&listening(s)&&delta>0)beginFormalExpiry(s);return}if(formal(s)&&s.examPhase==='reading'&&sessionQuestion(s.questionIds[target],s)?.part<5)return;if(listening(s)&&sessionQuestion(s.questionIds[target],s)?.part>=5){beginFormalExpiry(s);return;}stopAudio();s.index=target;const targetQ=questionByActive();s.index=s.questionIds.indexOf(groupQuestions(targetQ)[0].id);activeTranscript=null;await persist();render();window.scrollTo({top:0,behavior:'instant'})}
function moveQuestion(delta){return moveGroup(delta)}

async function submitAnswer(){if(!state.active)return;if(state.active.index===state.active.questionIds.length-1)return finishSession();moveQuestion(1)}
async function finishSession(force=false){
if(diagnostic){notify('This session is only for playback diagnostics. Nothing was saved.');return}
const s=state.active;if(!s||guestSubmitPending||guestBackupApplying||(force&&guestRejectedAutoSubmit===s))return;
if(accountActiveConflict){notify(accountActiveWarning);return}const done=Object.keys(s.answers).length;
const complete=async()=>{
 if(state.active!==s||guestSubmitPending)return;
 stopAudio();
 const original=state;
 // Keep the quiz and score/history untouched until its durable save succeeds.
 const owner=syncOwner;
 const target={...original,attempts:original.attempts.slice(),sessions:original.sessions.slice(),stats:JSON.parse(JSON.stringify(original.stats))};
 const submitted={...s.submitted};
 for(const id of s.questionIds){
  const q=sessionQuestion(id,s);
  if(q){recordAnswer(q,s.answers[id]||null,s.id,0,target);submitted[id]=true}
 }
 const outcomes=sessionOutcomes(s,target);
 const result={id:s.id,title:s.title,mode:s.mode,questionIds:s.questionIds,answers:s.answers,submitted,startedAt:s.startedAt,finishedAt:now(),correct:s.questionIds.filter(id=>outcomes.get(id)===true).length,answered:done,total:s.questionIds.length};
 target.sessions.push(result);
 target.active=null;
 guestSubmitPending=true;
 let accepted;
 try{accepted=await persist(false,false,null,target)}finally{guestSubmitPending=false}
 if(state!==original||syncOwner!==owner)return;
 if(accepted===false){guestRejectedAutoSubmit=s;return}
 Object.assign(original,{attempts:target.attempts,sessions:target.sessions,stats:target.stats,active:null});
 if(owner)scheduleCheckpoint();
 lastResult=result;resumeEnv=null;
 route='result';render();if(syncOwner)void startSync();window.scrollTo({top:0,behavior:'instant'})
};
if(!force&&done<s.questionIds.length)confirmBox('Submit and score this session?','There are '+(s.questionIds.length-done)+' unanswered questions. Unanswered items count as incorrect. Your score and explanations appear after submission.',complete,'Confirm Submission');else await complete()}
function questionGrid(){const s=state.active;if(!s||listening(s))return;const units=new Map();s.questionIds.forEach((id,i)=>{const q=sessionQuestion(id,s);if(!q||(formal(s)&&q.part<5))return;const key=q.groupId||id;if(!units.has(key))units.set(key,{index:i,qs:[]});units.get(key).qs.push(q)});modal('<h2>Group Navigator</h2><p>Each tile is a complete group. Green means every question is answered. The count shows answered / total questions.</p><div class="navigator group-navigator">'+[...units.values()].map(u=>{const done=u.qs.filter(q=>s.answers[q.id]).length;return '<button class="nav-q '+(done===u.qs.length?'answered':'')+' '+(u.qs.some(q=>q.id===s.questionIds[s.index])?'current':'')+'" data-action="jump" data-index="'+u.index+'">Q'+u.qs[0].number+(u.qs.length>1?'–'+u.qs.at(-1).number:'')+'<small>'+done+' / '+u.qs.length+'</small></button>'}).join('')+'</div><div class="btn-row">'+btn('Return to Practice','close-modal')+btn('Submit & Score','finish-from-modal','primary')+'</div>')}
function matchesListSearch(id){const q=Q.get(id);if(!q)return false;const term=listSearch.trim().toLowerCase();return !term||[q.prompt,q.promptZh,state.notes[id]||'',id,window.SHIFT_QUESTION_UUID(id),...(Array.isArray(q.tags)?q.tags:[])].join(' ').toLowerCase().includes(term)}
function sessionOutcomes(result,workspace=state){const outcomes=new Map(),prefix=result.id+':';for(const a of workspace.attempts)if(a.id===prefix+a.questionId)outcomes.set(a.questionId,a.correct);return outcomes}
function firstSessionAttempts(r){
 const first=new Map(),prefix=r.id+':';
 for(const a of state.attempts){
  if(typeof a.id!=='string'||!a.id.startsWith(prefix))continue;
  const id=a.id.slice(prefix.length);
  if(!first.has(id))first.set(id,a);
 }
 return first
}
function estimatedSections(r,first=firstSessionAttempts(r)){
if(r.mode!=='exam'||r.total!==200||r.questionIds.length!==200||new Set(r.questionIds).size!==200)return null;
const attempts=r.questionIds.map(id=>first.get(id));
if(attempts.some(a=>!a||!Number.isInteger(a.part)||a.part<1||a.part>7))return null;
const listening=attempts.filter(a=>a.part<5),reading=attempts.filter(a=>a.part>=5);
if(listening.length!==100||reading.length!==100)return null;
const rawL=listening.filter(a=>a.correct).length,rawR=reading.filter(a=>a.correct).length;
const scale=n=>5*Math.round((5+490*n/100)/5);
return {rawL,rawR,listening:scale(rawL),reading:scale(rawR),total:scale(rawL)+scale(rawR)};
}
function estimatedScoreCard(r,first){const s=estimatedSections(r,first);if(!s)return '';return '<section class="panel score-estimate" style="margin:20px 0"><h2>Unofficial linear score estimate</h2><p><strong>Listening '+s.listening+' / 495 · Reading '+s.reading+' / 495 · Total '+s.total+' / 990</strong></p><p>Raw correct answers: Listening '+s.rawL+' / 100; Reading '+s.rawR+' / 100. Unanswered items count as incorrect.</p><p class="hint">This is NOT an ETS score, official conversion, or prediction of an actual test result. Each section is estimated as 5 + 490 × (raw correct / 100), rounded to the nearest 5 points, from 5 to 495. ETS uses form-specific equating; its conversion tables are not public. This simple linear practice estimate does not reproduce that process.</p><a href="https://www.ets.org/pdfs/toeic/toeic-listening-reading-test-examinee-handbook.pdf" target="_blank" rel="noopener">ETS examinee handbook: scoring and equating</a></section>'}
function resultPage(){
const r=lastResult||state.sessions.at(-1);if(!r)return '<div class="empty"><h2>No completed sessions yet</h2>'+btn('Start Practicing','nav-practice','primary')+'</div>';
const first=firstSessionAttempts(r),outcomes=sessionOutcomes(r),wrong=r.questionIds.filter(id=>outcomes.get(id)===false),score=Math.round(r.correct/r.total*100);
let out='<section class="panel"><div class="result-header">'+icon('leaf')+'<p class="eyebrow">YOUR RESULTS</p><h1>Session complete. See what you learned.</h1><p>'+esc(displayEnglish(r.title))+' · '+new Date(r.finishedAt).toLocaleString('en-US')+'</p></div><div class="summary-grid"><div class="result-stat"><b>'+score+'<small style="font-size:.875rem"> points</small></b><span>Session score (out of 100)</span></div><div class="result-stat"><b>'+r.correct+'<small style="font-size:.875rem"> / '+r.total+'</small></b><span>Correct answers</span></div><div class="result-stat"><b>'+wrong.length+'<small style="font-size:.875rem"> questions</small></b><span>Questions to revisit</span></div></div><p class="hint" style="text-align:center">Score = Correct answers ÷ Total questions × 100.Unanswered items count as incorrect. This is not an official TOEIC scaled score.</p><div class="btn-row" style="justify-content:center;margin:23px 0">'+btn('Practice These Mistakes Again','review-result','primary',wrong.some(id=>Q.has(id))?'':'disabled')+btn('Back to Home','nav-home')+'</div></section><div class="section-heading"><h2>All Answers in This Session</h2><span>Review correct, incorrect, and unanswered questions after submission.</span></div>';
out+=estimatedScoreCard(r,first);
out+='<div class="record-list">'+r.questionIds.map(id=>{const q=Q.get(id),a=first.get(id);if(!q){const savedSelection=a?.selected??r.answers[id]??null;const savedKey=a?.correctAnswer;const savedOutcome=outcomes.get(id);const badge=typeof savedOutcome==='boolean'?(savedOutcome?'Correct':'Incorrect'):'Not recorded';return '<article class="record-card"><div class="record-title"><div class="badge-row"><span class="tag gray">Previous question version</span><span class="tag orange">'+esc(badge)+'</span></div><h3>'+esc(id)+'</h3>'+questionReference(id)+'<p>Your answer: '+esc(savedSelection||'Unanswered')+(savedKey?' · Original correct answer: '+esc(savedKey):'')+'</p><p class="hint">The old question content is no longer available. Your original result is unchanged.</p></div></article>';}return '<article class="record-card"><div class="record-title"><div class="badge-row"><span class="tag">Part '+q.part+'</span><span class="tag gray">'+esc(TOPICS[q.topic])+'</span><span class="tag orange">'+(a?.selected?(a.correct?'Correct · ':'Incorrect · ')+'Your answer '+esc(a.selected):'Unanswered')+'</span></div><h3>'+esc(q.prompt)+'</h3>'+questionReference(id)+'</div>'+btn('View Explanation '+icon('arrow'),'view-explanation','small','data-id="'+id+'" data-session="'+r.id+'" '+(!a?'disabled':''))+'</article>'}).join('')+'</div>';return out}
function explanationQueue(id,sessionId){
 const attempts=new Map();
 let ids,returnTo;
 if(sessionId){
  const completed=state.sessions.find(s=>s.id===sessionId&&s.questionIds.includes(id));
  if(!completed)return null;
  ids=completed.questionIds;returnTo='result';
  const prefix=completed.id+':';
  for(const a of state.attempts)if(a.id===prefix+a.questionId)attempts.set(a.questionId,a);
 }else{
  ids=reviewListIds();returnTo='review';
  for(const a of state.attempts)if(!a.correct&&(!attempts.has(a.questionId)||attempts.get(a.questionId).at<=a.at))attempts.set(a.questionId,a);
 }
 const entries=ids.filter(qid=>Q.has(qid)&&attempts.has(qid)).map(qid=>({questionId:qid,attempt:attempts.get(qid)}));
 const index=entries.findIndex(e=>e.questionId===id);
 return index===-1?null:{...entries[index],entries,index,returnTo,origin:{questionId:id,sessionId:sessionId||''}};
}
function openExplanation(detail){
 stopAudio();
 reviewDetail=detail;route='answer-review';render();
 document.getElementById('review-heading')?.focus({preventScroll:true});
 window.scrollTo(0,0);
}
function focusReviewOrigin(detail){
 const origin=detail?.origin;
 const control=origin&&Array.from(document.querySelectorAll('#main button[data-action="view-explanation"]:not(:disabled)')).find(b=>
  b.dataset.id===origin.questionId&&(b.dataset.session||'')===origin.sessionId);
 if(control){control.focus();return}
 const heading=document.querySelector('#main h1, #main h2')||document.getElementById('main');
 if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true})}
 window.scrollTo(0,0);
}
function reviewAdvance(d){
 if(d.index+1===d.entries.length)return '<p class="hint">This is the last question in this list.</p>';
 return btn((d.returnTo==='review'?'Next Incorrect Question ':'Next Question ')+icon('arrow'),'next-explanation','primary');
}
function reviewPassageMarkup(g){
 const filled=g.part===6&&typeof g.reviewPassage==='string'&&!!g.reviewPassage.trim()&&typeof g.reviewPassageZh==='string'&&!!g.reviewPassageZh.trim();
 return '<div class="passage-scroll"><div class="passage-text">'+esc(filled?g.reviewPassage:g.passage)+'</div><div class="passage-text zh" lang="zh-Hant">'+esc(filled?g.reviewPassageZh:g.passageZh)+'</div></div>';
}
function reviewedAnswerMarkup(q,attempt){
 const letter=x=>typeof x==='string'&&/^[A-D]$/.test(x)?x:null;
 const stored=letter(attempt?.selected),original=letter(attempt?.correctAnswer);
 const versionMatches=!!attempt&&attempt.revision===(q.revision||1);
 const selectedOption=versionMatches?q.options.find(o=>o.id===stored):null;
 const selection=stored?esc(stored)+(selectedOption?' · '+esc(selectedOption.text):''):(attempt?.selected===null?'Unanswered':'Not recorded');
 const key=versionMatches||original===q.answer?esc(q.answer):(original?esc(original):'Not recorded');
 const verdict=attempt?.selected===null?'Unanswered':typeof attempt?.correct==='boolean'?(attempt.correct?'Correct':'Incorrect'):'';
 const mark=(label,cls)=>'<span class="tag '+cls+'">'+esc(label)+'</span>';
 const summary='<section class="notice" aria-label="Recorded answer" data-review-selection><p><strong>Your answer:</strong> '+selection+(verdict?' '+mark(verdict,attempt?.correct?'':'orange'):'')+'</p><p><strong>'+(versionMatches?'Correct answer:':'Correct answer at the time:')+'</strong> '+key+'</p></section>';
 const options=q.options.map(o=>{
  const correct=o.id===q.answer,chosen=versionMatches&&o.id===stored;
  return '<div class="option '+(correct?'correct':chosen?'wrong':'')+'"><span class="option-letter">'+esc(o.id)+'</span><span class="option-text">'+esc(o.text)+'<span class="option-zh" lang="zh-Hant">'+esc(o.zh)+'</span>'+((chosen||correct)?'<span class="badge-row">'+(chosen?mark('Your answer',correct?'':'orange'):'')+(correct?mark(versionMatches?'Correct answer':'Current correct answer',''):'')+'</span>':'')+'</span>'+(correct?'<span class="option-check" aria-hidden="true">'+icon('check')+'</span>':'')+'</div>';
 }).join('');
 return {summary,options,selectionKnown:versionMatches,selected:versionMatches?stored:null};
}
function reviewDetailPage(){
const d=reviewDetail,q=d&&Q.get(d.questionId);if(!q)return '<div class="empty"><h2>This question is unavailable</h2>'+btn('Back to Review List','nav-review','primary')+'</div>';const g=G.get(q.groupId),a=d.attempt,reviewed=reviewedAnswerMarkup(q,a);
let out='<div class="quiz-top"><div><p class="eyebrow">REVIEW AFTER SUBMISSION</p><h1 id="review-heading" class="page-title" tabindex="-1" style="font-size:1.5rem">Understand this question.</h1><p class="subtitle-small">Part '+q.part+' · '+PARTS[q.part]+' · Q'+q.number +'</p></div>'+btn(icon('back')+' Back to Results / Review','back-review','small')+'</div><div class="quiz-grid '+(!g?'single':'')+'">';
if(g){out+='<section class="passage-panel"><div class="panel-head"><span>'+icon(q.part<5?'headphones':'book')+' '+(q.part<5?'Audio & Transcript':'Original Text & Translation')+'</span></div><div class="panel-body">';if(g.image&&safeMedia(g.image))out+=reviewedChartImage(g);if(q.part<5)out+=audioCard(g)+audioAccentNote(g);else out+='<h2 class="passage-title">'+esc(displayEnglish(g.title,'Reading passage'))+'</h2>';out+=reviewPassageMarkup(g)+'</div></section>'}
out+='<section class="question-panel"><div class="panel-head"><span>Correct answer '+esc(q.answer)+'</span><button class="icon-button '+(state.stars[q.id]?'starred':'')+'" data-action="star" data-id="'+q.id+'" aria-label="'+(state.stars[q.id]?'Unsave question':'Save question')+'">'+icon('star')+'</button></div><div class="panel-body">'+questionReference(q.id)+(a&&!reviewed.selectionKnown?'<div class="notice">The saved option letter belongs to an older or unconfirmed question version. The current choices may differ. Your original score is unchanged.</div>':'')+'<h2 class="question-text">'+esc(q.prompt)+'</h2><p class="translation" lang="zh-Hant">'+esc(q.promptZh)+'</p><div class="options">'+reviewed.options+'</div>'+reviewed.summary+explanation(q,reviewed.selected,reviewed.selectionKnown)+'<details class="note-box" open><summary>'+icon('note')+' My Notes</summary><textarea id="question-note" data-id="'+q.id+'" maxlength="20000" placeholder="Write down what you learned from this question…" aria-label="Question notes">'+esc(state.notes[q.id]||'')+'</textarea><div class="word-count" id="note-save-status">'+esc(noteStatusText(q.id))+'</div></details><div class="btn-row" style="margin-top:20px">'+reviewAdvance(d)+btn('Try This Group Again','open-question','','data-id="'+q.id+'"')+btn('Back to Results / Review','back-review')+'</div></div></section></div>';return out}
function reviewListIds(review=true){
 const cutoff=now();
 const ids=review?Object.keys(state.stats).filter(id=>listFilter==='history'?state.stats[id].wrong>0:state.stats[id].needsReview&&(listFilter!=='due'||state.stats[id].due<=cutoff)):Object.keys(state.stars).filter(id=>state.stars[id]);
 return ids.filter(matchesListSearch).sort((a,b)=>(state.stats[b]?.lastAt||0)-(state.stats[a]?.lastAt||0));
}
function listPage(){const review=route==='review',ids=reviewListIds(review);let out=heading(review?'Make unfamiliar questions familiar.':'Keep questions worth revisiting.',review?'Incorrect answers are added automatically. Two consecutive correct attempts remove a question from the review queue.':'Your saved questions, notes, and topics to revisit.',review?'REVIEW & REMEMBER':'YOUR SAVED QUESTIONS');out+='<div class="list-toolbar"><div class="btn-row"><input id="list-search" placeholder="Search questions, UUIDs or notes" aria-label="Search questions" value="'+esc(listSearch)+'">'+(review?'<select id="review-filter" aria-label="Review filter"><option value="all" '+(listFilter==='all'?'selected':'')+'>Questions to review</option><option value="due" '+(listFilter==='due'?'selected':'')+'>Due today</option><option value="history" '+(listFilter==='history'?'selected':'')+'>All past mistakes</option></select>':'')+'</div>'+btn('Start Review '+icon('arrow'),'start-list','primary',ids.length?'':'disabled')+'</div>';if(!ids.length)return out+'<section class="panel empty">'+icon(review?'review':'star')+'<h2>'+(review?'No mistakes match these filters':'No saved questions yet')+'</h2><p>'+(review?'Incorrect answers appear here after submission. Change the filter to see all past mistakes.':'Select the star while practicing to save a question and its notes.')+'</p>'+btn('Go to Practice','nav-practice','primary')+'</section>';out+='<div class="record-list">'+ids.slice(0,listLimit).map(id=>{const q=Q.get(id),st=state.stats[id];return '<article class="record-card"><div class="record-title"><div class="badge-row"><span class="tag">Part '+q.part+'</span><span class="tag gray">'+TOPICS[q.topic]+'</span>'+(st?.wrong?'<span class="tag orange">Incorrect attempts: '+st.wrong+' times</span>':'')+'</div><h3>'+esc(q.prompt)+'</h3>'+questionReference(id)+(state.notes[id]?'<p class="note-preview">'+icon('note')+' '+esc(state.notes[id])+'</p>':'')+'</div>'+btn((review?'View Explanation ':'practice session ')+icon('arrow'),review?'view-explanation':'open-question','small','data-id="'+id+'"')+'</article>'}).join('')+'</div>';if(ids.length>listLimit)out+='<div style="text-align:center;margin-top:22px">'+btn('Show More ('+(ids.length-listLimit)+')','more-list')+'</div>';out+='<p class="hint">Total: '+ids.length+' questions. Original passages and audio remain available, and new attempts are added to your history.</p>';return out}
function statsPage(){const s=statsSummary();let out=heading('See your progress grow.','Use your answer history to understand practice volume, accuracy, and areas to improve.','YOUR PROGRESS');out+='<div class="stats-grid">'+[['book',fmt(s.attempts),'Total attempts','times'],['target',s.accuracy===null?'—':s.accuracy,'Overall accuracy',s.accuracy===null?'':'%'],['review',fmt(s.wrongIds.length),'Questions to review','questions'],['check',fmt(state.sessions.length),'Completed sessions','times']].map(([i,v,l,u])=>'<div class="stat"><div class="stat-icon">'+icon(i)+'</div><div><div class="stat-value">'+v+'<small>'+u+'</small></div><div class="stat-label">'+l+'</div></div></div>').join('')+'</div>';out+='<div class="data-grid"><section class="panel"><h2>Accuracy by question type</h2><div class="metric-bars">'+Object.entries(PARTS).map(([id,name])=>metric('Part '+id,state.attempts.filter(a=>a.part===Number(id)))).join('')+'</div></section><section class="panel"><h2>Accuracy by topic</h2><div class="metric-bars">'+Object.entries(TOPICS).map(([id,name])=>metric(name,state.attempts.filter(a=>a.topic===id))).join('')+'</div><p class="hint">Repeating a question counts as a new attempt. These metrics track learning progress, not official TOEIC scores.</p></section></div><div class="section-heading"><h2>Recent Completed Sessions</h2><span>'+state.sessions.length+' records</span></div>';if(!state.sessions.length)out+='<section class="panel empty"><p>Complete your first session to see your history here.</p>'+btn('Start Practicing','nav-practice','primary')+'</section>';else out+='<div class="record-list">'+state.sessions.slice().reverse().slice(0,30).map(r=>'<article class="record-card"><div><h3>'+esc(displayEnglish(r.title))+'</h3><p>'+new Date(r.finishedAt).toLocaleString('en-US')+' · '+r.correct+' / '+r.total+' correct answers</p></div>'+btn('View Results','open-result','small','data-id="'+r.id+'"')+'</article>').join('')+'</div>';return out}
function metric(label,arr){const c=arr.filter(a=>a.correct).length,pct=arr.length?Math.round(c/arr.length*100):0;return '<div class="metric-line"><span>'+esc(label)+'</span><div class="metric-track"><div class="metric-fill" style="width:'+pct+'%"></div></div><span class="metric-right">'+(arr.length?pct+'% · '+arr.length:'Not answered yet')+'</span></div>'}
function dataPage(){const total=allTests().reduce((n,t)=>n+t.reading+t.listening,0);return heading('Take your progress with you.','Back up your records, import new packs, and adjust your reading preferences.','DATA & PREFERENCES')+historyNotice()+'<div class="data-grid"><section class="panel"><h2>'+icon('download')+' Learning Record Backup</h2><p>Export answers, mistakes, saved questions, notes, and unfinished sessions. Make a backup before moving folders, changing devices, or updating the app.</p><div class="btn-row">'+btn('Export Backup','export-backup','primary')+(syncOwner?'':btn('Import Backup','import-backup'))+'</div><p class="hint">Last export:'+(lastBackupTime()?new Date(lastBackupTime()).toLocaleString('en-US'):'Not exported yet')+'</p></section><section class="panel"><h2>'+icon('upload')+' Add Test Packs</h2><p>Add questions by selecting a compatible JSON test pack. Built-in audio is stored in the audio folder; additional audio must also be placed in the website folder.</p><div class="btn-row">'+btn('Import JSON Test Pack','import-pack','primary')+'<a class="btn" href="data/example-pack.json" download>Download Example Format</a></div><p class="hint">Currently: '+allTests().length+' test packs · '+fmt(total)+' questions.</p></section><section class="panel"><h2>'+icon('settings')+' Reading Preferences</h2><div class="field"><label for="font-scale">Text size</label><select id="font-scale"><option value="1" '+(state.settings.fontScale===1?'selected':'')+'>Standard</option><option value="1.1" '+(state.settings.fontScale===1.1?'selected':'')+'>Larger by 10%</option><option value="1.2" '+(state.settings.fontScale===1.2?'selected':'')+'>Larger by 20%</option></select></div><p class="hint">All practice sessions hide correctness, answers, translations, and explanations until submission.</p></section><section class="panel"><h2>'+icon('shield')+' Local Storage Status</h2><p><strong>'+(storageMode==='indexeddb'?'IndexedDB · Saving available':storageMode==='localstorage'?'localStorage · Backup storage available':storageMode==='tabstorage'?'Tab-only storage · Export before closing':'Temporary mode · Permanent storage unavailable')+'</strong></p><p>Guest records belong to this browser profile and website address. Private browsing, clearing site data, or moving folders may make unsynced records inaccessible.</p><p class="hint">No account is required. Current practice and completed history in a signed-in account workspace are eligible for sync.</p></section></div><section class="panel" style="margin-top:20px"><h2>What is included?</h2><ul class="inline-list"><li>'+fmt(catalog.tests.length)+' original tests: '+fmt(catalog.tests.reduce((n,t)=>n+t.reading,0))+' Reading and '+fmt(catalog.tests.reduce((n,t)=>n+t.listening,0))+' Listening questions. Traditional Chinese translations and explanations are shown only on answer explanation pages.</li><li>Part 1 uses original AI-generated photographs. Listening uses bundled synthetic speech.</li><li>Formal tests use a single-play Listening sequence whose duration is shown before the test, followed by 75 minutes of Reading. Practice mode allows replay.</li><li>This is practice material, not official questions, calibrated difficulty, or an official TOEIC score conversion.</li></ul><div class="btn-row"><a class="btn small" href="使用說明.html" target="_blank" rel="noopener">Open User Guide</a><a class="btn small" href="question-debug.html" target="_blank" rel="noopener">Question Debug</a>'+(syncOwner?'':btn('Clear Learning Records','reset-progress','danger small'))+'</div></section>'}
// Preserve the v1 payload and the original compact restore budget. Older
// pretty-printed exports get a bounded read allowance, not a larger data budget.
const BACKUP_DATA_BYTES=30*1024*1024,BACKUP_LEGACY_FILE_BYTES=48*1024*1024;
const backupFileBlob=obj=>new Blob([JSON.stringify(obj)],{type:'application/json;charset=utf-8'});
function downloadBackupBlob(name,blob){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000)}
function checkBackupFileSize(size){
 if(size>BACKUP_LEGACY_FILE_BYTES)throw new Error('Backup could not be restored: the file is larger than 48 MiB. Keep the original file; restoring separate files does not combine records.');
}
function parseBackupFile(text,size){
 let obj;try{obj=JSON.parse(text)}catch{throw new Error('Backup could not be restored: the file is not valid JSON. Keep the original and choose another SHIFT backup.')}
 if(!obj||obj.format!=='shift-learning-backup'||obj.version!==1)throw new Error('This is not a supported SHIFT learning-record backup.');
 if(size>BACKUP_DATA_BYTES&&backupFileBlob(obj).size>BACKUP_DATA_BYTES)throw new Error('Backup could not be restored: its data is larger than 30 MiB. Keep the original file; restoring separate files does not combine records.');
 return obj;
}
function lastBackupTime(){let stored=0;try{stored=Number(guestStorage().getItem(scopedKey(BACKUP_TIME_KEY)))||0}catch(e){}return Math.max(state.lastBackup||0,lastExportAt,stored>=0&&stored<8640000000000000?stored:0)}
async function backupSnapshot(owner=syncOwner,epoch=syncEpoch,includeUnsaved=false){
 // Drain saves already queued in this tab, then read only the workspace that
 // requested the backup. An auth change must not redirect a pending export.
 const assertWorkspace=()=>{if(owner!==syncOwner||epoch!==syncEpoch)throw Error('Backup could not be prepared because the account changed. Open Data & Settings and try again.');};
 try{await saveQueue}catch(error){
  assertWorkspace();
  if(!(includeUnsaved&&localSaveFailure)&&storageMode!=='memory')throw error
 }
 assertWorkspace();
 let saved;
 // Emergency export is the current tab's snapshot, not the older durable copy.
 if(includeUnsaved&&(localSaveFailure||accountActiveConflict))saved=state;
 else if(storageMode==='indexeddb'&&db){
  saved=await new Promise((resolve,reject)=>{
   const request=db.transaction('kv','readonly').objectStore('kv').get(scopedKey('state',owner));
   request.onsuccess=()=>resolve(request.result);
   request.onerror=()=>reject(new Error('Saved records could not be read. Reopen the app and try again.'));
  });
 }else if(storageMode==='localstorage'||storageMode==='tabstorage'){
  const raw=guestStorage().getItem(guestStorageKey(owner));
  if(raw!==null)saved=JSON.parse(raw);
 }
 assertWorkspace();
 const backup={...(saved??state)};
 delete backup.accountActiveRevision;delete backup.syncSent;delete backup.guestActiveRevision;delete backup.guestSupersededSessions;
 return backup;
}
async function exportBackup(){
 const owner=syncOwner,epoch=syncEpoch,saved=await backupSnapshot(owner,epoch,true);
 if(owner!==syncOwner||epoch!==syncEpoch)throw Error('Backup could not be prepared because the account changed. Open Data & Settings and try again.');
 const exportedAt=new Date().toISOString(),exportTime=Date.parse(exportedAt);
 const blob=backupFileBlob({format:'shift-learning-backup',version:1,exportedAt,state:{...saved,lastBackup:exportTime}});
 // Even oversized snapshots remain downloadable; never truncate records.
 downloadBackupBlob('SHIFT-learning-backup-'+exportedAt.slice(0,10)+'.json',blob);
 lastExportAt=exportTime;
 try{guestStorage().setItem(scopedKey(BACKUP_TIME_KEY,owner),String(exportTime))}catch(e){}
 notify(blob.size>BACKUP_DATA_BYTES?'This backup cannot be restored here because its data exceeds 30 MiB. Keep the original file from the download.':'Your backup is ready to download.');if(route==='data')render()
}
async function importBackup(file){
 const owner=syncOwner,epoch=syncEpoch;
 const restoreFailure='Backup could not be saved. Your original backup file and current learning records were not changed.';
 const unchangedGuest=()=>owner===null&&syncOwner===owner&&syncEpoch===epoch;
 const stale=()=>notify('Backup could not be restored because the account changed. Switch to guest mode and try again.');
 if(!unchangedGuest())return stale();
 checkBackupFileSize(file.size);
 const raw=await file.text();
 if(!unchangedGuest())return stale();
 const obj=parseBackupFile(raw,file.size);
 const next=normalizeState(obj.state);
 const omitted=(obj.state.importedPacks||[]).filter(p=>officialEntry(p?.testId)).length;
 const count=next.attempts.length,notes=Object.keys(next.notes).length;
 confirmBox('Restore these learning records?','The backup contains '+count+' answer record'+(count===1?'':'s')+' and '+notes+' note'+(notes===1?'':'s')+'. Restoring replaces current records. Export your current backup first.'+(omitted?' Custom definitions with official test IDs will not be installed. Your saved scores and answers are kept.':''),async()=>{
  if(!unchangedGuest())return stale();
  if(guestBackupApplying)return notify('Backup could not be restored because another backup is still being restored.');
  if(guestSubmitPending)return notify('Finish saving the current session before restoring a backup.');
  guestBackupApplying=true;
  let committed=false;
  try{
   // Drain any earlier guest write without making its failure reject this new restore.
   await saveQueue.catch(()=>{});
   if(!unchangedGuest())return stale();
   if(next.importedPacks.length)await loadAllOfficial();
   if(!unchangedGuest())return stale();
   next.noteDraftEpoch=uid();
   if(await persist(true,false,'restore',null,next)!==true)throw new Error('Backup state was not committed');
   committed=true;
   if(!unchangedGuest())return stale();
   resumeEnv=null;state=next;clearNoteDraft(true);lastResult=null;stopAudio();
   await installPackIndexes();
   if(!unchangedGuest())return stale();
   if(persistentError===restoreFailure)persistentError='';
   route='home';render();notify(omitted||unavailableCustom.size?'Learning records restored. Conflicting custom packs were not loaded.':'Learning records restored.');
  }catch(error){
   console.error(error);
   notify(committed?'Learning records were saved. Reload to finish opening them.':restoreFailure);
  }finally{
   guestBackupApplying=false;
   if(authRestoreStatus==='waiting'&&navigator.onLine!==false)void recheckAuthOnReconnect()
  }
 },'Confirm Restore')
}
async function importPack(file){if(file.size>20*1024*1024)throw new Error('Each additional pack must be smaller than 20 MB, Use one file per test.');const p=validatePack(JSON.parse(await file.text()));if(officialEntry(p.testId))throw new Error('Imported packs cannot overwrite built-in packs. Use a new testId.');await loadAllOfficial();const old=state.importedPacks.find(x=>x.testId===p.testId);const oldQIds=new Set((old?.questions||[]).map(q=>q.id));for(const q of p.questions)if(Q.has(q.id)&&!oldQIds.has(q.id))throw new Error('Question ID already exists:'+q.id);const oldGIds=new Set((old?.groups||[]).map(g=>g.id));for(const g of p.groups)if(G.has(g.id)&&!oldGIds.has(g.id))throw new Error('Groups ID already exists:'+g.id);const commit=async()=>{registerPack(p);unavailableCustom.delete(p.testId);state.importedPacks=state.importedPacks.filter(x=>x.testId!==p.testId);state.importedPacks.push(p);await persist();render();notify('Imported '+p.questions.length+' questions.')};if(old)confirmBox('Update this test pack?','The new file will replace '+p.testId+'.Existing answers and notes are kept. Question ID values must remain unchanged.',commit,'Update Pack');else await commit()}
async function resume(){const s=state.active;if(!s){notify('There is no unfinished practice session.');return}if(s.reservedPackConflict)throw new Error('This saved session used a custom pack with an official test ID. Your saved answers are kept, but its original pack is not available to resume.');for(const id of s.testIds||[])await loadTest(id);await prepareResume(s);if(restoreListeningTabPoint(s))await persist();route='quiz';mobileNav=false;syncListeningCountdown(s);if(beginReadingClock(s))await persist();render();if(formalClockExpired(s)){beginFormalExpiry(s);return}if(listening(s)){const g=sessionGroup(questionByActive()?.groupId,s);void runFormalGroup(g,{prepareOnly:true})}if(s.mode==='exam'&&!listening(s)&&!s.readingStartsOnReturn&&(formal(s)?s.sectionDeadline:s.deadline)<=now())await finishSession(true)}
async function beginReview(kind){
await loadAll();let ids;
if(kind==='result'){const r=lastResult||state.sessions.at(-1);if(!r){notify('There is no completed session available for review.');return}const outcomes=sessionOutcomes(r);ids=r.questionIds.filter(id=>outcomes.get(id)===false)}
else if(route==='favorites')ids=Object.keys(state.stars).filter(id=>state.stars[id]);
else ids=Object.keys(state.stats).filter(id=>listFilter==='history'?state.stats[id].wrong>0:listFilter==='due'?state.stats[id].needsReview&&state.stats[id].due<=now():state.stats[id].needsReview);
if(kind!=='result')ids=ids.filter(matchesListSearch);
const qs=ids.map(id=>Q.get(id)).filter(Boolean);
if(!qs.length){notify(kind==='result'?'There are no available incorrect questions to review in this session.':'No questions match these filters. Try changing your selection.');return}
await startSession(groupedSelection(qs,40),kind==='result'?'Review This Session':route==='favorites'?'Saved Question Practice':'Review Mistakes');
}
async function action(name,el){if(name==='export-unsaved-local-backup'){
 if(!diagnostic&&localSaveFailure)return exportBackup();
 return
}if(name==='retry-local-save'){
 if(!localSaveFailure)return;
 if(state.active&&guestRejectedAutoSubmit===state.active){
  guestRejectedAutoSubmit=null;return finishSession(true)
 }
 return persist()
}if(formal(state.active)&&route==='quiz'&&formalClockExpired(state.active)){beginFormalExpiry(state.active);return}if(name==='dismiss-page-error'){persistentError='';showPersistentError();return}if(diagnostic&&!['play-audio','question-grid','jump','close-modal','prev-question','next-question','answer','copy-question-uuid'].includes(name))return;if(name==='checkpoint-cloud'||name==='checkpoint-local'){void syncCheckpoint(name==='checkpoint-cloud'?'cloud':'local');return}if(name.startsWith('sync-'))return syncAccountAction(name);if(name==='copy-question-uuid')return copyQuestionUuid(el);if(name.startsWith('nav-'))return navigate(name.slice(4));if(name==='menu'){mobileNav=true;render();document.querySelector('#shift-sidebar nav button')?.focus();return}if(name==='menu-close'){mobileNav=false;render();document.querySelector('.mobile-menu')?.focus();return}if(name==='close-modal'){closeModal();return}if(name==='quick-reading')return startFiltered({section:'reading',part:'all',topic:'all',difficulty:'all',count:20,unseen:false,accent:'all'});if(name==='quick-listening')return startFiltered({section:'listening',part:'all',topic:'all',difficulty:'all',count:20,unseen:false,accent:'all'});if(name==='topic'){filters.topic=el.dataset.topic;filters.section='all';filters.part='all';return navigate('practice')}if(name==='start-filtered')return startFiltered();if(name==='resume')return resume();if(name==='test-pick'){const id=el.dataset.test;modal('<h2>Choose a practice mode</h2><p>Section practice is graded after submission, not while answering. You can leave and resume later.</p><div class="btn-row">'+btn('Reading 100 questions','test-reading','primary','data-test="'+id+'"')+btn('Listening 100 questions','test-listening','primary','data-test="'+id+'"')+btn('Cancel','close-modal')+'</div>');return}if(['test-reading','test-listening','test-exam'].includes(name)){const id=el.dataset.test;closeModal();await loadTest(id);const qs=allQuestions().filter(q=>q.testId===id&&(name==='test-reading'?q.part>4:name==='test-listening'?q.part<5:true)).sort((a,b)=>a.number-b.number);const t=allTests().find(t=>t.id===id);const title=t.title+(name==='test-reading'?' · Reading':name==='test-listening'?' · Listening':' · Full Test');if(name==='test-exam'){const pack=state.importedPacks.find(p=>p.testId===id)||(window.SHIFT_PACKS||[]).find(p=>p.testId===id);if(!pack?.listeningPlan?.frames?.length){notify('This pack has no formal-listening plan. Choose Section Practice.');return}confirmBox('Start a Formal Test','The listening sequence lasts '+listeningDurationLabel(pack.listeningPlan)+'. The first playback opens with the listening directions and an unscored example. Audio plays once, in order, without skipping or replay. Switching tabs pauses the countdown, not the audio. Use Pause Listening and Resume Listening to control audio without replay. Each group advances automatically after playback and answer time. Reading lasts 75 minutes, with free navigation among reading groups. When time is up, answers lock immediately; after a five-second notice, the test advances or submits automatically. This is an independently created practice test, not an ETS official test.',()=>startSession(qs,title,'exam'),'Start Test')}else return startSession(qs,title);return}if(name==='answer'){
 const s=state.active,q=sessionQuestion(el.dataset.question,s)||questionByActive(),choice=el.dataset.option;
 const ids=groupQuestions().map(item=>item.id);
 if(!q||!s||!ids.includes(q.id)||!q.options.some(o=>o.id===choice))return;
 const initialFocus=document.activeElement;
 s.answers[q.id]=choice;
 await persist();
 const activeFocus=document.activeElement,focusCard=activeFocus?.closest('.grouped-question');
 const stillInGroup=route==='quiz'&&state.active===s&&ids.join('\u0000')===groupQuestions().map(item=>item.id).join('\u0000');
 // The keyboard shortcut targets the focused card. Keep that target after replacing the quiz DOM.
 const restore=stillInGroup&&!document.getElementById('modal').open&&focusCard&&activeFocus.matches('button[data-action="answer"][data-option]')&&ids.includes(activeFocus.dataset.question)
  ?[activeFocus.dataset.question,initialFocus===activeFocus&&activeFocus.dataset.question===q.id?choice:activeFocus.dataset.option]:null;
 render();
 if(restore&&!document.getElementById('modal').open){
  const nextFocus=Array.from(document.querySelectorAll('.grouped-question button[data-action="answer"]:not(:disabled)')).find(o=>o.dataset.question===restore[0]&&o.dataset.option===restore[1]);
  nextFocus?.focus({preventScroll:true});
 }
 return
}if(name==='submit-answer')return submitAnswer();if(name==='next-question'){return moveGroup(1)}if(name==='prev-question'){return moveGroup(-1)}if(name==='finish-session')return finishSession();if(name==='question-grid'){questionGrid();return}if(name==='jump'){const s=state.active;if(s){const index=Number(el.dataset.index);if(listening(s)||(formal(s)&&sessionQuestion(s.questionIds[index],s)?.part<5))return;closeModal();stopAudio();s.index=index;s.index=s.questionIds.indexOf(groupQuestions()[0].id);persist();render();window.scrollTo(0,0)}return}if(name==='finish-from-modal'){closeModal();return finishSession()}if(name==='star'){const id=el.dataset.id;state.stars[id]=!state.stars[id];if(await persist()===false)return;render();notify(state.stars[id]?'Question saved.':'Question removed from saved items.');return}if(name==='toggle-translation'){state.settings.translation=!state.settings.translation;await persist();render();return}if(name==='transcript'){const q=questionByActive(),revealed=state.active?.mode==='practice'&&!!state.active?.submitted?.[q?.id];activeTranscript=!(activeTranscript===null?revealed:activeTranscript);render();return}if(name==='play-audio')return playAudio(el.dataset.group);if(name==='view-explanation'){
 clearTimeout(searchTimeout);
 await loadAll();
 const detail=explanationQueue(el.dataset.id,el.dataset.session);
 if(!detail){notify('There is no submitted answer record available for this question.');return}
 openExplanation(detail);return
}if(name==='next-explanation'){
 const d=reviewDetail;
 if(route!=='answer-review'||!d||!d.entries[d.index+1])return;
 openExplanation({...d,...d.entries[d.index+1],index:d.index+1});return
}if(name==='back-review'){
 const detail=reviewDetail;stopAudio();route=detail?.returnTo||'review';reviewDetail=null;render();focusReviewOrigin(detail);return
}if(name==='open-question'){await loadAll();const q=Q.get(el.dataset.id);if(q)return startSession(relatedQuestions(q),'Group Review');return}if(name==='start-list')return beginReview('list');if(name==='review-result')return beginReview('result');if(name==='more-list'){listLimit+=40;render();return}if(name==='open-result'){await loadAll();lastResult=state.sessions.find(s=>s.id===el.dataset.id);route='result';render();window.scrollTo(0,0);return}if(name==='export-backup')return exportBackup();if(name==='import-backup'){if(syncOwner)return;document.getElementById('backup-input').click();return}if(name==='import-pack'){await loadAll();document.getElementById('pack-input').click();return}if(name==='reset-progress'){if(syncOwner)return;confirmBox('Clear your learning records?',storageMode==='tabstorage'?'This clears this tab’s answers, mistakes, saved questions, notes, and unfinished progress only. Previously shared records are not changed. Export a backup before clearing anything.':'This removes local answers, mistakes, saved questions, notes, and unfinished progress. Imported packs are kept. Export a backup before clearing anything.',async()=>{const imported=state.importedPacks;state={formatVersion:1,settings:{fontScale:1,translation:false},attempts:[],stats:{},stars:{},notes:{},sessions:[],active:null,importedPacks:imported,lastBackup:null};clearNoteDraft();lastResult=null;if(await persist(false,false,'clear')===false)return;render();notify('Learning records cleared.')},'Confirm Clear')}}
document.addEventListener('click',e=>{const el=e.target.closest('[data-action]');if(!el||el.disabled)return;e.preventDefault();
 const name=el.dataset.action; void withBusy(async()=>{await action(name,el);if(/^(?:answer|resume|next-question|prev-question|jump|play-audio|finish-session|finish-from-modal|test-listening|test-reading|test-exam|quick-reading|quick-listening|start-filtered|nav-)/.test(name))scheduleCheckpoint()})
});
document.addEventListener('change',e=>{const el=e.target;withBusy(async()=>{if(el.id==='filter-section'){filters.section=el.value;filters.part='all';if(el.value==='reading')filters.accent='all';render()}else if(el.id==='filter-accent'){filters.accent=el.value;if(el.value!=='all'){filters.section='listening';if(Number(filters.part)>4)filters.part='all'}render()}else if(el.id==='filter-part'){filters.part=el.value;if(Number(el.value)>4)filters.accent='all';if(el.value!=='all')filters.section=Number(el.value)>4?'reading':'listening';render()}else if(el.id==='filter-topic')filters.topic=el.value;else if(el.id==='filter-difficulty')filters.difficulty=el.value;else if(el.id==='filter-count')filters.count=Number(el.value);else if(el.id==='filter-unseen')filters.unseen=el.checked;else if(el.id==='review-filter'){listFilter=el.value;listLimit=40;render()}else if(el.id==='font-scale'){state.settings.fontScale=Number(el.value);await persist();render()}else if(el.id==='default-translation'){state.settings.translation=el.checked;await persist()}else if(el.id==='audio-speed'&&!listening()){player.playbackRate=Number(el.value);if(savePracticeMedia(true))void persist()}else if(!diagnostic&&el.id==='backup-input'){const f=el.files[0];el.value='';if(f&&!syncOwner)await importBackup(f)}else if(!diagnostic&&el.id==='pack-input'){const f=el.files[0];el.value='';if(f)await importPack(f)}})});
let searchTimeout;
document.addEventListener('input',e=>{const el=e.target;if(el.id==='question-note'||el.classList.contains('group-note')){saveNoteInput(el.dataset.id,el.value)}else if(el.id==='audio-seek'&&!listening()&&Number.isFinite(player.duration)){scrubPractice(quizGroup(currentAudioGroup),Number(el.value))}else if(el.id==='list-search'){listSearch=el.value;clearTimeout(searchTimeout);searchTimeout=setTimeout(()=>{const pos=el.selectionStart;render();const input=document.getElementById('list-search');input?.focus();input?.setSelectionRange(pos,pos)},300)}});
window.matchMedia?.('(max-width:760px)').addEventListener?.('change',()=>{const sidebar=document.getElementById('shift-sidebar');if(window.matchMedia('(max-width:760px)').matches===false&&mobileNav){mobileNav=false;render();return}if(sidebar)sidebar.inert=window.matchMedia('(max-width:760px)').matches&&!mobileNav});
function keepDrawerTab(e){
 if(e.key!=='Tab'||!mobileNav||!window.matchMedia?.('(max-width:760px)').matches||document.getElementById('modal').open)return false;
 const menu=document.getElementById('shift-sidebar');
 const controls=menu?[...menu.querySelectorAll('button:not([disabled]),a[href]')].filter(x=>x.getClientRects().length>0):[];
 if(!controls.length)return false;
 const i=controls.indexOf(document.activeElement);
 if(i<0||(e.shiftKey?i===0:i===controls.length-1)){
  e.preventDefault();controls[e.shiftKey?controls.length-1:0].focus();return true;
 }
 return false;
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&mobileNav&&!document.getElementById('modal').open){mobileNav=false;render();document.querySelector('.mobile-menu')?.focus();return}if(keepDrawerTab(e))return;if(route!=='quiz'||document.getElementById('modal').open||e.target.closest('.copy-question-uuid')||(e.key==='Enter'&&e.target.closest('a,button,summary,.chart-full-size'))||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||e.ctrlKey||e.metaKey||e.altKey)return;const card=e.target.closest('.grouped-question'),q=card?sessionQuestion(card.dataset.questionId):questionByActive();if(!q)return;const letter=e.key.toUpperCase();if(['A','B','C','D'].includes(letter)&&q.options.some(o=>o.id===letter)){const el=document.querySelector('[data-question="'+q.id+'"][data-option="'+letter+'"]');if(el&&!el.disabled){e.preventDefault();el.click()}}else if(e.key==='Enter'){const el=document.querySelector('[data-action="submit-answer"], [data-action="next-question"], [data-action="finish-session"]');if(el&&!el.disabled){e.preventDefault();el.click()}}});
player.addEventListener('playing',()=>{checkPracticeRange();startPracticeRangeTimer()});
for(const e of ['timeupdate','seeked'])player.addEventListener(e,checkPracticeRange);
for(const e of ['waiting','pause','ended','emptied','error'])player.addEventListener(e,stopPracticeRangeTimer);
for(const e of ['timeupdate','seeked','playing','pause','ended','ratechange'])player.addEventListener(e,()=>{
 if(savePracticeMedia(e!=='timeupdate'))void persist()
});
document.addEventListener('visibilitychange',()=>{
 const s=state.active;
 if(formal(s)&&route==='quiz'){
  if(listening(s)){syncListeningCountdown(s);void persist();updateExamClock();}
  else if(beginReadingClock(s)){void persist();updateExamClock();}
  return;
 }
 if(document.hidden&&(route==='answer-review'||route==='quiz'&&!listening())){cancelPracticePosition();player.pause();syncAudioUI()}
});
for(const ev of ['timeupdate','loadedmetadata','play','pause','ended'])player.addEventListener(ev,syncAudioUI);
player.addEventListener('ratechange',()=>{
 if(route==='quiz'&&listening()&&player.playbackRate!==1)player.playbackRate=1;
});
player.addEventListener('error',()=>{if(currentAudioGroup)notify('Audio file loading failed. Make sure the audio folder and index.html were extracted together.')});
setInterval(()=>{
 const s=state.active;if(!s||s.mode!=='exam')return;
 if(listening(s)&&!s.listeningStartedAt){syncAudioUI();return}
 const left=examSeconds(s);
 updateExamClock(left);
 if(listening(s)&&route==='quiz'&&!document.hidden&&performance.now()-countdownFor(s).lastSave>=2000)void persist();
 syncAudioUI();
 if(formal(s)&&formalClockExpired(s)){beginFormalExpiry(s);advanceExpiredFormalPhase()}else if(left<=0&&!busy&&!listening(s))withBusy(async()=>{await loadAll();await finishSession(true)});
},1000);
async function bootDiagnostic(){
 const fail=message=>shell('<section class="panel panel-body"><h1>Playback diagnostic</h1><p>'+esc(message)+'</p></section>');
 if(!/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(diagnosticUuid)||!['practice','exam'].includes(diagnosticMode)){
  fail('Choose a listening question and a playback mode in Question Debug.');return
 }
 storageMode='diagnostic';
 try{await installPackIndexes();await loadAllOfficial()}catch(e){fail('Could not load the built-in tests. Reopen Question Debug to retry.');return}
 const target=[...Q.values()].find(q=>q.part<=4&&window.SHIFT_QUESTION_UUID(q.id)===diagnosticUuid);
 if(!target){fail('No built-in listening question matches this UUID.');return}
 const pack=officialPacks.get(target.testId),g=G.get(target.groupId);
 if(!g||diagnosticMode==='practice'&&!g.audio||diagnosticMode==='exam'&&!pack?.listeningPlan?.frames?.some(f=>f.groupId===g.id)){
  fail('The requested playback mode is not available for this question.');return
 }
 const section=pack.questions.filter(q=>q.part<=4).sort((a,b)=>a.number-b.number);
 const start=section.find(q=>q.groupId===target.groupId);
 return startSession(section,officialEntry(target.testId).title+' · Playback Diagnostic',diagnosticMode,start.id)
}
async function boot(){if(diagnostic)return bootDiagnostic();const previousRoute=tabRead(LAST_PAGE_TAB_KEY);await initStorage();const restoredNote=await restoreNoteDraft();await installPackIndexes();await restoreSavedAccount();const lastQuiz=(()=>{try{return sessionStorage.getItem(scopedKey('shift-last-quiz'))}catch(e){return null}})();if(state.active&&lastQuiz===state.active.id){try{await resume()}catch(e){route='home';render();notify(e.message)}}else{route=previousRoute==='data'?'data':'home';render()}if(storageMode==='memory')notify('Only temporary storage is available. Export a backup before leaving.');else if(restoredNote)notify('Your unfinished note draft has been restored.');if(syncOwner){void startSync();void syncCheckpoint()}}
boot().catch(e=>{console.error(e);app.innerHTML='<div class="boot"><h1>Unable to Open Practice</h1><p>'+esc(e.message)+'</p><p>Extract the entire folder and use Chrome or Edge to open index.html.</p></div>'});
})();
