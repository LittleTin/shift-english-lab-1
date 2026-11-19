'use strict';
const assert=require('node:assert/strict'),{test}=require('node:test'),http=require('node:http');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{createHash}=require('node:crypto');
const {target,transport}=require('./backup-two-tab.cjs');
test('transport checks exact app, mp3 and wav ranges and refuses unsafe origin',async()=>{
 for(const bad of ['https://example.com/','http://127.0.0.1/#x','http://127.0.0.1/?x=y','http://u:p@127.0.0.1/'])assert.throws(()=>target(bad));
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'shift-smoke-'));fs.mkdirSync(path.join(root,'assets'));fs.mkdirSync(path.join(root,'audio'));
 const app=Buffer.from('async function backupSnapshot() {}');
 const media=Buffer.from(Array.from({length:240},(_,i)=>i));
 const wav='audio/new.wav',mp3='audio/old.mp3',asset='assets/app.js';
 for(const ref of [asset,wav,mp3])fs.writeFileSync(path.join(root,ref),ref===asset?app:media);
 let corrupt=false;
 const server=http.createServer((req,res)=>{
  const ref=req.url.replace('/shift/',''), data=ref===asset?app:media;
  if(req.method==='HEAD'){res.writeHead(200,{'Content-Length':data.length}).end();return;}
  if(req.headers.range==='bytes=64-127'){
   res.writeHead(206,{'Content-Range':`bytes 64-127/${data.length}`}).end(corrupt?Buffer.alloc(64):data.subarray(64,128));return;
  }
  if(req.headers.range){res.writeHead(416).end();return;}
  res.writeHead(200).end(data);
 });
 try{
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve)});
  const url=target(`http://127.0.0.1:${server.address().port}/shift/`);
  const sha=createHash('sha256').update(app).digest('hex');
  await transport(url,root,sha,[wav,mp3]);
  corrupt=true;await assert.rejects(transport(url,root,sha,[wav,mp3])); 
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));fs.rmSync(root,{recursive:true,force:true});}
});
