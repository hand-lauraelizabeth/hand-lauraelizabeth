/* Review-only companion to the nationwide College Search. Does not alter live page 1044. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.HistoricalProgramExplorer = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const PERIOD = 'July 1, 2024–June 30, 2025';
  const KINDS = ['reported', 'missing_or_suppressed'];
  const LIMIT = 768000;
  const cipRe = /^\d{6}$/;
  const uidRe = /^\d{6}$/;
  const shaRe = /^[a-f0-9]{64}$/;

  function validateManifest(m) {
    if (!m || m.schema_version !== '1.0' ||
        m.data_kind !== 'IPEDS_2024_25_HISTORICAL_FIRST_MAJOR_COMPLETIONS' ||
        m.current_program_offering_verified !== false ||
        m.credential_name_institution_verified !== false ||
        m.professional_license_eligibility_verified !== false ||
        m.admissions_and_career_matching_authorized !== false ||
        m.source_reporting_period !== '2024-07-01 through 2025-06-30' ||
        !m.sources || !m.sources.completions || !m.sources.cip2020 ||
        !shaRe.test(m.sources.completions.sha256) ||
        !shaRe.test(m.sources.cip2020.sha256) ||
        !Array.isArray(m.shards) || m.shards.length !== 13 ||
        !m.award_levels || !m.cip2020_titles || !m.counts) {
      throw new Error('Program evidence manifest failed the historical-source gate.');
    }
    let schools = 0, records = 0;
    m.shards.forEach((s, i) => {
      if (s.file !== `programs-${String(i).padStart(2, '0')}.json` ||
          !shaRe.test(s.sha256) || !shaRe.test(s.gzip_sha256) ||
          !Number.isInteger(s.bytes) || s.bytes < 0 ||
          !Number.isInteger(s.gzip_bytes) || s.gzip_bytes > LIMIT || s.gzip_bytes < 0 ||
          !Number.isInteger(s.institutions) || s.institutions < 0 ||
          !Number.isInteger(s.program_award_records) || s.program_award_records < 0) {
        throw new Error('Program shard manifest entry failed validation.');
      }
      schools += s.institutions;
      records += s.program_award_records;
    });
    if (schools !== m.counts.institutions_with_historical_program_completions ||
        records !== m.counts.joined_program_award_records ||
        schools + m.counts.national_institutions_without_joined_completions !== m.counts.national_institutions) {
      throw new Error('Program manifest totals do not reconcile.');
    }
    return m;
  }

  function validateShard(payload, shardMeta, manifest, titles, seenIds) {
    if (!payload || payload.schema_version !== '1.0' || !Array.isArray(payload.institutions) ||
        payload.institutions.length !== shardMeta.institutions) throw new Error('Invalid program shard structure.');
    const ids = seenIds || new Set();
    let n = 0;
    const results = [];
    for (const item of payload.institutions) {
      if (!Array.isArray(item) || item.length !== 2 || !uidRe.test(item[0]) ||
          !Array.isArray(item[1]) || ids.has(item[0])) throw new Error('Invalid or duplicate UNITID.');
      ids.add(item[0]);
      const local = new Set();
      for (const p of item[1]) {
        if (!Array.isArray(p) || p.length !== 4 || !cipRe.test(p[0]) ||
            !Object.prototype.hasOwnProperty.call(titles, p[0]) ||
            !Object.prototype.hasOwnProperty.call(manifest.award_levels, p[1]) ||
            !KINDS.includes(p[3]) ||
            (p[3] === 'reported' ? !Number.isSafeInteger(p[2]) || p[2] < 0 : p[2] !== null)) {
          throw new Error('Invalid CIP6 × award-level historical record.');
        }
        const key = p[0] + ':' + p[1];
        if (local.has(key)) throw new Error('Duplicate CIP6 × award-level record.');
        local.add(key);
        n++;
      }
      results.push(item);
    }
    if (n !== shardMeta.program_award_records) throw new Error('Program shard record total mismatch.');
    return results;
  }

  function search(rows, titles, awards, query, award, names) {
    const q = String(query || '').trim().toLocaleLowerCase();
    if (!q && !award) return [];
    const out = [];
    for (const [unitid, programs] of rows) {
      for (const [cip, level, count, status] of programs) {
        const title = titles[cip];
        if ((award && level !== award) || (q && !(cip.includes(q.replace(/\./g, '')) || title.toLocaleLowerCase().includes(q)))) continue;
        out.push({unitid, institution: names?.[unitid]?.name || `Institution UNITID ${unitid}`,
          state: names?.[unitid]?.state || null, cip6:cip, cip_title:title,
          awlevel:level, award_level:awards[level], awards_conferred:count,
          count_status:status, evidence_kind:'historical_completions',
          current_offering_verified:false, reporting_period:PERIOD});
      }
    }
    return out.sort((a,b)=>a.institution.localeCompare(b.institution) || a.cip6.localeCompare(b.cip6) || Number(a.awlevel)-Number(b.awlevel));
  }

  async function verifiedJSON(url, expectedSha) {
    if (!globalThis.crypto?.subtle) throw new Error('Secure context required for SHA-256 source verification.');
    const response = await fetch(url, {cache:'no-store'});
    if (!response.ok) throw new Error('Source request failed (' + response.status + ').');
    const bytes = await response.arrayBuffer();
    const actual = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b=>b.toString(16).padStart(2,'0')).join('');
    if (actual !== expectedSha) throw new Error('Source checksum mismatch.');
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  return Object.freeze({validateManifest, validateShard, search, verifiedJSON, PERIOD});
});