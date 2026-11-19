(function(root){
'use strict';
// Fixed SHIFT question namespace. RFC 9562 UUIDv5 over the existing, case-sensitive question ID.
const ns='fa3963cb85854191a84e08f061ecd026'.match(/../g).map(x=>parseInt(x,16));
const rot=(x,n)=>(x<<n)|(x>>>(32-n));
function questionUuid(id){
 const name=new TextEncoder().encode(id),size=16+name.length;
 const bytes=new Uint8Array(Math.ceil((size+9)/64)*64);
 bytes.set(ns);bytes.set(name,16);bytes[size]=128;
 const view=new DataView(bytes.buffer);view.setUint32(bytes.length-4,size*8);
 const h=new Int32Array([0x67452301,0xefcdab89,0x98badcfe,0x10325476,0xc3d2e1f0]),w=new Int32Array(80);
 for(let pos=0;pos<bytes.length;pos+=64){
  for(let i=0;i<16;i++)w[i]=view.getInt32(pos+i*4);
  for(let i=16;i<80;i++)w[i]=rot(w[i-3]^w[i-8]^w[i-14]^w[i-16],1);
  let [a,b,c,d,e]=h;
  for(let i=0;i<80;i++){
   const f=i<20?(b&c)|(~b&d):i<40||i>=60?b^c^d:(b&c)|(b&d)|(c&d);
   const k=i<20?0x5a827999:i<40?0x6ed9eba1:i<60?0x8f1bbcdc:0xca62c1d6;
   const next=(rot(a,5)+f+e+k+w[i])|0;
   e=d;d=c;c=rot(b,30);b=a;a=next;
  }
  h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;
 }
 for(let i=0;i<4;i++)view.setInt32(i*4,h[i]);
 bytes[6]=(bytes[6]&15)|80;bytes[8]=(bytes[8]&63)|128;
 const hex=Array.from(bytes.subarray(0,16),x=>x.toString(16).padStart(2,'0')).join('');
 return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
}
if(typeof module==='object'&&module.exports)module.exports=questionUuid;
else root.SHIFT_QUESTION_UUID=questionUuid;
})(globalThis);
