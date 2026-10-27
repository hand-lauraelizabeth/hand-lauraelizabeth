/** Local-only expenditure correction history. This is a user-entered change log, not verified provenance. */
import {exportJSON} from './core.mjs';
export const MAX_CORRECTIONS = 500;
export const EXPENSE_FIELDS = Object.freeze([
  'transactionId','sourceId','date','categoryId','amount','percent',
  'allocationBasis','evidenceRef','note'
]);
function exactSnapshot(entry) {
  if (!entry || typeof entry !== 'object') throw new Error('Correction requires an expenditure.');
  const copy = {};
  for (const field of EXPENSE_FIELDS) {
    const value = entry[field] ?? (['allocationBasis','evidenceRef','note'].includes(field) ? '' : undefined);
    if (typeof value !== 'string') throw new Error('Correction has invalid '+field+'.');
    copy[field] = value;
  }
  return copy;
}
/** Return a new log only for a substantive, validated correction. No timestamps are invented. */
export function appendExpenseCorrection(history, previous, replacement) {
  if (!Array.isArray(history) || history.length > MAX_CORRECTIONS) throw new Error('Invalid correction history.');
  const before = exactSnapshot(previous), after = exactSnapshot(replacement);
  if (!before.transactionId.trim() || before.transactionId !== after.transactionId) {
    throw new Error('Correction cannot change the transaction ID.');
  }
  if (EXPENSE_FIELDS.every(field => before[field] === after[field])) return history;
  if (history.length >= MAX_CORRECTIONS) throw new Error('Correction history limit reached. Download Evidence JSON before continuing.');
  return [...history, {revision:history.length+1, transactionId:before.transactionId, before, after}];
}
/** Preserve the existing evidence schema and add explicitly scoped, exact prior values. */
export function exportEvidenceWithCorrections(result, history) {
  if (!Array.isArray(history) || history.length > MAX_CORRECTIONS) throw new Error('Invalid correction history.');
  const evidence = JSON.parse(exportJSON(result));
  evidence.correctionHistory = {
    schema:'expenditure-corrections-v1',
    scope:'Expenditure corrections only. Award and budget-category edits are not recorded.',
    entries:history
  };
  return JSON.stringify(evidence,null,2)+'\n';
}
