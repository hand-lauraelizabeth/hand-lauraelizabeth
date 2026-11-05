/* Browser-local download lifecycle. A click starts a download; it cannot confirm a save.
 * Do not log user-provided content or filenames to an external service.
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
      // A failed timer must not leave a persistent object URL.
      try{urlRef.revokeObjectURL(objectUrl);}catch{}
    }
    return true;
  } finally {
    // A blocked click or URL creation must not leave temporary DOM or URLs.
    try{anchor?.remove();}catch{}
    if(!started && objectUrl!==null) {
      try{urlRef.revokeObjectURL(objectUrl);}catch{}
    }
  }
}
