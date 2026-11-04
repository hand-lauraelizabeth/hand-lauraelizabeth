(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const candidate = byId('candidate');
  const job = byId('job');
  const zipInput = byId('career-zip');
  const areaSelect = byId('career-area');
  const results = byId('career-results');
  const status = byId('career-status');
  const output = byId('resume-output');
  const resumeStatus = byId('resume-status');
  const assets = window.roleEvidenceData;
  const cache = new Map();
  let matches = [];
  let serial = 0;
  let knownCandidate = candidate.value;

  const common = new Set(('about across additional analysis based business candidate company data demonstrated duties education employment excellent experience first good help high including internal job knowledge leadership manage management manager multiple organization people performance professional program project provide related report required requirements responsibility review role school services skills strong support system team tools use using work working years').split(' '));
  const tokenize = text => [...new Set((text.toLowerCase().match(/[a-z][a-z0-9+#.]{1,}/g) || [])
    .map(word => word.replace(/\.$/, ''))
    .filter(word => !common.has(word) && (word.length >= 3 || ['ai', 'hr', 'ux', 'it'].includes(word))))];
  const dollars = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 0});

  function load(name) {
    if (!cache.has(name)) {
      const request = fetch(assets[name], {credentials: 'omit', referrerPolicy: 'no-referrer'})
        .then(async response => {
          if (!response.ok) throw Error('Data source is unavailable.');
          const compressed = Uint8Array.from(atob((await response.text()).trim()), character => character.charCodeAt(0));
          const bytes = new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
          return new Response(bytes).json();
        }).catch(error => {
          cache.delete(name);
          throw error;
        });
      cache.set(name, request);
    }
    return cache.get(name);
  }

  function resumeLines(text) {
    const lines = text.split(/\r?\n/);
    const tagged = lines.some(line => /^\s*\[(resume|portfolio|public|document|user)\]\s*$/i.test(line));
    let include = !tagged;
    const selected = [];
    for (const line of lines) {
      const marker = line.trim().match(/^\[(resume|portfolio|public|document|user)\]$/i);
      if (marker) {
        include = marker[1].toLowerCase() === 'resume';
        if (include && selected.length) selected.push('');
      } else if (include) {
        selected.push(line);
      }
    }
    const normalized = value => value.toLowerCase().replace(/\s+/g, ' ').trim();
    const restricted = typeof GRAPH === 'undefined' ? [] : GRAPH
      .filter(node => ['private', 'anonymize', 'do-not-use'].includes(node.reviewed?.confidentiality))
      .map(node => normalized(node.statement)).filter(Boolean);
    return selected.filter(line => !restricted.some(statement => normalized(line).includes(statement)));
  }

  function rank(text, hint, catalog) {
    const tokens = new Set(tokenize(text));
    const focus = new Set(tokenize(hint));
    const normalized = ` ${hint.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()} `;
    return catalog.roles.map(role => {
      const [code, title, aliases, terms] = role;
      const matched = terms.filter(term => tokens.has(term));
      const inTitle = [...new Set(tokenize([title, ...aliases].join(' ')))].filter(term => tokens.has(term));
      if (new Set([...matched, ...inTitle]).size < 2) return null;
      const target = terms.filter(term => focus.has(term));
      const exact = hint && [title, ...aliases].some(label => {
        const phrase = label.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
        return phrase.length >= 5 && normalized.includes(` ${phrase} `);
      });
      const importance = term => catalog.weights[term] || 1;
      const score = matched.reduce((sum, term) => sum + importance(term), 0)
        + inTitle.reduce((sum, term) => sum + 1.25 * importance(term), 0)
        + 0.5 * target.length + (exact ? 15 : 0);
      return {code, title, score, evidence: [...new Set([...inTitle, ...matched])].slice(0, 8)};
    }).filter(Boolean).sort((a, b) => b.score - a.score || a.title.localeCompare(b.title)).slice(0, 8);
  }

  function element(tag, text, parent) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    parent.append(node);
    return node;
  }

  function render(wages, region, reason) {
    results.replaceChildren();
    const occupation = byId('resume-target');
    const previous = occupation.value;
    occupation.replaceChildren(new Option('Use posting or my target role, if supplied', ''));
    for (const match of matches) {
      occupation.add(new Option(match.title, match.title));
      const item = element('article', '', results);
      item.className = 'career-card';
      const title = element('h3', '', item);
      const link = element('a', match.title, title);
      link.href = `https://www.onetonline.org/link/summary/${match.code}`;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      element('p', `Résumé signals: ${match.evidence.join(', ')}.`, item);
      if (region) {
        const values = wages?.[match.code.slice(0, 7)];
        if (values?.every(Number.isFinite)) {
          const [low, median, high] = values;
          element('p', `${dollars.format(low)}–${dollars.format(high)} per year · median ${dollars.format(median)}`, item).className = 'career-pay';
          element('p', `${region} · BLS OEWS, May 2025 · 25th–75th percentile`, item).className = 'muted';
        } else {
          element('p', `${region} · annual percentiles unavailable for this occupation.`, item).className = 'muted';
        }
      } else if (reason) {
        element('p', reason, item).className = 'muted';
      }
    }
    if ([...occupation.options].some(option => option.value === previous)) occupation.value = previous;
  }

  async function addPay(run) {
    const zip = zipInput.value.trim();
    const selected = areaSelect.value;
    areaSelect.replaceChildren(new Option('Choose a labor market', ''));
    areaSelect.disabled = true;
    if (!zip) {
      render();
      status.textContent = 'Add a U.S. ZIP code to look up regional pay.';
      return;
    }
    if (!/^\d{5}(?:-\d{4})?$/.test(zip)) {
      render();
      status.textContent = 'Enter a five-digit ZIP code, such as 11432.';
      return;
    }
    status.textContent = 'Looking up the ZIP’s labor-market area…';
    const geography = await load('geography');
    if (run !== serial) return;
    const areas = geography.zips[zip.slice(0, 5)] || [];
    if (!areas.length) {
      render();
      status.textContent = 'No mapped labor-market area for this ZIP. Try a nearby work-location ZIP.';
      return;
    }
    for (const code of areas) areaSelect.add(new Option(geography.areas[code][0], code));
    const code = areas.length === 1 ? areas[0] : areas.includes(selected) ? selected : '';
    areaSelect.disabled = areas.length === 1;
    if (!code) {
      render();
      status.textContent = 'This ZIP overlaps multiple labor markets. Choose the work-location area below.';
      return;
    }
    areaSelect.value = code;
    const [name, asset] = geography.areas[code];
    status.textContent = `Loading May 2025 wages for ${name}…`;
    const wageData = await load(asset);
    if (run !== serial) return;
    render(wageData[code], name);
    status.textContent = `${matches.length} occupation leads · ${name}`;
  }

  async function findRoles() {
    const run = ++serial;
    const text = resumeLines(candidate.value).join('\n').trim();
    const hint = byId('career-focus').value.trim();
    matches = [];
    render();
    areaSelect.replaceChildren(new Option('Choose a labor market', ''));
    areaSelect.disabled = true;
    if (text.length < 30) {
      status.textContent = 'Paste a résumé or several lines of work and skills above first.';
      return;
    }
    const detected = readZipCodes(text);
    if (!zipInput.value.trim() && detected.size === 1) zipInput.value = [...detected][0];
    status.textContent = 'Finding occupations supported by your résumé…';
    try {
      const catalog = await load('occupations');
      if (run !== serial) return;
      matches = rank(text, hint, catalog);
      render();
      if (!matches.length) {
        status.textContent = 'No reliable leads from this text. Add specific duties, skills, or tools.';
        return;
      }
      await addPay(run);
    } catch (error) {
      if (run !== serial) return;
      status.textContent = matches.length ? 'Occupation matches are available. Pay data could not load; try again.' : 'The occupation catalog could not load. Try again.';
    }
  }

  const headings = /^(professional summary|summary|profile|experience|professional experience|work experience|employment history|education|skills|technical skills|core skills|certifications|licenses|projects|publications|awards|volunteer experience|leadership)\s*:?$/i;
  const bullet = /^\s*(?:[-–—*•▪]\s+|\d{1,2}[.)]\s+)/u;

  function createDraft(lines, target) {
    const keywords = new Set(tokenize(target));
    const score = line => tokenize(line).reduce((sum, word) => sum + Number(keywords.has(word)), 0);
    const normalized = lines.map(line => line.trim());
    const draft = [];
    let group = [];
    let experience = false;
    const flush = () => {
      group.sort((a, b) => score(b) - score(a));
      draft.push(...group);
      group = [];
    };
    for (const [index, line] of normalized.entries()) {
      const heading = line.match(headings);
      if (heading) {
        flush();
        experience = /experience|employment history/i.test(heading[1]);
        draft.push(heading[1].toUpperCase());
      } else if (experience && bullet.test(line)) {
        group.push(line.replace(bullet, '- '));
      } else if (experience && /^\s{2,}\S/.test(lines[index]) && group.length) {
        group[group.length - 1] += ' ' + line;
      } else {
        flush();
        draft.push(line);
      }
    }
    flush();
    return draft.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  function readZipCodes(text) {
    const codes = [...text.matchAll(/\bZIP(?:\s+code)?\s*[:=]?\s*(\d{5})(?:-\d{4})?\b/gi)];
    const addresses = [...text.matchAll(/\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|DC|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|PR)\s+(\d{5})(?:-\d{4})?\b/g)];
    return new Set([...codes, ...addresses].map(match => match[1]));
  }

  byId('career-run').addEventListener('click', findRoles);
  byId('analyze').addEventListener('click', () => { byId('career-evidence-tools').open = true; });
  byId('career-read-zip').addEventListener('click', () => {
    const found = readZipCodes(resumeLines(candidate.value).join('\n'));
    if (found.size !== 1) {
      status.textContent = found.size ? 'Multiple ZIP codes found. Enter the ZIP where you want to work.' : 'No unambiguous ZIP found. Enter a five-digit work-location ZIP if desired.';
      return;
    }
    zipInput.value = [...found][0];
    zipInput.dispatchEvent(new Event('input'));
    status.textContent = 'ZIP copied from the résumé. Confirm it is the location where you want to work.';
    zipInput.focus();
  });
  byId('career-file').addEventListener('change', async event => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!/\.txt$/i.test(file.name) || file.size > 512000) {
      byId('career-input-status').textContent = 'Choose a .txt file smaller than 512 KB.';
      return;
    }
    const before = candidate.value;
    try {
      const text = await file.text();
      if (candidate.value !== before) throw Error('Résumé text changed while the file was opening. Try again.');
      if (!text.trim() || text.includes('\u0000')) throw Error('This file does not contain readable plain text.');
      if (before.trim() && !confirm('Replace the existing evidence with this résumé file?')) return;
      candidate.value = text;
      candidate.dispatchEvent(new Event('input'));
      byId('career-input-status').textContent = 'Résumé loaded in this browser tab.';
      candidate.focus();
    } catch (error) { byId('career-input-status').textContent = error.message; }
  });
  areaSelect.addEventListener('change', async () => {
    const run = ++serial;
    try { await addPay(run); }
    catch (error) { if (run === serial) status.textContent = 'Regional wage data could not load. Try again.'; }
  });
  [candidate, zipInput, byId('career-focus')].forEach(input => input.addEventListener('input', () => {
    knownCandidate = candidate.value;
    ++serial;
    matches = [];
    areaSelect.replaceChildren(new Option('Choose a labor market', ''));
    areaSelect.disabled = true;
    render();
    status.textContent = 'Inputs changed. Run the occupation search to refresh results.';
    if (input === candidate && output.value) {
      byId('resume-copy').disabled = byId('resume-download').disabled = true;
      resumeStatus.textContent = 'Source text changed. Rebuild the draft to use its copy and download controls.';
    }
  }));
  const checkCandidateChange = () => {
    if (candidate.value !== knownCandidate) candidate.dispatchEvent(new Event('input'));
  };
  byId('sampleCandidate').addEventListener('click', checkCandidateChange);
  new MutationObserver(checkCandidateChange).observe(byId('profileMsg'), {childList: true, subtree: true});
  byId('saveNode').addEventListener('click', () => {
    candidate.dispatchEvent(new Event('input'));
    if (output.value) resumeStatus.textContent = 'Evidence review changed. Rebuild to apply the latest disclosure choices.';
  });
  byId('resume-build').addEventListener('click', () => {
    const lines = resumeLines(candidate.value);
    if (lines.join('').trim().length < 30) {
      resumeStatus.textContent = 'Paste résumé text above first. For tagged evidence, include a [resume] section.';
      return;
    }
    if (output.value && !confirm('Replace the editable draft with a new version?')) return;
    const target = byId('resume-target').value || byId('career-focus').value || job.value;
    output.value = createDraft(lines, target);
    output.hidden = false;
    byId('resume-copy').disabled = byId('resume-download').disabled = false;
    resumeStatus.textContent = 'Draft ready. Review every line before submitting.';
    output.focus();
  });
  byId('resume-copy').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(output.value);
      resumeStatus.textContent = 'Draft copied.';
    } catch (error) {
      output.focus();
      output.select();
      resumeStatus.textContent = 'Draft selected. Use your device’s Copy command.';
    }
  });
  byId('resume-download').addEventListener('click', () => {
    const href = URL.createObjectURL(new Blob([output.value], {type: 'text/plain;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = href;
    link.download = 'resume-draft.txt';
    link.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
    resumeStatus.textContent = 'Download requested. Check your browser’s downloads.';
  });
  byId('career-example').addEventListener('click', () => {
    if ((candidate.value.trim() || job.value.trim()) && !confirm('Replace the current inputs with fictional examples?')) return;
    byId('sampleJob').click();
    candidate.value = 'Jordan Example\n\nEXPERIENCE\nLearning and Development Specialist | Example Organization | 2021–present\n- Facilitated onboarding workshops for new employees.\n- Designed training materials and learning objectives for instructor-led courses.\n- Analyzed survey feedback and evaluated training effectiveness.\n\nSKILLS\nInstructional design, training needs assessment, facilitation, evaluation, Excel.';
    candidate.dispatchEvent(new Event('input'));
    zipInput.value = '11432';
    byId('career-focus').value = 'Training and development specialist';
    status.textContent = 'Fictional résumé, job posting, and ZIP loaded.';
  });
})();
