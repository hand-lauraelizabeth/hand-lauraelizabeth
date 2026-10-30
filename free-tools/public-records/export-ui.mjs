import {exportCSV,exportJSON} from './core.mjs';
export function bindExports(getState,say,countPendingCorrections=()=>0){
  const save=(name,type,content)=>{
    const url=URL.createObjectURL(new Blob([content],{type}));
    const link=document.createElement('a');
    link.href=url;link.download=name;document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  const excludedWarning=()=>{
    const count=countPendingCorrections();
    return count>0
      ? ` Warning: ${count} unsaved correction${count===1?' was':'s were'} excluded. Save each correction and download again.`
      : '';
  };
  document.getElementById('save-json').addEventListener('click',()=>{
    save('public-records-workspace.json','application/json',exportJSON(getState()));say('JSON downloaded.'+excludedWarning());
  });
  document.getElementById('save-csv').addEventListener('click',()=>{
    try {save('public-records-workspace.csv','text/csv;charset=utf-8',exportCSV(getState()));say('CSV downloaded.'+excludedWarning());}
    catch(error){say('CSV unavailable: '+error.message+'; your data is unchanged. Use JSON to retain exact values.');}
  });
}
