"""Apply the isolated read-only backup fix, never in place."""
from pathlib import Path
import sys
source,destination=map(Path,sys.argv[1:3])
if source.resolve()==destination.resolve() or destination.exists():
    raise ValueError("Use a new output app.js in the staging copy")
ANCHORS=[('const NOTE_DRAFT_KEY=', "const BACKUP_TIME_KEY='shift-english-last-export-v1';\nlet lastExportAt=0;\nconst NOTE_DRAFT_KEY="), ("(state.lastBackup?new Date(state.lastBackup).toLocaleString('en-US'):'Not exported yet')", "(lastBackupTime()?new Date(lastBackupTime()).toLocaleString('en-US'):'Not exported yet')"), ("async function exportBackup(){state.lastBackup=now();await persist();downloadJson('SHIFT-learning-backup-'+new Date().toISOString().slice(0,10)+'.json',{format:'shift-learning-backup',version:1,exportedAt:new Date().toISOString(),state});notify('Your backup is ready to download.');if(route==='data')render()}", "function lastBackupTime(){let stored=0;try{stored=Number(localStorage.getItem(BACKUP_TIME_KEY))||0}catch(e){}return Math.max(state.lastBackup||0,lastExportAt,stored>=0&&stored<8640000000000000?stored:0)}\nasync function backupSnapshot(){\n // Drain saves already queued in this tab, then read the shared durable snapshot.\n // A backup is read-only with respect to learning state, even in a stale tab.\n await saveQueue;\n let saved;\n if(storageMode==='indexeddb'&&db){\n  saved=await new Promise((resolve,reject)=>{\n   const request=db.transaction('kv','readonly').objectStore('kv').get('state');\n   request.onsuccess=()=>resolve(request.result);\n   request.onerror=()=>reject(new Error('Saved records could not be read. Reopen the app and try again.'));\n  });\n }else if(storageMode==='localstorage'){\n  const raw=localStorage.getItem('shift-english-lab-v1');\n  if(raw!==null)saved=JSON.parse(raw);\n }\n return saved??state;\n}\nasync function exportBackup(){\n const saved=await backupSnapshot(),exportedAt=new Date().toISOString(),exportTime=Date.parse(exportedAt);\n downloadJson('SHIFT-learning-backup-'+exportedAt.slice(0,10)+'.json',{format:'shift-learning-backup',version:1,exportedAt,state:{...saved,lastBackup:exportTime}});\n lastExportAt=exportTime;\n try{localStorage.setItem(BACKUP_TIME_KEY,String(exportTime))}catch(e){}\n notify('Your backup is ready to download.');if(route==='data')render()\n}")]
s=source.read_text(encoding='utf-8')
for old,new in ANCHORS:
    if s.count(old)!=1 or new in s:
        raise ValueError("Missing, ambiguous, or already applied backup fix anchor")
    s=s.replace(old,new,1)
destination.write_text(s,encoding='utf-8')
