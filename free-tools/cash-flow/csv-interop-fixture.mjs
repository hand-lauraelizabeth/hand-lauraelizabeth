// Synthetic CSV export fixture for independently parsed interoperability testing.
import {project,exportCSV,addDays} from './engine.mjs';
const labels=[
  '=HYPERLINK("https://example.invalid","click")',
  '+SUM(1,2)',
  '-cmd|whoami',
  '@SUM(1,2)',
  '\t=1+1',
  '   =SUM(5,6)',
  '\r\n=2+2',
  'Quoted "value", comma',
  'Multiline\nstatement',
  'Résumé — ñ and €',
];
const events=labels.map((label,i)=>({
  id:i===0?'=unsafe-id':'event-'+i,
  label,
  date:addDays('2026-10-14',i),
  repeat:'once',
  cents:i%2===0?-12345:10001,
}));
const result=project({
  start:'2026-10-14',end:'2026-10-23',
  openingCents:1000000,events
});
process.stdout.write(exportCSV(result));
