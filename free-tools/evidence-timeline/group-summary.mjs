/* Bounded, text-only preview of user-assigned related-record groups.
 * Full records and exact source IDs remain unchanged in exports.
 */
export const MAX_PREVIEW_GROUPS = 8;
export const MAX_PREVIEW_SOURCE_IDS = 3;
export const MAX_PREVIEW_FIELD_CODEPOINTS = 48;
const obscuring = /[\u0000-\u001f\u007f-\u009f\u00ad\u061c\u180e\u200b-\u200f\u2028-\u202e\u2060-\u2069\ufeff]/gu;
function visibleQuoted(value) {
  // Limit only the preview, counting Unicode code points so astral symbols
  // are not split. Exact user-provided strings remain in the saved evidence.
  const points=Array.from(value);
  const prefix=points.slice(0,MAX_PREVIEW_FIELD_CODEPOINTS).join('');
  const safe=prefix.replaceAll('\\','\\\\').replaceAll('"','\\"')
    .replace(obscuring, c => '\\u'+c.codePointAt(0).toString(16).padStart(4,'0'));
  const hidden=points.length-MAX_PREVIEW_FIELD_CODEPOINTS;
  return '"'+safe+'"'+(hidden>0?' ('+hidden+' additional characters not shown)':'');
}
export function formatGroupSummary(groups) {
  if (!Array.isArray(groups) || groups.length > 5000) throw Error('Invalid group summary');
  if (groups.length === 0) return 'No related-record groups to review.';
  const shown = Math.min(groups.length, MAX_PREVIEW_GROUPS);
  const result = [groups.length+' related-record '+(groups.length===1?'group':'groups')+
    ' flagged for manual review. Showing first '+shown+' '+(shown===1?'group':'groups')+' by first record date.'];
  for (const group of groups.slice(0, MAX_PREVIEW_GROUPS)) {
    if (!group || typeof group.group !== 'string' || !Array.isArray(group.sourceIds) ||
      group.sourceIds.length < 2 || group.sourceIds.length > 10000 ||
      group.sourceIds.slice(0,MAX_PREVIEW_SOURCE_IDS).some(id => typeof id !== 'string'))
      throw Error('Invalid group summary');
    const ids = group.sourceIds.slice(0, MAX_PREVIEW_SOURCE_IDS).map(visibleQuoted);
    const omitted = group.sourceIds.length-ids.length;
    result.push('Group '+visibleQuoted(group.group)+': '+group.sourceIds.length+' records; source IDs '+
      ids.join(', ')+(omitted?'; '+omitted+' additional source IDs not shown':'')+'.');
  }
  if (groups.length > shown)
    result.push((groups.length-shown)+' additional groups not shown. Search by group label to inspect them.');
  result.push('The full records remain in exact JSON exports; spreadsheet CSV is available only when its safety checks pass.');
  return result.join(' ');
}
