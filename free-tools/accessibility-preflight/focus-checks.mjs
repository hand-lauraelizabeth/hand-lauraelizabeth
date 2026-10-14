// HTML-only heuristic for W3C ACT rule 6cfa84. Static markup cannot establish
// computed CSS, flat-tree focusability, scripted focus redirection, or compliance.
const NATIVELY_SEQUENTIAL = new Set(['BUTTON', 'SELECT', 'TEXTAREA', 'IFRAME', 'SUMMARY']);
const cssHidden = element => {
  for (let node = element; node && node.nodeType === 1; node = node.parentElement) {
    if (node.hasAttribute('hidden') || node.hasAttribute('inert')) return true;
    const display = node.style?.display?.toLowerCase();
    const visibility = node.style?.visibility?.toLowerCase();
    if (display === 'none' || visibility === 'hidden' || visibility === 'collapse') return true;
  }
  return false;
};
const sequentialCandidate = element => {
  if (element.matches(':disabled') || (element.tagName === 'INPUT' && element.type === 'hidden')) return false;
  const rawTabindex = element.getAttribute('tabindex');
  if (rawTabindex !== null && /^[+-]?\d+$/.test(rawTabindex.trim())) {
    return Number(rawTabindex) >= 0;
  }
  if (NATIVELY_SEQUENTIAL.has(element.tagName)) return true;
  if (element.tagName === 'INPUT') return true;
  if ((element.tagName === 'A' || element.tagName === 'AREA') && element.hasAttribute('href')) return true;
  if (element.getAttribute('contenteditable') === '' || element.getAttribute('contenteditable') === 'true') return true;
  return false;
};
export function checkHiddenFocus(doc, add) {
  for (const element of doc.querySelectorAll('[aria-hidden="true"], [aria-hidden="true"] *')) {
    if (!element.closest('[aria-hidden="true"]') || cssHidden(element) || !sequentialCandidate(element)) continue;
    add('aria-hidden-focus', 'review', element,
      'Potential sequential keyboard focus inside aria-hidden="true". Check actual visibility, focus behavior, and the accessibility tree.',
      'W3C ACT rule 6cfa84 / WCAG 4.1.2');
  }
}
