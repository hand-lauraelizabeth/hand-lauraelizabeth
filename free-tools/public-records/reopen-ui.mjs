import {readWorkspaceFile} from './import.mjs';
export function bindReopen(getState,setState,say) {
  const input=document.getElementById('open-json');
  let serial=0;
  const resetImportError=()=>{
    input.removeAttribute('aria-invalid');
    input.setAttribute('aria-describedby','import-help');
  };
  const reportImportError=message=>{
    say(message);
    input.setAttribute('aria-invalid','true');
    input.setAttribute('aria-describedby','import-help status');
    input.focus();
  };
  const cancelPending=()=>{
    if(input.getAttribute('aria-busy')!=='true')return;
    ++serial;
    input.value='';
    input.setAttribute('aria-busy','false');
    resetImportError();
    say('Workspace import canceled. Existing records were kept.');
  };
  input.addEventListener('cancel',cancelPending);
  input.addEventListener('change',async()=>{
    const file=input.files?.[0];
    if(!file){cancelPending();return;}
    const current=++serial;
    resetImportError();
    input.setAttribute('aria-busy','true');
    say('Reading saved workspace locally…');
    try {
      const records=await readWorkspaceFile(file);
      if(current!==serial || input.files?.[0]!==file)return;
      const existing=getState();
      if(existing.requests.length || existing.events.length){
        reportImportError('Import not applied: save your work and reopen this page to load another workspace.');
        return;
      }
      setState(records);
      say('Imported '+records.requests.length+' requests and '+records.events.length+' events from JSON.');
    }catch(error){
      if(current!==serial || input.files?.[0]!==file)return;
      reportImportError('Import rejected: '+error.message+'. Existing records were kept.');
    }finally {
      if(current===serial){
        input.value='';
        input.setAttribute('aria-busy','false');
      }
    }
  });
}
