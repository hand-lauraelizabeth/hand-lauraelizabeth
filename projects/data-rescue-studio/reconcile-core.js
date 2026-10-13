/* Exact-key, browser-local CSV reconciliation. No automatic merges. */
(function(root,factory){
 const api=factory();
 if(typeof module!=='undefined' && module.exports) module.exports=api;
 if(root) root.DataReconcile=api;
})(typeof window!=='undefined'?window:null,function(){
'use strict';
function reconcile(left,right,leftKey,rightKey){
 const l=left.normalizedHeaders.indexOf(leftKey),r=right.normalizedHeaders.indexOf(rightKey);
 if(l<0||r<0)throw Error('Choose a valid key column in both tables.');
 const index=(table,col)=>{
  const out=new Map(),missing=[];
  table.rows.forEach((row,i)=>{
   const key=row[col];
   if(!key||!key.trim()){missing.push(i+2);return;}
   if(!out.has(key))out.set(key,[]);
   out.get(key).push(i+2);
  });
  return {out,missing};
 };
 const a=index(left,l),b=index(right,r);
 const matches=[],ambiguous=[],leftOnly=[],rightOnly=[];
 for(const key of new Set([...a.out.keys(),...b.out.keys()])){
  const x=a.out.get(key)||[],y=b.out.get(key)||[];
  if(x.length>1||y.length>1)ambiguous.push({key,leftRows:x,rightRows:y});
  else if(x.length&&y.length)matches.push({key,leftRow:x[0],rightRow:y[0]});
  else if(x.length)leftOnly.push({key,row:x[0]});
  else rightOnly.push({key,row:y[0]});
 }
 return {matches,ambiguous,leftOnly,rightOnly,missingLeft:a.missing,missingRight:b.missing};
}
return {reconcile};
});
