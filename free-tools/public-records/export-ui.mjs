import {exportCSV,exportJSON} from './core.mjs';
export function bindExports(getState,say,countPendingCorrections=()=>0){
  const save=(name,type,content)=>{
    const url=URL.createObjectURL(new Blob([content],{type}));
    const link=document.createElement('a');
    try{
      link.href=url;link.download=name;document.body.append(link);link.click();
    }finally{
      // A blocked click must not leave a detached download link or live object URL.
      link.remove();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
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
      say('JSON downloaded.'+excludedWarning());
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
      say('CSV downloaded.'+excludedWarning());
    }catch{
      say('CSV download could not start. Your saved records are unchanged. Try JSON or another browser.');
    }
  });
}
