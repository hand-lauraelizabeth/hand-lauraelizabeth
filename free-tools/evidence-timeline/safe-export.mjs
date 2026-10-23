/* Conservative, browser-local spreadsheet export gate. Preserve evidence in JSON. */
import {exportEvidenceCSV} from './core.mjs';
const columns=['sourceId','date','claim','status','kind','group'];
const hidden=/[\u0000-\u001f\u007f-\u009f\u00ad\u034f\u061c\u180e\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb]/u;
const formula=/^[\p{White_Space}\u200b-\u200f\u2060\ufeff]*[=+@\-＝＋＠－]/u;
const boundary=/(?:[,;])[\p{White_Space}\u200b-\u200f\u2060\ufeff]*[=+@\-＝＋＠－]/u;
/** Return the first unsafe field, never the sensitive value itself. */
export function csvExportRisk(records){
  if(!Array.isArray(records)) return {field:'records',reason:'invalid input'};
  for(let i=0;i<records.length;i++){
    const record=records[i];
    if(!record||typeof record!=='object'||Array.isArray(record)) return {field:'records',reason:'invalid input'};
    for(const field of columns){
      const value=record[field];
      if(value!==undefined&&value!==null&&typeof value!=='string') return {field,reason:'invalid value'};
      const s=String(value??'');
      if(hidden.test(s)) return {field,reason:'control or invisible character'};
      if(formula.test(s)||boundary.test(s)) return {field,reason:'formula-like content'};
    }
  }
  return null;
}
export function exportSafeEvidenceCSV(records){
  const risk=csvExportRisk(records);
  if(risk) throw Error('CSV export blocked: '+risk.field+' contains '+risk.reason+'. Use exact JSON.');
  return exportEvidenceCSV(records);
}
