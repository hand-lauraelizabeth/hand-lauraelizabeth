import {normalizeEvidence,exportEvidenceCSV} from './core.mjs';
const rows=normalizeEvidence([
  {sourceId:' ID, "one" ',date:'2026-10-16',claim:'Line one\nLine two',group:'＝group'},
  {sourceId:'cafe\u0301',date:'2026-10-15',claim:'＋SUM(1,2)',status:'disputed',kind:'inference'},
]);
process.stdout.write(exportEvidenceCSV(rows));
