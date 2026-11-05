/** Initiate a browser-local download; never claim that the user saved it. */
export function startLocalDownload({data,filename,mime,documentRef=document,urlApi=URL,schedule=setTimeout}){
 let objectUrl=null,anchor=null;
 try{
  objectUrl=urlApi.createObjectURL(new Blob([data],{type:mime+';charset=utf-8'}));
  anchor=documentRef.createElement('a');
  anchor.href=objectUrl;anchor.download=filename;
  documentRef.body.append(anchor);
  anchor.click();
  schedule(()=>urlApi.revokeObjectURL(objectUrl),3000);
 }catch{
  if(objectUrl!==null){try{urlApi.revokeObjectURL(objectUrl);}catch{/* Browser cleanup unavailable. */}}
  // Never surface browser exception text: it may contain private paths or IDs.
  throw Error('The browser could not start this download. Your entries and evaluation are unchanged; try again.');
 }finally{
  if(anchor)anchor.remove();
 }
}
