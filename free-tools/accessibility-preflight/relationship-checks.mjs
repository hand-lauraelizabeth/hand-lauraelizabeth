// Static HTML relationship checks. Findings are review prompts, not conformance verdicts.
const IDREF_LIST = ['aria-labelledby', 'aria-describedby', 'aria-controls', 'aria-owns', 'aria-details', 'aria-errormessage'];
const IDREF_SINGLE = ['aria-activedescendant'];
const LABELABLE = new Set(['INPUT','BUTTON','SELECT','TEXTAREA','METER','OUTPUT','PROGRESS']);
const tidy = value => String(value ?? '').replace(/\s+/g, ' ').trim();

export function checkRelationships(doc, add) {
  // IDs are case-sensitive. Do not trim or normalize ID values themselves.
  const byId = new Map();
  const idCounts = new Map();
  for (const el of doc.querySelectorAll('[id]')) {
    // Keep the exact, case-sensitive ID. Do not collapse Unicode or whitespace.
    idCounts.set(el.id, (idCounts.get(el.id) || 0) + 1);
    if (!byId.has(el.id)) byId.set(el.id, el);
  }
  for (const attr of [...IDREF_LIST, ...IDREF_SINGLE]) {
    for (const el of doc.querySelectorAll('[' + attr + ']')) {
      const raw = el.getAttribute(attr) ?? '';
      const refs = tidy(raw).split(' ').filter(Boolean);
      if (!refs.length) {
        add('empty-id-reference', 'review', el, attr + ' has no reference target.', 'WAI-ARIA 1.2 ID reference processing');
        continue;
      }
      if (IDREF_SINGLE.includes(attr) && refs.length !== 1) {
        add('single-id-reference', 'review', el, attr + ' must reference one ID.', 'WAI-ARIA 1.2 ID reference processing');
      }
      const visited = new Set();
      for (const ref of refs) {
        if (visited.has(ref)) {
          add('repeated-id-reference', 'review', el, attr + ' repeats ID ' + ref.slice(0, 100) + '.', 'WAI-ARIA 1.2 ID reference processing');
        } else if (!byId.has(ref)) {
          add('unresolved-id-reference', 'review', el, attr + ' references missing ID ' + ref.slice(0, 100) + '.', 'WAI-ARIA 1.2 ID reference processing');
        } else if (idCounts.get(ref) > 1) {
          add('ambiguous-id-reference', 'review', el, attr + ' references ID ' + ref.slice(0, 100) + ' used by multiple elements. The first match may provide the wrong name, description, or relationship.', 'WAI-ARIA 1.2 ID reference processing / WCAG 4.1.2');
        }
        visited.add(ref);
      }
    }
  }
  for (const label of doc.querySelectorAll('label[for]')) {
    const target = byId.get(label.getAttribute('for'));
    if (!target || !LABELABLE.has(target.tagName) || (target.tagName === 'INPUT' && target.type === 'hidden')) {
      add('label-target', 'review', label, 'The label for attribute does not resolve to a supported labelable control.', 'WCAG 1.3.1 / HTML label association');
    }
    if (idCounts.get(label.getAttribute('for')) > 1) {
      add('ambiguous-label-target', 'review', label, 'The label for attribute targets an ID used by multiple elements. Verify which control receives the label.', 'HTML label association / WCAG 4.1.2');
    }
  }
  for (const cell of doc.querySelectorAll('th[headers],td[headers]')) {
    const refs = tidy(cell.getAttribute('headers')).split(' ').filter(Boolean);
    if (!refs.length) add('table-header-reference', 'review', cell, 'The headers attribute is empty.', 'WCAG 1.3.1');
    for (const id of new Set(refs)) {
      if (idCounts.get(id) > 1) {
        add('ambiguous-table-header', 'review', cell, 'The headers attribute references ID ' + id.slice(0, 100) + ' used by multiple elements.', 'HTML table headers / WCAG 1.3.1');
      }
      const target = byId.get(id);
      if (!target || target.tagName !== 'TH' || target.closest('table') !== cell.closest('table')) {
        add('table-header-reference', 'review', cell, 'A headers reference does not resolve to a header cell in this table: ' + id.slice(0, 100) + '.', 'WCAG 1.3.1');
      }
    }
  }
  for (const el of doc.querySelectorAll('button[aria-label],a[href][aria-label]')) {
    // Only inspect literal text; CSS visibility, nested images and computed names require manual review.
    const visible = tidy(el.textContent);
    const named = tidy(el.getAttribute('aria-label'));
    if (visible && named && !named.toLocaleLowerCase().includes(visible.toLocaleLowerCase())) {
      add('label-in-name', 'review', el, 'The explicit ARIA name does not contain the element text. Verify visible-label correspondence.', 'WCAG 2.5.3');
    }
  }
  for (const frame of doc.querySelectorAll('iframe')) {
    if (!tidy(frame.getAttribute('title'))) {
      add('iframe-title', 'review', frame, 'Provide a descriptive frame title or verify another accessible naming method.', 'WCAG 4.1.2');
    }
  }
}
