export function validDate(value) {
  if (typeof value !== 'string' || value.length !== 10) return false;
  const parts = value.split('-').map(Number);
  if (parts.length !== 3) return false;
  const [year,month,day] = parts;
  const date = new Date(Date.UTC(year,month-1,day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month-1 && date.getUTCDate() === day;
}
