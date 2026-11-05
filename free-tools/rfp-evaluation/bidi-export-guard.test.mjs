import assert from 'node:assert/strict';
import test from 'node:test';
import {evaluateMatrix, exportMatrixCSV, exportEvidenceCSV, exportMatrixJSON} from './core.mjs';
import {evaluateWithProvenance, exportEvidenceCoverageCSV} from './evidence-coverage.mjs';

// Synthetic identifiers only. The JSON export retains original bytes/code points;
// spreadsheet CSV is deliberately unavailable for directional-control content.
const base = () => ({
  criteria: [{id:'C-0001',label:'Delivery',weight:100,mandatory:true,sourceRef:'REQ-0001'}],
  vendors: [{id:'V-0007',name:'Example vendor',conflict:'none',price:'10.00'}],
  ratings: [{vendorId:'V-0007',criterionId:'C-0001',score:4,evidenceRef:'EV-0001',note:'Reviewed',reviewer:'QA'}]
});
const controls = [0x061C,0x200E,0x200F,0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069];
test('all directional formatting controls fail closed in each spreadsheet export', () => {
  for(const cp of controls){
    const mark=String.fromCodePoint(cp);
    const vendor=base();
    vendor.vendors[0].name='Example'+mark+' vendor';
    assert.throws(()=>exportMatrixCSV(evaluateMatrix(vendor)),/CSV export blocked/, 'matrix U+'+cp.toString(16));
    const evidence=base();
    evidence.ratings[0].note='Reviewed'+mark+' text';
    assert.throws(()=>exportEvidenceCSV(evaluateMatrix(evidence)),/CSV export blocked/, 'ratings U+'+cp.toString(16));
    assert.throws(()=>exportEvidenceCoverageCSV(evaluateWithProvenance(evidence)),/CSV export blocked/, 'coverage U+'+cp.toString(16));
    const exact=exportMatrixJSON(evaluateMatrix(evidence));
    assert.ok(exact.includes(mark), 'JSON must retain original U+'+cp.toString(16));
  }
});
test('benign multilingual, zero-padded source identifiers and exact JSON remain usable', () => {
  const input=base();
  input.vendors[0].name='供應商 – Café';
  input.ratings[0].evidenceRef='EV-0001';
  const result=evaluateWithProvenance(input);
  assert.equal(result.vendors[0].id,'V-0007');
  assert.equal(result.criteria[0].sourceRef,'REQ-0001');
  assert.match(exportMatrixCSV(result),/"V-0007"/);
  assert.match(exportEvidenceCSV(result),/"EV-0001"/);
  assert.match(exportEvidenceCoverageCSV(result),/"REQ-0001"/);
  assert.equal(JSON.parse(exportMatrixJSON(result)).vendors[0].name,'供應商 – Café');
});
test('NFKC formula variants remain blocked without silently altering JSON', () => {
  for(const value of ['＝1+2','＋SUM(1,2)','＠cmd','-1+2','x,=1+2']){
    const input=base();
    input.ratings[0].note=value;
    const result=evaluateMatrix(input);
    assert.throws(()=>exportEvidenceCSV(result),/CSV export blocked/);
    assert.equal(JSON.parse(exportMatrixJSON(result)).ratings[0].note,value);
  }
});
