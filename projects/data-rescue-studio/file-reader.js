/* Data Rescue local file boundary: bytes are untrusted, no upload or network. */
(function(root,factory){
 const api=factory(root);
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.DataRescueFileReader=api;
})(typeof window!=='undefined'?window:null,function(root){
 'use strict';
 const maxBytes=5000000;
 function extension(name){
  if(typeof name!=='string')throw Error('Choose a .csv or .tsv file.');
  const match=/\.(csv|tsv)$/i.exec(name);
  if(!match)throw Error('Choose a .csv or .tsv file.');
  return match[1].toLowerCase();
 }
 function requireFile(file){
  if(!file||typeof file.arrayBuffer!=='function')throw Error('Choose a local file.');
  const kind=extension(file.name);
  if(!Number.isSafeInteger(file.size)||file.size<0||file.size>maxBytes)
   throw Error('The selected file is larger than 5 MB or has an invalid size.');
  return kind;
 }
 function decode(bytes){
  const data=bytes instanceof Uint8Array?bytes:new Uint8Array(bytes);
  if(data.byteLength>maxBytes)throw Error('The selected file is larger than 5 MB.');
  let decoded;
  try{decoded=new TextDecoder('utf-8',{fatal:true}).decode(data);}
  catch(_){throw Error('Invalid UTF-8 text. Convert the file to UTF-8 before importing.');}
  if(decoded.includes('\u0000'))throw Error('NUL characters are not supported in a CSV or TSV file.');
  return decoded;
 }
 async function readValidated(file,parser){
  const kind=requireFile(file);
  const parse=parser||(root&&root.DataRescue&&root.DataRescue.parseDelimited);
  if(typeof parse!=='function')throw Error('CSV parser is unavailable.');
  const buffer=await file.arrayBuffer();
  // Trust neither declared size nor returned bytes; parse and hash the SAME buffer.
  if(!(buffer instanceof ArrayBuffer))
   throw Error('Unable to read file bytes. Re-select the file.');
  if(buffer.byteLength>maxBytes)
   throw Error('The selected file is larger than 5 MB.');
  if(buffer.byteLength!==file.size)
   throw Error('File byte count changed or is inconsistent. Re-select the file.');
  // The extension selects the separator. A tab inside CSV text must not
  // silently become a new column (or a different reconciliation key).
  const parsed=parse(decode(buffer),kind==='tsv'?'\t':',');
  return {parsed,buffer};
 }
 async function read(file,parser){
  return (await readValidated(file,parser)).parsed;
 }
 // Fingerprint ORIGINAL bytes, not normalized CSV cells or exported JSON.
 // A hash can check byte equality; it does not authenticate who supplied a file.
 async function readWithDigest(file,parser,subtleOverride){
  const {parsed,buffer}=await readValidated(file,parser);
  const subtle=subtleOverride===undefined?(root&&root.crypto&&root.crypto.subtle):subtleOverride;
  if(!subtle||typeof subtle.digest!=='function')
   return {parsed,provenance:null};
  let hash;
  try{hash=await subtle.digest('SHA-256',buffer);}
  catch(_){return {parsed,provenance:null};}
  if(!(hash instanceof ArrayBuffer)||hash.byteLength!==32)
   throw Error('The source-file fingerprint was invalid.');
  const sha256=Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
  return {parsed,provenance:{sha256,byteCount:buffer.byteLength}};
 }
 return {read,readWithDigest,decode,extension,requireFile,maxBytes};
});
