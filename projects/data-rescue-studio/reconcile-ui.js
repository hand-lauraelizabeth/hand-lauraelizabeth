/* Local-only comparison UI for two CSV/TSV files. No network calls. */
(function (root) {
  'use strict';
  const $ = id => document.getElementById(id);
  const lib = root.DataRescue;
  const engine = root.DataRescueProvenance || root.DataReconcile;
  let first = null, second = null, firstName = '', secondName = '';
  let comparison = null, generation = 0, findingPage = 0, exactIdentifier = null;
  let findings = [];
  const FINDINGS_PAGE_SIZE = 30;
  const FINDING_FILTERS = Object.freeze({
    all: () => true,
    matches: row => row[0] === 'Match',
    ambiguous: row => row[0] === 'Ambiguous — not merged',
    unmatched: row => row[0] === 'First file only' || row[0] === 'Second file only',
    missing: row => row[0] === 'Missing first-file key' || row[0] === 'Missing second-file key'
  });
  const el = (tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  function message(text, error = false, uploadError = false) {
    const node = $('compareStatus');
    node.textContent = text;
    node.className = error ? 'error' : '';
    node.setAttribute('role', error ? 'alert' : 'status');
    node.setAttribute('aria-live', error ? 'assertive' : 'polite');
    // Only a failed secondary-file read marks the file control invalid.
    // Comparison and export errors must not mislabel a valid upload.
    if (uploadError) $('compareFile').setAttribute('aria-invalid', 'true');
    else $('compareFile').removeAttribute('aria-invalid');
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
    findings = [];
    findingPage = 0;
    exactIdentifier = null;
    $('compareIdentifier').value = '';
    $('compareIdentifier').disabled = true;
    $('compareIdentifierFind').disabled = true;
    $('compareIdentifierClear').disabled = true;
    $('compareFindingFilter').value = 'all';
    $('compareFindingFilter').disabled = true;
    $('comparePrev').disabled = true;
    $('compareNext').disabled = true;
    $('comparePageStatus').textContent = 'Compare files to inspect findings.';
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
      message('The second file is larger than 5 MB.', true, true); return;
    }
    if (!/\.(csv|tsv)$/i.test(file.name)) {
      message('Choose a second .csv or .tsv file.', true, true); return;
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
      message('Unable to read second file: ' + error.message, true, true);
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
  // Escape combining marks, invisible formatting, line breaks and literal backslashes so distinct
  // identifiers do not render as identical escape notation. Exports stay exact.
  function auditPreview(value) {
    // Preserve exact Unicode code-point preview semantics without allocating
    // an array for every code point of an untrusted multi-megabyte identifier.
    // This is code-point truncation, not grapheme-cluster segmentation.
    const first = [], last = [];
    let count = 0;
    for (const char of String(value)) {
      if (count < 96) first.push(char);
      else {
        if (last.length === 20) last.shift();
        last.push(char);
      }
      count++;
    }
    const omitted = Math.max(0, count - 116);
    const shown = first.concat(last);
    const visible = shown.map(char => {
      const code = char.codePointAt(0);
      if (char === '\\') return '\\\\';
      if (char === '\n') return '\\n';
      if (char === '\r') return '\\r';
      if (char === '\t') return '\\t';
      if (code < 32 || (code >= 127 && code <= 159) ||
          (code !== 32 && /\p{White_Space}/u.test(char)) ||
          code === 0x2800 || // Braille Pattern Blank renders empty but is not White_Space.
          /\p{Default_Ignorable_Code_Point}/u.test(char) ||
          /\p{Mark}/u.test(char))
        return '\\u{' + code.toString(16).toUpperCase().padStart(4, '0') + '}';
      return char;
    });
    if (omitted) visible.splice(96, 0, ' … [' + omitted + ' code points omitted] … ');
    return visible.join('');
  }
  function visibleFindings() {
    const filter = $('compareFindingFilter').value;
    return findings.filter(row => (FINDING_FILTERS[filter] || FINDING_FILTERS.all)(row) &&
      (exactIdentifier === null || row[1] === exactIdentifier));
  }
  function renderFindingsPage() {
    if (!comparison) return;
    const filter = $('compareFindingFilter').value;
    const visible = visibleFindings();
    const total = visible.length;
    const allTotal = findings.length;
    const filterLabel = $('compareFindingFilter').selectedOptions?.[0]?.textContent || 'Selected';
    const maxPage = Math.max(0, Math.ceil(total / FINDINGS_PAGE_SIZE) - 1);
    findingPage = Math.min(Math.max(0, findingPage), maxPage);
    const start = findingPage * FINDINGS_PAGE_SIZE;
    const end = Math.min(start + FINDINGS_PAGE_SIZE, total);
    const table = el('table');
    table.append(el('caption', total
      ? 'Reconciliation findings ' + (start + 1) + '–' + end + ' of ' + total
      : 'No reconciliation findings'));
    const head = el('thead'), heading = el('tr');
    ['Classification', 'Identifier', 'First-file row(s)', 'Second-file row(s)'].forEach(text => {
      const cell = el('th', text);
      cell.scope = 'col';
      heading.append(cell);
    });
    head.append(heading); table.append(head);
    const body = el('tbody');
    visible.slice(start, end).forEach(record => {
      const line = el('tr');
      record.forEach((value, index) => {
        const cell = el(index === 0 ? 'th' : 'td', auditPreview(value));
        if (index === 0) cell.scope = 'row';
        line.append(cell);
      });
      body.append(line);
    });
    table.append(body);
    $('compareResults').replaceChildren(table);
    $('comparePrev').disabled = findingPage === 0;
    $('compareNext').disabled = findingPage >= maxPage;
    $('comparePageStatus').textContent = total
      ? 'Showing findings ' + (start + 1) + ' through ' + end + ' of ' + total +
        (filter === 'all' ? '' : ' in ' + filterLabel) +
        (exactIdentifier === null ? '' : ' for the exact identifier') +
        (filter === 'all' && exactIdentifier === null ? '' : ' (' + allTotal + ' findings overall)') +
        '. Downloads include every finding regardless of this preview filter or page.'
      : 'No ' + (filter === 'all' ? 'reconciliation' : filterLabel) +
        ' findings' + (exactIdentifier === null ? '' : ' for the exact identifier') +
        ' (' + allTotal + ' findings overall). Downloads retain the complete result.';
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
    findings = auditRows(result);
    findingPage = 0;
    $('compareFindingFilter').value = 'all';
    $('compareFindingFilter').disabled = false;
    exactIdentifier = null;
    $('compareIdentifier').value = '';
    $('compareIdentifier').disabled = false;
    $('compareIdentifierFind').disabled = false;
    $('compareIdentifierClear').disabled = false;
    renderFindingsPage();
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
  // Download initiation is not proof the browser saved a file.
  // Guard each comparison format and release temporary URLs on activation failure.
  function download(contents, filename, type, kind) {
    let url = null, link = null;
    try {
      url = URL.createObjectURL(new Blob([contents], {type}));
      link = el('a');
      link.href = url;
      link.download = filename;
      document.body.append(link);
      link.click();
    } catch {
      if (url) { try { URL.revokeObjectURL(url); } catch {} }
      message(kind + ' download could not be started. Both source files and the comparison remain loaded; retry or choose another format.', true);
      return false;
    } finally {
      if (link) link.remove();
    }
    try { setTimeout(() => { try { URL.revokeObjectURL(url); } catch {} }, 1000); } catch {}
    return true;
  }
  function exportAudit() {
    if (!comparison) return;
    try {
      // A reconciliation may have up to 100,000 unmatched findings from two
      // valid 50,000-row inputs. The shared CSV writer permits only 50,000
      // data rows; do not mistake this output limit for a corrupt source.
      const rows = auditRows(comparison).map(record => record.map(value =>
        Number.isSafeInteger(value) ? String(value) : value));
      if (rows.length > lib.MAX_ROWS) {
        message('Comparison CSV supports at most ' + lib.MAX_ROWS.toLocaleString('en-US') +
          ' findings; this comparison has ' + rows.length.toLocaleString('en-US') +
          '. No CSV was downloaded. Use exact comparison audit JSON or the value-free issue index.', true);
        return;
      }
      const headers = ['Classification', 'Identifier', 'First-file row(s)', 'Second-file row(s)'];
      const parsed = {headers, normalizedHeaders: headers, rows, warnings: [], delimiter: ','};
      // A validator failure must not bypass the spreadsheet formula check.
      // Keep the already loaded sources and both JSON alternatives available.
      const risk = lib.spreadsheetExportRisk(parsed);
      if (risk) {
        message('Comparison CSV blocked at audit record ' + risk.sourceRecord +
          ', column ' + risk.column + '. No CSV was downloaded. Use Export exact comparison audit JSON instead.', true);
        return;
      }
      if (!download(lib.exportCsvDownload(parsed, true), 'data-rescue-comparison-audit.csv',
        'text/csv;charset=utf-8', 'Comparison CSV')) return;
      message('Comparison CSV download started for ' + rows.length +
        ' findings. Contains identifier keys and source record positions, not full input records. Check your browser downloads and keep it private if identifiers are sensitive.');
    } catch {
      // Do not expose arbitrary parser/validator exception text or identifiers.
      message('Comparison CSV could not be prepared. No CSV was downloaded. Both source files remain loaded. Use exact comparison audit JSON or the value-free issue index.', true);
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
      if (!download(lib.requireJsonBudget(JSON.stringify(audit), 'Comparison audit'), 'data-rescue-comparison-audit.json', 'application/json;charset=utf-8', 'Comparison audit JSON')) return;
      message('Exact comparison audit JSON download started. Includes all findings and exact identifier keys, not complete input records. Check your browser downloads and keep it private if identifiers are sensitive.');
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
      if (!download(contents, 'data-rescue-reconciliation-issue-index.json', 'application/json;charset=utf-8', 'Reconciliation issue index')) return;
      message('Reconciliation issue index download started with source positions and categories only. No identifier keys, filenames or cell values. Check your browser downloads; linkage patterns may still be sensitive.');
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
  $('compareFindingFilter').addEventListener('change', () => {
    findingPage = 0;
    renderFindingsPage();
  });
  function findIdentifier() {
    if (!comparison) return;
    const value = $('compareIdentifier').value;
    if (!value) {
      $('comparePageStatus').textContent = 'Enter a nonempty identifier to search, or clear the identifier filter.';
      $('compareIdentifier').focus();
      return;
    }
    exactIdentifier = value;
    findingPage = 0;
    renderFindingsPage();
  }
  $('compareIdentifierFind').addEventListener('click', findIdentifier);
  $('compareIdentifier').addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); findIdentifier(); }
  });
  $('compareIdentifierClear').addEventListener('click', () => {
    if (!comparison) return;
    exactIdentifier = null;
    findingPage = 0;
    $('compareIdentifier').value = '';
    renderFindingsPage();
    $('compareIdentifier').focus();
  });
  $('comparePrev').addEventListener('click', () => {
    if (comparison && findingPage > 0) { findingPage--; renderFindingsPage(); }
  });
  $('compareNext').addEventListener('click', () => {
    if (comparison && (findingPage + 1) * FINDINGS_PAGE_SIZE < visibleFindings().length) {
      findingPage++; renderFindingsPage();
    }
  });
  root.DataRescueCompareUI = {setPrimary, previewText: auditPreview};
})(window);
