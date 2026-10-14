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
 async function read(file,parser){
  const kind=requireFile(file);
  const parse=parser||(root&&root.DataRescue&&root.DataRescue.parseDelimited);
  if(typeof parse!=='function')throw Error('CSV parser is unavailable.');
  const buffer=await file.arrayBuffer();
  const source=decode(buffer);
  return parse(source,kind==='tsv'?'\t':undefined);
 }
 return {read,decode,extension,requireFile,maxBytes};
});
