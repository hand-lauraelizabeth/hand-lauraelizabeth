'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'college-program-search.js'), 'utf8');
const titles = JSON.parse(fs.readFileSync(path.join(root, 'data/programs/ipeds2025/cip2020-titles.json'), 'utf8'));
const editorial = JSON.parse(fs.readFileSync(path.join(root, 'data/programs/ipeds2025/program-search-terms.v1.json'), 'utf8')).terms_by_cip;
const start = source.indexOf('function normalize(v)');
const end = source.indexOf('function activeFilters()');
assert.ok(start >= 0 && end > start, 'Known source anchors are required');
const ranking = source.slice(start, end).replace(
  'var discoveryTerms={}; // editorial terms; no institutional admissions or licensing inference', ''
);
assert.ok(!ranking.includes('var discoveryTerms={}'), 'Editorial vocabulary must be injected');
const suggest = new Function(
  'titles', 'discoveryTerms', 'reportedCips', 'positiveCips', 'zeroOnlyCips', 'keys',
  'var collator=new Intl.Collator("en",{sensitivity:"base"});\n' + ranking + '\nreturn suggestFor;'
)(titles, editorial, new Set(), new Set(), new Set(), Object.keys(titles));

test('federal taxonomy and editorial coverage remain intact', () => {
  assert.equal(Object.keys(titles).length, 2325);
  assert.equal(Object.values(titles).filter(v => /^reserved\\.?$/i.test(v.trim())).length, 30);
  assert.equal(Object.keys(editorial).length, 88);
});
test('two-character common abbreviations do not match substrings', () => {
  for (const [term, count, cip] of [
    ['IT', 3, '110103'], ['AI', 1, '110102'], ['HR', 1, '521001'],
    ['PR', 1, '090902'], ['RN', 1, '513801']
  ]) {
    const result = suggest(term, 40);
    assert.equal(result.total, count, term);
    assert.equal(result.options[0].cip, cip, term);
  }
  assert.equal(suggest('nu', 40).total, 0);
});
test('longer subject searches and numeric prefixes retain expected coverage', () => {
  for (const [term, count] of [['UX', 2], ['coding', 5], ['nurse', 69], ['Biology', 52], ['12', 33]]) {
    assert.equal(suggest(term, 100).total, count, term);
  }
});
test('reserved CIP classifications are not suggested as fields of study', () => {
  assert.equal(suggest('Reserved', 100).total, 0);
  const numeric = suggest('12', 100);
  assert.ok(numeric.options.every(x => !x.reserved));
  const literal = suggest('CIP 12.0580', 40);
  assert.equal(literal.total, 1);
  assert.equal(literal.options[0].cip, '120580');
  assert.equal(literal.options[0].reserved, true);
  assert.match(source, /b\\.disabled=!!hit\\.reserved/);
});
test('search classifications do not imply current programs or licensure', () => {
  assert.match(source, /HISTORICAL completions index/);
  assert.match(source, /not a defined academic field/);
});
