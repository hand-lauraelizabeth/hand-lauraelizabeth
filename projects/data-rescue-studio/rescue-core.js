/* Data Rescue Studio — browser-local CSV/TSV utilities. No third-party dependencies. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.DataRescue = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const MAX_BYTES = 5_000_000;
  const MAX_ROWS = 50_000;
  const MAX_COLUMNS = 100;

  function detectDelimiter(text) {
    let quote = false, commas = 0, tabs = 0;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '"') {
        if (quote && text[i+1] === '"') { i++; continue; }
        quote = !quote;
      } else if (!quote) {
        if (c === '\n' || c === '\r') break;
        if (c === ',') commas++;
        if (c === '\t') tabs++;
      }
    }
    return tabs > commas ? '\t' : ',';
  }

  function parseDelimited(text, delimiter) {
    if (typeof text !== 'string') throw new Error('Input must be text.');
    if (text.length > MAX_BYTES) throw new Error('File exceeds the 5 MB text limit.');
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
    if (!text.trim()) throw new Error('File contains no data.');
    const sep = delimiter || detectDelimiter(text);
    if (sep !== ',' && sep !== '\t') throw new Error('Only CSV and TSV are supported.');
    const records = []; let row = [], field = '', state = 'start';
    function pushField() { row.push(field); field = ''; state = 'start'; }
    function pushRow() {
      pushField();
      if (row.length > MAX_COLUMNS) throw new Error('More than 100 columns are not supported.');
      records.push(row); row = [];
      if (records.length > MAX_ROWS + 1) throw new Error('More than 50,000 data rows are not supported.');
    }
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (state === 'quoted') {
        if (c === '"') {
          if (text[i+1] === '"') { field += '"'; i++; }
          else state = 'afterQuote';
        } else {
          // Quoted CRLF, lone CR and LF are cell data, not record boundaries.
          // Preserve their exact decoded characters for evidence and round-trips.
          field += c;
        }
      } else if (c === sep) pushField();
      else if (c === '\n' || c === '\r') {
        pushRow();
        if (c === '\r' && text[i+1] === '\n') i++;
      } else if (state === 'start' && c === '"') state = 'quoted';
      else if (state === 'afterQuote' && (c === ' ' || c === '\t') && sep !== '\t') {
        // Tolerate whitespace between a quoted cell and its separator.
      } else if (state === 'afterQuote') throw new Error('Unexpected text after a closing quote near character ' + (i+1) + '.');
      else if (c === '"') throw new Error('Unexpected quote near character ' + (i+1) + '.');
      else { field += c; state = 'unquoted'; }
    }
    if (state === 'quoted') throw new Error('Unclosed quoted field.');
    if (row.length || field !== '' || state !== 'start') pushRow();
    if (!records.length) throw new Error('No header row found.');
    const headers = records.shift();
    if (headers.length > MAX_COLUMNS) throw new Error('More than 100 columns are not supported.');
    const normalizedHeaders = [];
    const seen = new Map(), used = new Set();
    const warnings = [];
    for (let i = 0; i < headers.length; i++) {
      const base = headers[i].trim() || ('Column ' + (i+1));
      const id = base.toLowerCase();
      const count = (seen.get(id) || 0) + 1; seen.set(id, count);
      // A literal header such as "ID (2)" can collide with the generated
      // label for a second "ID" column. Reconciliation uses these labels
      // as keys, so each displayed choice must identify exactly one column.
      let suffix = count;
      let label = count === 1 ? base : base + ' (' + suffix + ')';
      while (used.has(label.toLowerCase())) {
        suffix = Math.max(2, suffix + 1);
        label = base + ' (' + suffix + ')';
      }
      used.add(label.toLowerCase());
      normalizedHeaders.push(label);
      if (!headers[i].trim()) warnings.push('Column ' + (i+1) + ' has a blank header.');
      if (count > 1) warnings.push('Repeated header: ' + base + '.');
      else if (label !== base) warnings.push('Column ' + (i+1) + ' was labeled "' + label + '" to distinguish it from another column.');
    }
    const data = [];
    for (let i = 0; i < records.length; i++) {
      if (records[i].length !== headers.length) throw new Error('Row ' + (i+2) + ' has ' + records[i].length + ' columns; expected ' + headers.length + '. No data was discarded.');
      data.push(records[i]);
    }
    return { headers, normalizedHeaders, rows: data, warnings, delimiter: sep };
  }

  function summarize(parsed) {
    const {rows, normalizedHeaders: headers} = parsed;
    const counts = headers.map((name, column) => {
      const values = rows.map(r => r[column]);
      return {name, blank: values.filter(v => v.trim() === '').length,
        unique: new Set(values).size, total: values.length};
    });
    const seen = new Map(), duplicateRows = [];
    rows.forEach((row, i) => {
      const key = JSON.stringify(row);
      if (seen.has(key)) duplicateRows.push({row: i + 2, firstSeen: seen.get(key) + 2});
      else seen.set(key, i);
    });
    return {rowCount: rows.length, columnCount: headers.length, columns: counts, duplicateRows};
  }

  function withoutExactDuplicates(parsed) {
    const seen = new Set(), rows = [], sourceRecords = [];
    parsed.rows.forEach((row, index) => {
      const key = JSON.stringify(row);
      if (seen.has(key)) return;
      seen.add(key);
      rows.push(row);
      sourceRecords.push(parsed.sourceRecords ? parsed.sourceRecords[index] : index + 2);
    });
    // Retained records keep their ORIGINAL logical positions after deduplication.
    // The unmodified source remains available separately for exact JSON export.
    return {...parsed, rows, sourceRecords,
      originalRowCount: parsed.originalRowCount ?? parsed.rows.length};
  }

  // Read-only review filters: original logical source records are never renumbered.
  // Filtering the preview does not filter CSV or JSON exports.
  function inspectSourceRecords(parsed, mode = 'all', limit = 20, offset = 0) {
    if (!parsed || !Array.isArray(parsed.rows) ||
        !['all', 'missing', 'duplicates'].includes(mode) ||
        !Number.isSafeInteger(limit) || limit < 1 || limit > 100 ||
        !Number.isSafeInteger(offset) || offset < 0)
      throw new Error('Choose a valid source-record review filter.');
    const seen = new Map(), entries = [];
    let total = 0;
    parsed.rows.forEach((row, index) => {
      const sourceRecord = parsed.sourceRecords ? parsed.sourceRecords[index] : index + 2;
      const signature = JSON.stringify(row);
      const duplicateOf = seen.has(signature) ? seen.get(signature) : null;
      if (!seen.has(signature)) seen.set(signature, sourceRecord);
      const missing = row.some(value => value.trim() === '');
      if (mode !== 'all' && !(mode === 'missing' ? missing : duplicateOf !== null)) return;
      total++;
      if (total > offset && entries.length < limit) entries.push({
        sourceRecord, duplicateOf, values: row.slice()
      });
    });
    return {mode, total, offset, shown: entries.length, entries};
  }

  // Locate an original logical source record within the active preview filter.
  // Returns its zero-based position among matching records, or null when absent
  // or excluded. No values are normalized or copied into an index.
  function findSourceRecordOffset(parsed, mode, target) {
    if (!parsed || !Array.isArray(parsed.rows) ||
        !['all', 'missing', 'duplicates'].includes(mode) ||
        !Number.isSafeInteger(target) || target < 2 || target > MAX_ROWS + 1)
      throw new Error('Enter a valid original source-record number.');
    const seen = new Set();
    let matchingOffset = 0;
    for (let i = 0; i < parsed.rows.length; i++) {
      const row = parsed.rows[i];
      const signature = JSON.stringify(row);
      const duplicate = seen.has(signature);
      seen.add(signature);
      const included = mode === 'all' ||
        (mode === 'missing' && row.some(value => value.trim() === '')) ||
        (mode === 'duplicates' && duplicate);
      const sourceRecord = parsed.sourceRecords ? parsed.sourceRecords[i] : i + 2;
      if (sourceRecord === target) return included ? matchingOffset : null;
      if (included) matchingOffset++;
    }
    return null;
  }

  function formulaRisk(value) {
    return /^[\s\uFEFF]*[=+\-@\uFF1D\uFF0B\uFF0D\uFF20]/u.test(String(value));
  }

  // Spreadsheet importers can reinterpret line breaks and invisible controls.
  // Refuse ambiguous spreadsheet-view exports, but preserve exact cells in JSON
  // and in the explicitly machine-readable CSV option.
  function spreadsheetExportRisk(parsed) {
    for (const [rowIndex, row] of [parsed.headers, ...parsed.rows].entries()) {
      for (const [columnIndex, value] of row.entries()) {
        const text = String(value);
        // Unicode LS/PS may become new rows or visible line breaks on import.
        // Their spreadsheet behavior is not consistent enough to promise safe CSV.
        // Keep them unchanged in exact machine CSV and evidence JSON instead.
        if (/[\u2028\u2029]/u.test(text) ||
            /^[\p{White_Space}\p{Default_Ignorable_Code_Point}]*\t[\p{White_Space}\p{Default_Ignorable_Code_Point}]*[=+\-@＝＋－＠]/u.test(text) ||
            /^[\t\r\n]/u.test(text) ||
            /[\r\n][\p{White_Space}\p{Default_Ignorable_Code_Point}]*[=+\-@＝＋－＠]/u.test(text) ||
            /[\u202A-\u202E\u2066-\u2069]/u.test(text) ||
            /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/u.test(text) ||
            /^[\p{White_Space}\p{Default_Ignorable_Code_Point}]*[=+\-@＝＋－＠]/u.test(text) &&
              !formulaRisk(text)) {
          return {sourceRecord:rowIndex === 0 ? 1 :
            (parsed.sourceRecords ? parsed.sourceRecords[rowIndex - 1] : rowIndex + 1),
            column:columnIndex + 1};
        }
      }
    }
    return null;
  }

  function exportCsv(parsed, spreadsheetView = true) {
    const risk = spreadsheetView ? spreadsheetExportRisk(parsed) : null;
    if (risk) throw new Error('Spreadsheet CSV blocked at source record ' + risk.sourceRecord + ', column ' + risk.column + '. Use exact JSON, or machine CSV only outside spreadsheet software.');
    const write = v => {
      let s = String(v);
      // Spreadsheet-oriented mode adds a leading tab *inside* a quoted cell.
      // This may alter exported data; machine-readable users should disable it.
      if (spreadsheetView && formulaRisk(s)) s = '\t' + s;
      return '"' + s.replace(/"/g, '""') + '"';
    };
    return [parsed.headers, ...parsed.rows].map(row => row.map(write).join(',')).join('\r\n');
  }

  // Spreadsheet download adds a UTF-8 BOM for Excel's direct-open behavior.
  // Machine-readable CSV remains BOM-free and preserves unmodified cells.
  function exportCsvDownload(parsed, spreadsheetView = true) {
    const csv = exportCsv(parsed, spreadsheetView);
    return spreadsheetView ? '\uFEFF' + csv : csv;
  }

  // Exact decoded cells and logical source record positions, without CSV formula rewriting.
  // This is not a byte-for-byte copy or a cryptographic authenticity record.
  function exportEvidenceJson(parsed, sourceFileName = '', provenance = null) {
    if (!parsed || !Array.isArray(parsed.headers) || !Array.isArray(parsed.rows) ||
        !Array.isArray(parsed.normalizedHeaders) || !Array.isArray(parsed.warnings) ||
        (parsed.delimiter !== ',' && parsed.delimiter !== '\t') ||
        typeof sourceFileName !== 'string')
      throw new Error('A parsed CSV or TSV and its source filename are required.');
    const width = parsed.headers.length;
    if (width < 1 || width > MAX_COLUMNS || parsed.normalizedHeaders.length !== width ||
        parsed.rows.length > MAX_ROWS ||
        !parsed.headers.every(v => typeof v === 'string') ||
        !parsed.normalizedHeaders.every(v => typeof v === 'string') ||
        !parsed.warnings.every(v => typeof v === 'string') ||
        !parsed.rows.every(row => Array.isArray(row) && row.length === width &&
          row.every(v => typeof v === 'string')))
      throw new Error('Cannot export an incomplete or inconsistent evidence table.');
    // If a filtered view is exported, retain original logical record positions.
    // Reject malformed provenance rather than silently renumbering source records.
    if (parsed.sourceRecords !== undefined && (
        !Array.isArray(parsed.sourceRecords) ||
        parsed.sourceRecords.length !== parsed.rows.length ||
        !parsed.sourceRecords.every((n, i) =>
          Number.isSafeInteger(n) && n >= 2 && n <= MAX_ROWS + 1 &&
          (i === 0 || n > parsed.sourceRecords[i - 1]))))
      throw new Error('Invalid source-record positions in evidence table.');
    if (parsed.originalRowCount !== undefined && (
        !Number.isSafeInteger(parsed.originalRowCount) ||
        parsed.originalRowCount < parsed.rows.length ||
        parsed.originalRowCount > MAX_ROWS ||
        (parsed.sourceRecords && parsed.sourceRecords.some(n => n > parsed.originalRowCount + 1))))
      throw new Error('Invalid original record count in evidence table.');
    // Optional fingerprint describes original uploaded bytes, not this JSON representation.
    // Never accept a digest without its matching validated byte count.
    if(provenance !== null && (
       !provenance || typeof provenance !== 'object' ||
       !Number.isSafeInteger(provenance.byteCount) || provenance.byteCount < 0 ||
       provenance.byteCount > MAX_BYTES ||
       typeof provenance.sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(provenance.sha256)))
      throw new Error('Invalid original-file SHA-256 provenance.');
    const source = {fileName: sourceFileName, delimiter: parsed.delimiter,
      headerRecord: 1, recordUnit: 'logical CSV/TSV record'};
    if(parsed.originalRowCount !== undefined) source.originalDataRecords = parsed.originalRowCount;
    if(provenance !== null) {
      source.byteCount = provenance.byteCount;
      source.digestAlgorithm = 'SHA-256';
      source.sha256 = provenance.sha256;
    }
    return JSON.stringify({
      format: 'data-rescue-evidence', schemaVersion: 1,
      source,
      headers: parsed.headers.slice(), normalizedHeaders: parsed.normalizedHeaders.slice(),
      warnings: parsed.warnings.slice(), recordCount: parsed.rows.length,
      records: parsed.rows.map((values, index) => ({
        sourceRecord: parsed.sourceRecords ? parsed.sourceRecords[index] : index + 2,
        values: values.slice()
      }))
    });
  }

  return {parseDelimited, summarize, withoutExactDuplicates, inspectSourceRecords, findSourceRecordOffset, formulaRisk, spreadsheetExportRisk, exportCsv, exportCsvDownload, exportEvidenceJson, MAX_BYTES, MAX_ROWS};
});
