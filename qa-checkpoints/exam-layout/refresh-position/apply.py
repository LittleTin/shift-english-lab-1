"""Generate isolated refresh-journal and narrow-stat-grid candidates."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('app',type=Path);p.add_argument('css',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
assert not a.out.exists()
app=a.app.read_text();css=a.css.read_text()
def replace(s,old,new):
 assert s.count(old)==1,repr(old)
 return s.replace(old,new,1)
app=replace(app,"let audioRun=0,formalRunning=false,formalElapsed=0,formalRole='',captureFormal=null,visibilityResume=null;","""let audioRun=0,formalRunning=false,formalElapsed=0,formalRole='',captureFormal=null,visibilityResume=null;
const LISTENING_TAB_KEY='shift-formal-listening-refresh-v1';
function frameSignature(f){return f&&JSON.stringify([f.kind,f.role,f.src||null,f.start??null,f.end??null,Number(f.duration)])}
function saveListeningTabPoint(){
 if(!formalRunning||route!=='quiz'||!listening()||!currentAudioGroup)return;
 captureFormal?.();
 const s=state.active,g=sessionGroup(currentAudioGroup,s),u=s.audioUsed?.[currentAudioGroup];
 if(!g||u?.status!=='started')return;
 const frames=groupFrames(g),f=frames[u.frame];if(!f)return;
 try{sessionStorage.setItem(LISTENING_TAB_KEY,JSON.stringify({
  id:s.id,startedAt:s.startedAt,version:s.contentVersion??null,edition:s.audioEdition,index:s.index,
  question:s.questionIds[s.index],group:g.id,frame:u.frame,offset:u.offset,signature:frameSignature(f)
 }))}catch{}
}
function restoreListeningTabPoint(s){
 let x;try{const raw=sessionStorage.getItem(LISTENING_TAB_KEY);sessionStorage.removeItem(LISTENING_TAB_KEY);x=JSON.parse(raw)}catch{return false}
 if(!listening(s)||!x||x.id!==s.id||x.startedAt!==s.startedAt||x.version!==(s.contentVersion??null)||
    x.edition!==s.audioEdition||x.index!==s.index||x.question!==s.questionIds[s.index])return false;
 const q=sessionQuestion(s.questionIds[s.index],s),g=q?.groupId&&sessionGroup(q.groupId,s);
 if(g?.id!==x.group)return false;
 const frames=groupFrames(g),f=frames[x.frame],u=s.audioUsed?.[g.id]; 
 if(!u||u.status==='ended'||!Number.isSafeInteger(x.frame)||x.frame<0||!f||
    x.signature!==frameSignature(f)||!Number.isFinite(x.offset)||x.offset<0||x.offset>Number(f.duration))return false;
 const old=resumePosition(u,frames);
 if(x.frame<old.frame||(x.frame===old.frame&&x.offset<=old.offset))return false;
 s.audioUsed[g.id]={...u,status:'interrupted',frame:x.frame,offset:x.offset};return true;
}
window.addEventListener?.('pagehide',saveListeningTabPoint);
""")
app=replace(app,"  visibilityResume={sessionId:state.active?.id,groupId:currentAudioGroup};\n  stopAudio();","  saveListeningTabPoint();\n  visibilityResume={sessionId:state.active?.id,groupId:currentAudioGroup};\n  stopAudio();")
app=replace(app,"await prepareResume(s);route='quiz';","await prepareResume(s);if(restoreListeningTabPoint(s))await persist();route='quiz';")
css=replace(css,'.stats-grid{grid-template-columns:repeat(2,1fr);margin:18px 0 26px;gap:10px}', '.stats-grid{grid-template-columns:repeat(2,minmax(0,1fr));margin:18px 0 26px;gap:10px}.stats-grid .stat{min-width:0}.stats-grid .stat-icon{flex-shrink:0}.stats-grid .stat-value,.stats-grid .stat-label{overflow-wrap:anywhere}')
a.out.mkdir();(a.out/'app.js').write_text(app);(a.out/'style.css').write_text(css)
