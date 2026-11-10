/* A browser click can start a local download; it cannot confirm that a file was saved.
 * Keep all user-entered evidence in this tab; do not log content or filenames.
 */
export function startLocalDownload({filename,content,type,documentRef=document,urlRef=URL,BlobRef=Blob,schedule=setTimeout}) {
  let objectUrl=null, anchor=null, started=false;
  try {
    const blob=new BlobRef([content],{type});
    objectUrl=urlRef.createObjectURL(blob);
    anchor=documentRef.createElement('a');
    anchor.href=objectUrl;
    anchor.download=filename;
    anchor.hidden=true;
    documentRef.body.append(anchor);
    anchor.click();
    started=true;
    try {
      schedule(()=>{try{urlRef.revokeObjectURL(objectUrl);}catch{}},2000);
    } catch {
      // If a timer cannot be scheduled, do not retain the object URL indefinitely.
      try{urlRef.revokeObjectURL(objectUrl);}catch{}
    }
    return true;
  } finally {
    try{anchor?.remove();}catch{}
    if(!started && objectUrl!==null){
      try{urlRef.revokeObjectURL(objectUrl);}catch{}
    }
  }
}
