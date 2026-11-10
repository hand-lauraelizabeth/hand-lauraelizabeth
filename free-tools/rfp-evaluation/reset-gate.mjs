/** Browser-local confirmation token for discarding unsaved entries. */
export function createResetGate(){
 let generation=0,pending=null;
 return {
  stage(counts){
   if(!counts || typeof counts!=='object' || !['criterion','vendor','rating'].every(key=>Number.isSafeInteger(counts[key])&&counts[key]>=0))
    throw Error('Invalid entry counts.');
   const snapshot={criterion:counts.criterion,vendor:counts.vendor,rating:counts.rating};
   const total=snapshot.criterion+snapshot.vendor+snapshot.rating;
   if(!Number.isSafeInteger(total)) throw Error('Invalid entry counts: total exceeds the safe integer range.');
   const token=++generation;
   pending={token,counts:snapshot};
   return {token,total};
  },
  take(token){
   if(!pending || token!==generation || token!==pending.token)
    throw Error('The clear confirmation is no longer current. Review the entries again.');
   const counts={...pending.counts};pending=null;generation++;
   return counts;
  },
  cancel(){pending=null;generation++;},
  hasPending(){return pending!==null;}
 };
}
