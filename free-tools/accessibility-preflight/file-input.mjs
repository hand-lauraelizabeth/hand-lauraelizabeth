// Files are decoded in the browser. Never transmit the document to a server.
export function bindHTMLFile(input, target, status) {
 let version=0;
 // Typing while a File.arrayBuffer() read is pending must take precedence.
 // Clear the file input so the same file can be deliberately selected again.
 target.addEventListener('input',()=>{version++;input.value='';});
 input.addEventListener('change',async()=>{
  const selected=input.files?.[0];if(!selected)return;
  const current=++version;
  try{
   if(!/\.html?$/i.test(selected.name)||!Number.isSafeInteger(selected.size)||selected.size<1||selected.size>2_000_000)throw Error('Choose a nonempty HTML file up to 2 MB.');
   // Read actual bytes, not just untrusted file metadata; never accept a partial or substituted read.
   const buffer=await selected.arrayBuffer();
   if(!(buffer instanceof ArrayBuffer))throw Error('File read did not return an ArrayBuffer.');
   const bytes=new Uint8Array(buffer);
   if(bytes.byteLength!==selected.size)throw Error('File byte count does not match its declared size.');
   const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
   if(current!==version||input.files?.[0]!==selected)return;
   target.value=text;
   status.textContent='HTML loaded locally. Select Analyze.';
  }catch(error){if(current===version){status.textContent='File rejected: '+error.message;status.focus();}}
  finally{if(current===version)input.value='';}
 });
}
