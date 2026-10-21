import {readWorkspaceFile} from './import.mjs';
export function bindReopen(getState,setState,say) {
  const input=document.getElementById('open-json');
  let serial=0;
  input.addEventListener('change',async()=>{
    const file=input.files?.[0];
    if(!file)return;
    const current=++serial;
    try {
      const records=await readWorkspaceFile(file);
      if(current!==serial || input.files?.[0]!==file)return;
      const existing=getState();
      if(existing.requests.length || existing.events.length){
        say('Import not applied: save your work and reopen this page to load another workspace.');
        return;
      }
      setState(records);
      say('Imported '+records.requests.length+' requests and '+records.events.length+' events from JSON.');
    }catch(error){
      if(current!==serial || input.files?.[0]!==file)return;
      say('Import rejected: '+error.message+'. Existing records were kept.');
    }finally {
      if(current===serial)input.value='';
    }
  });
}
