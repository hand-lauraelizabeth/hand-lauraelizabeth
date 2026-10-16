import test from 'node:test';
import assert from 'node:assert/strict';
import {validateDataset, selectCells, visibleProblemSeries} from './model.mjs';
const base = () => ({dataset_id:'erm2-nwe9',source_sha256:'a'.repeat(64),rules:{display_minimum_cell_count:10},
  disclosure:{marginals_available:false},aggregates:[
    {month:'2026-09',borough:'QUEENS',agency:'DOT',problem:'Road',requests:30},
    {month:'2026-09',borough:'BRONX',agency:'DEP',problem:'Water',requests:20},
    {month:'2026-08',borough:'QUEENS',agency:'DOT',problem:'Road',requests:12}]});
test('valid disclosure-safe aggregate loads', () => assert.equal(validateDataset(base()).aggregates.length,3));
test('reject source record fields', () => {const d=base();d.aggregates[0].incident_address='private';assert.throws(()=>validateDataset(d),/Raw/);});
test('reject small cells', () => {const d=base();d.aggregates[0].requests=9;assert.throws(()=>validateDataset(d),/undersized/);});
test('reject unsafe closure partitions', () => {const d=base();d.aggregates[0].closed_with_valid_interval=25;assert.throws(()=>validateDataset(d),/Closure/);});
test('reject exact marginals', () => {const d=base();d.disclosure.marginals_available=true;assert.throws(()=>validateDataset(d),/Disclosure/);});
test('reject duplicate grains', () => {const d=base();d.aggregates.push({...d.aggregates[0]});assert.throws(()=>validateDataset(d),/Duplicate/);});
test('filter and sort by month, borough, agency, problem', () => {
  const c=selectCells(base().aggregates,{month:'2026-09',borough:'QUEENS',agency:'DOT',query:'roAd'});
  assert.equal(c.length,1);assert.equal(c[0].requests,30);
});
test('visible series derives from released cells only', () => {
  assert.deepEqual(visibleProblemSeries(base().aggregates),[['Road',42],['Water',20]]);
});
