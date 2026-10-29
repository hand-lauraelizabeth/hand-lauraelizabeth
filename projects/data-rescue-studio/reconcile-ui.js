/* Local-only comparison UI for two CSV/TSV files. No network calls. */
(function (root) {
  'use strict';
  const $ = id => document.getElementById(id);
  const lib = root.DataRescue;
  const engine = root.DataRescueProvenance || root.DataReconcile;
  let first = null, second = null, firstName = '', secondName = '';
  let comparison = null, generation = 0;
  const el = (tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  function message(text, error = false) {
    const node = $('compareStatus');
    node.textContent = text;
    node.className = error ? 'error' : '';
    node.setAttribute('role', error ? 'alert' : 'status');
    if (error) node.focus();
  }
  function options(selectId, data) {
    const select = $(selectId);
    select.replaceChildren();
    select.append(el('option', 'Select a column'));
    select.options[0].value = '';
    for (const name of (data ? data.normalizedHeaders : [])) {
      const opt = el('option', name);
      opt.value = name;
      select.append(opt);
    }
    select.disabled = !data;
  }
  function invalidate() {
    comparison = null;
    $('compareMetrics').replaceChildren();
    $('compareResults').replaceChildren();
    $('compareExport').disabled = true;
    $('compareJson').disabled = true;
    $('compareIndex').disabled = true;
    $('compareRun').disabled = !(first && second && $('leftKey').value && $('rightKey').value);
  }
  function setPrimary(data, name = '') {
    const priorKey = $('leftKey').value;
    // A new primary source invalidates every secondary selection and pending
    // secondary read, even when the replacement has identical column labels.
    ++generation;
    second = null;
    secondName = '';
    $('compareFile').value = '';
    options('rightKey', null);
    first = data;
    firstName = name;
    options('leftKey', data);
    if (data && priorKey && data.normalizedHeaders.includes(priorKey)) $('leftKey').value = priorKey;
    invalidate();
    message(data ? 'First file ready. Choose a second file and both identifier columns.' : 'Open a first file above to compare.');
  }
  function clearSecond() {
    generation++;
    second = null;
    secondName = '';
    $('compareFile').value = '';
    options('rightKey', null);
    invalidate();
    message(first ? 'Second file cleared. Choose a second CSV or TSV.' : 'Open a first file above to compare.');
  }
  async function loadSecond() {
    const file = $('compareFile').files && $('compareFile').files[0];
    const thisGeneration = ++generation;
    second = null;
    options('rightKey', null);
    invalidate();
    if (!file) { message('No second file selected.'); return; }
    if (file.size > lib.MAX_BYTES) {
      message('The second file is larger than 5 MB.', true); return;
    }
    if (!/\.(csv|tsv)$/i.test(file.name)) {
      message('Choose a second .csv or .tsv file.', true); return;
    }
    message('Reading second file locally…');
    try {
      // Never bypass byte-count and fatal UTF-8 validation if the shared
      // reader is missing or unavailable. A text() fallback can silently
      // replace malformed bytes and corrupt identifiers.
      if (!root.DataRescueFileReader || typeof root.DataRescueFileReader.read !== 'function')
        throw Error('Strict local file reader is unavailable. Reload this page before importing.');
      const parsed = await root.DataRescueFileReader.read(file, lib.parseDelimited);
      if (thisGeneration !== generation) return;
      second = parsed;
      secondName = file.name;
      options('rightKey', second);
      invalidate();
      message('Loaded second file: ' + second.rows.length + ' rows. No file was transmitted.');
    } catch (error) {
      if (thisGeneration !== generation) return;
      message('Unable to read second file: ' + error.message, true);
    }
  }
  function auditRows(result) {
    const records = [];
    const add = (kind, key, a, b) => records.push([kind, key, a, b]);
    result.matches.forEach(item => add('Match', item.key, item.leftRow, item.rightRow));
    result.ambiguous.forEach(item => add('Ambiguous — not merged', item.key, item.leftRows.join('; '), item.rightRows.join('; ')));
    result.leftOnly.forEach(item => add('First file only', item.key, item.row, ''));
    result.rightOnly.forEach(item => add('Second file only', item.key, '', item.row));
    result.missingLeft.forEach(row => add('Missing first-file key', '', row, ''));
    result.missingRight.forEach(row => add('Missing second-file key', '', '', row));
    return records;
  }
  // Bound DOM previews of untrusted identifiers without altering any audit export.
  // Escape invisible formatting and line breaks so readers can see what matched.
  function auditPreview(value) {
    const points = Array.from(String(value));
    const omitted = Math.max(0, points.length - 116);
    const shown = omitted ? [...points.slice(0, 96), ...points.slice(-20)] : points;
    const visible = shown.map(char => {
      const code = char.codePointAt(0);
      if (char === '\n') return '\\n';
      if (char === '\r') return '\\r';
      if (char === '\t') return '\\t';
      if (code < 32 || (code >= 127 && code <= 159) || /\p{Default_Ignorable_Code_Point}/u.test(char))
        return '\\u{' + code.toString(16).toUpperCase().padStart(4, '0') + '}';
      return char;
    });
    if (omitted) visible.splice(96, 0, ' … [' + omitted + ' code points omitted] … ');
    return visible.join('');
  }
  function render(result, coverage) {
    const categories = [
      ['One-to-one matches', result.matches.length],
      ['Ambiguous keys', result.ambiguous.length],
      ['First file only', result.leftOnly.length],
      ['Second file only', result.rightOnly.length],
      ['Missing identifiers', result.missingLeft.length + result.missingRight.length],
      ['First-file records classified', coverage.counts.firstRecords],
      ['Second-file records classified', coverage.counts.secondRecords],
      ['First-file records in ambiguous groups', coverage.firstAmbiguous],
      ['Second-file records in ambiguous groups', coverage.secondAmbiguous]
    ];
    const grid = $('compareMetrics');
    grid.replaceChildren();
    for (const [name, count] of categories) {
      const metric = el('div');
      metric.className = 'metric';
      metric.append(el('span', name), el('strong', count));
      grid.append(metric);
    }
    const rows = auditRows(result);
    const table = el('table');
    table.append(el('caption', 'First ' + Math.min(30, rows.length) + ' of ' + rows.length + ' reconciliation findings'));
    const head = el('thead'), heading = el('tr');
    ['Classification', 'Identifier', 'First-file row(s)', 'Second-file row(s)'].forEach(text => {const cell=el('th',text);cell.scope='col';heading.append(cell);});
    head.append(heading); table.append(head);
    const body = el('tbody');
    rows.slice(0, 30).forEach(record => {
      const line = el('tr');
      record.forEach((value,index) => {const cell=el(index===0?'th':'td',auditPreview(value));if(index===0)cell.scope='row';line.append(cell);});
      body.append(line);
    });
    table.append(body);
    $('compareResults').replaceChildren(table);
    $('compareExport').disabled = false;
    $('compareJson').disabled = false;
    $('compareIndex').disabled = false;
    message('Comparison complete: ' + result.matches.length + ' exact one-to-one matches; ' + result.ambiguous.length + ' ambiguous identifier groups. Classified ' + coverage.counts.firstRecords + ' of ' + first.rows.length + ' first-file records and ' + coverage.counts.secondRecords + ' of ' + second.rows.length + ' second-file records. Unmatched and missing-key records remain separate.');
  }
  // Use the same fail-closed source-position validator as the privacy-minimized
  // issue index. A successful-looking result is never shown or exported unless
  // every original logical record is classified exactly once.
  const positions = table => table.sourceRecords || table.sourceRowNumbers ||
    table.rows.map((_, index) => index + 2);
  function compare() {
    if (!(first && second && $('leftKey').value && $('rightKey').value)) return;
    try {
      if (!root.DataRescueComparisonIndex || typeof root.DataRescueComparisonIndex.create !== 'function')
        throw Error('The local reconciliation coverage validator is unavailable. Reload this page.');
      const candidate = (engine.compare || engine.reconcile)(first, second, $('leftKey').value, $('rightKey').value);
      const coverage = JSON.parse(root.DataRescueComparisonIndex.create(candidate, positions(first), positions(second)));
      const firstAmbiguous = coverage.findings.ambiguous.reduce((n, group) => n + group.firstSourceRecords.length, 0);
      const secondAmbiguous = coverage.findings.ambiguous.reduce((n, group) => n + group.secondSourceRecords.length, 0);
      comparison = candidate;
      render(candidate, {counts:coverage.counts, firstAmbiguous, secondAmbiguous});
    } catch (error) {
      invalidate();
      message('Unable to compare: ' + error.message, true);
    }
  }
  function download(contents, filename, type) {
    const url = URL.createObjectURL(new Blob([contents], {type}));
    const link = el('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function exportAudit() {
    if (!comparison) return;
    const rows = auditRows(comparison);
    const headers = ['Classification', 'Identifier', 'First-file row(s)', 'Second-file row(s)'];
    const parsed = {headers, normalizedHeaders: headers, rows, warnings: [], delimiter: ','};
    // Identifier keys are untrusted. Do not download a CSV when spreadsheet
    // import could reinterpret them; retain exact findings in the JSON option.
    const risk = lib.spreadsheetExportRisk(parsed);
    if (risk) {
      message('Comparison CSV blocked at audit record ' + risk.sourceRecord +
        ', column ' + risk.column + '. No CSV was downloaded. Use Export exact comparison audit JSON instead.', true);
      return;
    }
    try {
      download(lib.exportCsvDownload(parsed, true), 'data-rescue-comparison-audit.csv', 'text/csv;charset=utf-8');
      message('Exported ' + rows.length + ' findings. Contains identifier keys and source record positions, not full input records. Keep it private if identifiers are sensitive.');
    } catch (error) {
      message('Unable to export comparison CSV: ' + error.message + ' Use exact comparison audit JSON instead.', true);
    }
  }
  function exportAuditJson() {
    if (!comparison) return;
    // Preserve exact keys and numeric source-record arrays. No full source rows,
    // fabricated timestamps, remote requests, or spreadsheet-specific rewrites.
    const audit = {
      format: 'data-rescue-comparison-audit', schemaVersion: 1,
      source: {firstFileName: firstName, secondFileName: secondName,
        firstKey: $('leftKey').value, secondKey: $('rightKey').value,
        recordUnit: 'logical CSV/TSV record; header is record 1'},
      ...comparison
    };
    try {
      download(JSON.stringify(audit), 'data-rescue-comparison-audit.json', 'application/json;charset=utf-8');
      message('Exported exact comparison audit JSON. Includes all findings and exact identifier keys, not complete input records. Keep it private if identifiers are sensitive.');
    } catch (error) {
      message('Unable to export comparison audit JSON: ' + error.message, true);
    }
  }
  function exportIssueIndex() {
    if (!comparison) return;
    try {
      if (!root.DataRescueComparisonIndex || typeof root.DataRescueComparisonIndex.create !== 'function')
        throw Error('The local reconciliation index builder is unavailable. Reload this page.');
      const contents = root.DataRescueComparisonIndex.create(comparison, positions(first), positions(second));
      download(contents, 'data-rescue-reconciliation-issue-index.json', 'application/json;charset=utf-8');
      message('Exported reconciliation issue index with source positions and categories only. No identifier keys, filenames or cell values. Linkage patterns may still be sensitive; keep it private.');
    } catch (error) {
      message('Unable to export reconciliation issue index: ' + error.message, true);
    }
  }
  $('compareFile').addEventListener('change', loadSecond);
  $('compareClear').addEventListener('click', clearSecond);
  $('leftKey').addEventListener('change', invalidate);
  $('rightKey').addEventListener('change', invalidate);
  $('compareRun').addEventListener('click', compare);
  $('compareExport').addEventListener('click', exportAudit);
  $('compareJson').addEventListener('click', exportAuditJson);
  $('compareIndex').addEventListener('click', exportIssueIndex);
  root.DataRescueCompareUI = {setPrimary, previewText: auditPreview};
})(window);
