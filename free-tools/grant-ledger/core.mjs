/** Grant Budget & Evidence Ledger — local, review-only calculation engine.
 * All amounts are integer cents. All eligibility and compliance judgments remain human.
 */
export const MAX_CATEGORIES = 50;
export const MAX_EXPENSES = 500;
export const MAX_MONEY_CENTS = 999_999_999_99;

function boundedText(value, field, max = 500, required = true) {
  if (typeof value !== 'string' || value.length > max || (required && !value.trim())) {
    throw new Error(`${field}: ${required ? 'enter' : 'use'} text of at most ${max} characters`);
  }
  return value; // Preserve identifiers exactly; do not trim.
}
function isoDate(value, field) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error(`${field}: use YYYY-MM-DD`);
  const [year, month, day] = value.split('-').map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1]) throw new Error(`${field}: invalid calendar date`);
  return value;
}
export function parseMoney(value) {
  if (typeof value !== 'string' || !/^(0|[1-9]\d{0,8})(?:\.(\d{1,2}))?$/.test(value)) throw new Error('Amount: use a nonnegative decimal with at most two cents digits');
  const [dollars, fraction = ''] = value.split('.');
  const cents = Number(dollars) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(cents) || cents > MAX_MONEY_CENTS) throw new Error('Amount exceeds limit');
  return cents;
}
export function parsePercent(value) {
  if (typeof value !== 'string' || !/^(?:100(?:\.0{1,2})?|(?:0|[1-9]\d?)(?:\.\d{1,2})?)$/.test(value)) throw new Error('Allocation: enter 0 through 100 with up to two decimal places');
  const [whole, fraction = ''] = value.split('.');
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
}
export function formatMoney(cents) {
  if (!Number.isSafeInteger(cents)) throw new Error('Invalid cents');
  const sign = cents < 0 ? '-' : '';
  const n = Math.abs(cents);
  return `${sign}$${Math.floor(n / 100).toLocaleString('en-US')}.${String(n % 100).padStart(2, '0')}`;
}
export function calculateLedger(award, categories, expenses) {
  if (!award || typeof award !== 'object') throw new Error('Award required');
  const awardId = boundedText(award.awardId, 'Award ID', 120);
  const awardName = boundedText(award.awardName, 'Award name', 180);
  const start = isoDate(award.start, 'Award start');
  const end = isoDate(award.end, 'Award end');
  if (start > end) throw new Error('Award start is after end');
  if (!Array.isArray(categories) || categories.length > MAX_CATEGORIES) throw new Error('Too many budget categories');
  if (!Array.isArray(expenses) || expenses.length > MAX_EXPENSES) throw new Error('Too many expenses');
  const categoryIds = new Set();
  const normalizedCategories = categories.map((c) => {
    if (!c || typeof c !== 'object') throw new Error('Invalid category');
    const categoryId = boundedText(c.categoryId, 'Category ID', 120);
    if (categoryIds.has(categoryId)) throw new Error(`Duplicate category ID: ${categoryId}`);
    categoryIds.add(categoryId);
    return { categoryId, label: boundedText(c.label, 'Category label', 180),
      budgetCents: parseMoney(c.budget), restrictionNote: boundedText(c.restrictionNote ?? '', 'Restriction note', 500, false) };
  });
  const totals = new Map(normalizedCategories.map(c => [c.categoryId, 0]));
  const transactionIds = new Set();
  const review = [];
  let totalExpenseCents = 0;
  let totalAssignedCents = 0;
  const normalizedExpenses = expenses.map((e) => {
    if (!e || typeof e !== 'object') throw new Error('Invalid expense');
    const transactionId = boundedText(e.transactionId, 'Transaction ID', 120);
    if (transactionIds.has(transactionId)) throw new Error(`Duplicate transaction ID: ${transactionId}`);
    transactionIds.add(transactionId);
    const sourceId = boundedText(e.sourceId, 'Source ID', 120);
    const date = isoDate(e.date, `Expense ${transactionId} date`);
    const categoryId = boundedText(e.categoryId, 'Category ID', 120);
    if (!categoryIds.has(categoryId)) throw new Error(`Unknown category ID: ${categoryId}`);
    const totalCents = parseMoney(e.amount);
    const allocationBps = parsePercent(e.percent);
    const allocationBasis = boundedText(e.allocationBasis ?? '', 'Allocation basis', 500, false);
    const evidenceRef = boundedText(e.evidenceRef ?? '', 'Evidence reference', 500, false);
    const note = boundedText(e.note ?? '', 'Note', 500, false);
    const assignedCents = Math.floor((totalCents * allocationBps + 5000) / 10000);
    const unassignedCents = totalCents - assignedCents;
    if (date < start || date > end) review.push({transactionId, flag:'Date outside award period'});
    if (allocationBps > 0 && allocationBps < 10000 && !allocationBasis.trim()) review.push({transactionId, flag:'Partial allocation lacks documented basis'});
    if (!evidenceRef.trim()) review.push({transactionId, flag:'Supporting evidence reference missing'});
    if (allocationBps === 0) review.push({transactionId, flag:'No amount assigned to this award'});
    totalExpenseCents += totalCents;
    totalAssignedCents += assignedCents;
    totals.set(categoryId, totals.get(categoryId) + assignedCents);
    return {transactionId,sourceId,date,categoryId,totalCents,allocationBps,assignedCents,unassignedCents,allocationBasis,evidenceRef,note};
  });
  const lines = normalizedCategories.map(c => {
    const actualCents = totals.get(c.categoryId);
    const differenceCents = c.budgetCents - actualCents;
    if (differenceCents < 0) review.push({transactionId:'', flag:`Budget comparison: ${c.categoryId} exceeds planned amount`});
    return {...c,actualCents,differenceCents};
  });
  return {award:{awardId,awardName,start,end},lines,expenses:normalizedExpenses,
    totalBudgetCents:lines.reduce((sum,l)=>sum+l.budgetCents,0),totalExpenseCents,totalAssignedCents,
    totalUnassignedCents:totalExpenseCents-totalAssignedCents,review};
}
function csvCell(value) {
  let text = String(value ?? '');
  // Spreadsheet-oriented precaution; a CSV consumer may strip or reinterpret this prefix.
  if (/^[\s\uFEFF]*[=+\-@\t\r＝＋－＠]/u.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"','""')}"`;
}
export function exportTransactionsCSV(result) {
  const cols=['transactionId','sourceId','date','categoryId','totalCents','allocationBps','assignedCents','unassignedCents','allocationBasis','evidenceRef','note'];
  return [cols.map(csvCell).join(','),...result.expenses.map(e=>cols.map(c=>csvCell(e[c])).join(','))].join('\r\n')+'\r\n';
}
export function exportBudgetCSV(result) {
  const cols=['awardId','categoryId','label','budgetCents','actualCents','differenceCents','restrictionNote'];
  return [cols.map(csvCell).join(','),...result.lines.map(l=>cols.map(c=>csvCell(c==='awardId'?result.award.awardId:l[c])).join(','))].join('\r\n')+'\r\n';
}
export function exportJSON(result) {
  return JSON.stringify({schema:'grant-ledger-review-v1',...result},null,2)+'\n';
}
