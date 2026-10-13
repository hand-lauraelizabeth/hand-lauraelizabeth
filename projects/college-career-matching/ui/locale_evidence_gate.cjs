'use strict';
/** Accept only exact-IPEDs-unit evidence for locale enrichment. */
const VALID=new Set([11,12,13,21,22,23,31,32,33,41,42,43]);
function validateLocaleCandidate(c) {
  if(!c || !/^\d{6}$/.test(String(c.unitid))) return false;
  if(String(c.source_unitid)!==String(c.unitid)) return false;
  if(c.source_table!=='HD2025' || c.reporting_year!==2025) return false;
  if(!VALID.has(c.locale_code)) return false;
  if(typeof c.source_url!=='string' ||
    !c.source_url.startsWith('https://nces.ed.gov/ipeds/')) return false;
  if(c.source_system!=='IPEDS') return false;
  return true;
}
module.exports={validateLocaleCandidate};
