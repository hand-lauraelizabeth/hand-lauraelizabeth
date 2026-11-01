import {exportCSV,exportJSON} from './core.mjs';
export function bindExports(getState,say,countPendingCorrections=()=>0){
  const save=(name,type,content)=>{
    const url=URL.createObjectURL(new Blob([content],{type}));
    let link, started=false;
    try{
      // DOM creation/attachment may also fail after the object URL exists.
      link=document.createElement('a');
      link.href=url;link.download=name;document.body.append(link);link.click();
      started=true;
    }finally{
      link?.remove();
      // Revoke immediately when activation fails, including before a link exists.
      if(started) setTimeout(()=>URL.revokeObjectURL(url),1000);
      else URL.revokeObjectURL(url);
    }
  };
  const excludedWarning=()=>{
    const count=countPendingCorrections();
    return count>0
      ? ` Warning: ${count} unsaved correction${count===1?' was':'s were'} excluded. Save each correction and download again.`
      : '';
  };
  document.getElementById('save-json').addEventListener('click',()=>{
    try{
      save('public-records-workspace.json','application/json',exportJSON(getState()));
      say('JSON download started; confirm the file was saved by your browser.'+excludedWarning());
    }catch{
      // Do not echo browser exception details or private record values.
      say('JSON download could not start. Your saved records are unchanged. Try again or use another browser.');
    }
  });
  document.getElementById('save-csv').addEventListener('click',()=>{
    let csv;
    try{csv=exportCSV(getState());}
    catch(error){
      say('CSV unavailable: '+error.message+'; your data is unchanged. Use JSON to retain exact values.');
      return;
    }
    try{
      save('public-records-workspace.csv','text/csv;charset=utf-8',csv);
      say('CSV download started; confirm the file was saved by your browser.'+excludedWarning());
    }catch{
      say('CSV download could not start. Your saved records are unchanged. Try JSON or another browser.');
    }
  });
}
