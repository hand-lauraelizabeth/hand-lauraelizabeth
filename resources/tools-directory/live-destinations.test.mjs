import assert from 'node:assert/strict';
import { TOOLS } from './catalog.mjs';
import { validateCatalog, filterTools } from './directory.mjs';

// Public navigation contracts: intentionally deterministic and network-independent.
// Live HTTP reachability is checked separately; this test does not imply it.
const expected = new Map([
  ['text-lens', '/resources/research-writing-tools/text-lens/'],
  ['prompt-lab', '/resources/learning-curriculum-tools/prompt-lab/'],
  ['ai-use', '/resources/learning-curriculum-tools/ai-use-decision-lab/'],
  ['nlp-lesson', '/resources/learning-curriculum-tools/teaching-nlp-with-python/'],
  ['stats-lesson', '/resources/learning-curriculum-tools/teaching-statistics-with-r/'],
  ['reverse-ats', '/resources/career-professional-development-tools/reverse-ats/'],
]);
let checks = 0;
function check(value, label) { assert.ok(value, label); checks++; }
function rejects(rows, label) { assert.throws(() => validateCatalog(rows), label); checks++; }
function verifyDestinations(rows) {
  for (const [id, path] of expected) {
    const tool = rows.find(tool => tool.id === id);
    assert.equal(tool?.status, 'live', `live status ${id}`);
    assert.equal(tool?.url, `https://www.lauraelizabethhand.com${path}`, `destination ${id}`);
  }
}
function mutated(id, changes) {
  return TOOLS.map(tool => tool.id === id ? {...tool, ...changes} : {...tool});
}

check(validateCatalog(TOOLS) === true, 'catalog valid');
verifyDestinations(TOOLS); checks += expected.size * 2;
check(TOOLS.length === 17, 'catalog count');
check(new Set(TOOLS.map(tool => tool.id)).size === TOOLS.length, 'IDs unique');
const live = TOOLS.filter(tool => tool.status === 'live');
const development = TOOLS.filter(tool => tool.status === 'development');
check(live.length === expected.size, 'live count');
check(development.length === 11, 'development count');
check(TOOLS.every(tool => tool.status !== 'preview'), 'no unverified preview');
check(development.every(tool => !Object.hasOwn(tool, 'url')), 'no unreleased links');
for (const [id, path] of expected) {
  const tool = live.find(tool => tool.id === id);
  check(!!tool, `live ID ${id}`);
  check(tool?.url === `https://www.lauraelizabethhand.com${path}`, `exact destination ${id}`);
  check(filterTools(TOOLS, {status:'live'}).some(tool => tool.id === id), `live filter includes ${id}`);
  rejects(mutated(id, {url:`https://www.lauraelizabethhand.com:8443${path}`}), `nondefault port ${id}`);
  rejects(mutated(id, {url:`https://www.lauraelizabethhand.com/resources/${id}/?redirect=1`}), `query parameter ${id}`);
  rejects(mutated(id, {url:`https://untrusted.example${path}`}), `foreign origin ${id}`);
  rejects(mutated(id, {url:undefined}), `missing live link ${id}`);
  // A valid but incorrect internal path must be caught by the destination contract.
  const changed = mutated(id, {url:'https://www.lauraelizabethhand.com/resources/wrong/'});
  assert.throws(() => verifyDestinations(changed), `wrong internal path ${id}`); checks++;
}
for (const tool of development) {
  rejects(mutated(tool.id, {url:'https://www.lauraelizabethhand.com/resources/not-launched/'}), `no development link ${tool.id}`);
}
check(filterTools(TOOLS, {status:'development'}).length === 11, 'development filter');
check(filterTools(TOOLS, {status:'live'}).length === 6, 'live filter');
console.log(`FT-15 deterministic live-destination contract: ${checks}/${checks} PASS`);
