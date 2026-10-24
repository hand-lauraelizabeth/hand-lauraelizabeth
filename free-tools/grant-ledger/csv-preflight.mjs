/** Browser-local CSV export gate. Never rewrite source identifiers to make CSV appear safe. */
const COLUMNS = Object.freeze({
  transactions: ['transactionId','sourceId','date','categoryId','totalCents','allocationBps','assignedCents','unassignedCents','allocationBasis','evidenceRef','note'],
  budget: ['awardId','categoryId','label','budgetCents','actualCents','differenceCents','restrictionNote'],
  review: ['transactionId','sourceId','categoryId','flag']
});
const DANGEROUS_CONTROL = /[\u0000-\u001F\u007F-\u009F\u00AD\u034F\u061C\u180E\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFE00-\uFE0F\uFEFF]/u;
const FORMULA_PREFIX = /^[\s\u00A0\uFEFF\u200B-\u200F\u202A-\u202E\u2060-\u206F]*[=+\-@＝＋－＠]/u;
function checkCell(value, column) {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error(`CSV export blocked: invalid ${column}. Use Evidence JSON.`);
    return;
  }
  if (typeof value !== 'string' || DANGEROUS_CONTROL.test(value) || FORMULA_PREFIX.test(value)) {
    throw new Error(`CSV export blocked: ${column} cannot be safely exported to a spreadsheet. Use Evidence JSON to preserve the original value.`);
  }
}
/** Returns true or throws before any CSV Blob is constructed. */
export function assertSafeLedgerCSV(result, kind) {
  const columns = COLUMNS[kind];
  if (!columns || !result || typeof result !== 'object') throw new Error('Invalid CSV export request');
  const rows = kind === 'transactions' ? result.expenses : kind === 'budget' ? result.lines : result.review;
  if (!Array.isArray(rows)) throw new Error('CSV export blocked: invalid data. Use Evidence JSON.');
  for (const row of rows) {
    if (!row || typeof row !== 'object') throw new Error('CSV export blocked: invalid row. Use Evidence JSON.');
    for (const column of columns) {
      const value = column === 'awardId' ? result.award?.awardId : row[column];
      checkCell(value, column);
    }
  }
  return true;
}
