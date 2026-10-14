import {exportCSV,exportJSON} from './core.mjs';
export function bindExports(getState,say){
  const save=(name,type,content)=>{
    const url=URL.createObjectURL(new Blob([content],{type}));
    const link=document.createElement('a');
    link.href=url;link.download=name;document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  document.getElementById('save-json').addEventListener('click',()=>{
    save('public-records-workspace.json','application/json',exportJSON(getState()));say('JSON downloaded.');
  });
  document.getElementById('save-csv').addEventListener('click',()=>{
    save('public-records-workspace.csv','text/csv;charset=utf-8',exportCSV(getState()));say('CSV downloaded.');
  });
}
