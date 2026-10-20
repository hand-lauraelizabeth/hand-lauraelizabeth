/** Local-only confirmation gate for replacing an existing workspace. */
export function createReplacementGate(){
 let generation=0,staged=null;
 return {
  stage(workspace){
   if(!workspace||!Array.isArray(workspace.criteria)||!Array.isArray(workspace.vendors)||!Array.isArray(workspace.ratings))
    throw Error('Invalid replacement workspace.');
   // Freeze the preview boundary: later mutations to the caller-owned object
   // must never change what a user has approved for replacement.
   const snapshot=structuredClone(workspace);
   const token=++generation;
   staged={token,workspace:snapshot};
   return {token,counts:{criteria:snapshot.criteria.length,vendors:snapshot.vendors.length,ratings:snapshot.ratings.length}};
  },
  take(token){
   if(!staged||token!==generation||token!==staged.token)throw Error('The selected workspace is no longer current. Choose the file again.');
   const workspace=staged.workspace;
   staged=null;generation++;
   return workspace;
  },
  cancel(){staged=null;generation++;},
  hasPending(){return staged!==null;}
 };
}
