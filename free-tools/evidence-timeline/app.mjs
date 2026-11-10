import {summary} from './core.mjs';
import {startLocalDownload} from './download-guard.mjs';
import {csvExportRisk,exportSafeEvidenceCSV} from './safe-export.mjs';
import {normalizeExact as normalizeEvidence} from './exact-core.mjs';
import {readExactJSON} from './json-import.mjs';
import {createImportFeedback} from './import-feedback.mjs';
import {previewReplacement, replacementConfirmation} from './replacement-preview.mjs';
import {reviewStatusSummary} from './review-filter.mjs';
import {findSourceIds} from './source-id-find.mjs';
import {filterByGroupLabel} from './group-find.mjs';
import {formatGroupSummary} from './group-summary.mjs';
import {setReviewGroup} from './edit-group.mjs';
import {STATUS_OPTIONS} from './reclassify.mjs';
import {changeReviewStatus, undoReviewStatus} from './undo-status.mjs';
import {timelineSVG,timelineScale,isoDay,prettyDay} from './timeline-visual.mjs';
import {exportGantt} from './gantt-export.mjs';

const $ = id => document.getElementById(id);
const form = $('entry-form');
const error = $('error');
const list = $('records');
const statusNames = {
  reported: 'Recorded',
  corroborated: 'Cross-checked',
  disputed: 'Disputed',
  unresolved: 'Needs review'
};
const kindNames = {source:'Source record', observation:'My observation', inference:'My interpretation'};
const dateFormatter = new Intl.DateTimeFormat('en-US', {month:'short', day:'numeric', year:'numeric', timeZone:'UTC'});
let records = [];
let pendingStatusUndo = null;
let editingGroupId = null;
let editingRecordId = null;
let exampleMode = false;
let visualOffset = 0;

function text(tag, value, className) {
  const element = document.createElement(tag);
  element.textContent = String(value);
  if (className) element.className = className;
  return element;
}
function displayDate(value) {
  return dateFormatter.format(new Date(value + 'T00:00:00Z'));
}
function clearStatusUndo() {
  pendingStatusUndo = null;
  $('undo-status').hidden = true;
  $('undo-status').disabled = true;
}
function clearError() {
  error.hidden = true;
  error.textContent = '';
  for (const field of form.elements) {
    field.removeAttribute('aria-invalid');
    if (field.id === 'sourceId') field.setAttribute('aria-describedby', 'source-help');
    else if(field.id==='endDate')field.setAttribute('aria-describedby','end-date-help');
    else field.removeAttribute('aria-describedby');
  }
}
function showError(message, field) {
  error.textContent = message;
  error.hidden = false;
  if (field) {
    const input = $(field);
    input.setAttribute('aria-invalid', 'true');
    input.setAttribute('aria-describedby', (field === 'sourceId' ? 'source-help ' : field==='endDate'?'end-date-help ':'') + 'error');
    if(field==='endDate')$('date-range-options').open=true;
  }
  error.focus();
}
function clearFilters() {
  $('review-filter').value = 'all';
  $('text-search').value = '';
  $('source-find').value = '';
  $('group-find').value = '';
  $('group-find').disabled = false;
  $('ungrouped-only').checked = false;
}
function visibleRecords() {
  const filtered = filterByGroupLabel(
    findSourceIds(records, $('review-filter').value, $('source-find').value),
    $('group-find').value,
    $('ungrouped-only').checked
  );
  const search = $('text-search').value.toLocaleLowerCase();
  return search ? filtered.filter(record =>
    [record.claim, record.sourceId, record.group].some(value => value.toLocaleLowerCase().includes(search))
  ) : filtered;
}
function stopEntryEdit() {
  editingRecordId = null;
  form.reset();
  clearError();
  $('editing-note').hidden = true;
  $('cancel-entry-edit').hidden = true;
  $('save-entry').textContent = 'Add to timeline +';
}
function stopGroupEdit() {
  editingGroupId = null;
  $('group-edit-panel').hidden = true;
  $('group-edit-form').reset();
  $('group-edit-error').hidden = true;
  $('group-edit-error').textContent = '';
  $('group-edit-value').removeAttribute('aria-invalid');
  $('group-edit-value').setAttribute('aria-describedby', 'group-edit-help');
}
function focusRecordButton(sourceId, action) {
  const button = [...list.querySelectorAll('button')].find(item =>
    item.dataset.sourceId === sourceId && item.dataset.action === action
  );
  (button || $('count')).focus();
}
function beginEntryEdit(record) {
  if ((editingRecordId !== null || $('claim').value || $('sourceId').value) &&
      !window.confirm('Replace the unsaved form with this entry?')) return;
  clearError();
  editingRecordId = record.sourceId;
  for (const key of ['date', 'endDate', 'sourceId', 'claim', 'group', 'kind', 'status']) $(key).value = record[key] ?? '';
  $('date-range-options').open = Boolean(record.endDate);
  $('editing-note').hidden = false;
  $('cancel-entry-edit').hidden = false;
  $('save-entry').textContent = 'Save changes';
  $('entry-message').textContent = '';
  $('entry-heading').textContent = 'Edit this entry';
  $('claim').focus();
}
function beginGroupEdit(record) {
  if (editingGroupId !== null && editingGroupId !== record.sourceId &&
      !window.confirm('Discard the unsaved group edit and open another entry?')) return;
  stopGroupEdit();
  editingGroupId = record.sourceId;
  $('group-edit-source').textContent = 'Source reference · ' + record.sourceId;
  $('group-edit-value').value = record.group;
  $('group-edit-panel').hidden = false;
  $('group-edit-value').focus();
}
function renderRecord(record) {
  const item = text('li', '', 'record');
  item.dataset.status = record.status;
  const heading = text('div', '', 'record-head');
  const date = text('time', displayDate(record.date));
  date.dateTime = record.date;
  heading.append(date);
  if(record.endDate&&record.endDate!==record.date)heading.append(text('span','– '+displayDate(record.endDate),'range-end'));
  heading.append(text('span', statusNames[record.status], 'status-badge'));
  item.append(heading, text('h3', record.claim));
  const reference = text('p', '', 'source-reference');
  reference.append(text('strong', record.sourceId), document.createTextNode(' · ' + kindNames[record.kind]));
  item.append(reference);
  if (record.group) item.append(text('span', record.group, 'group-chip'));

  const actions = text('div', '', 'record-actions');
  const edit = text('button', 'Edit entry', 'text-button');
  edit.type = 'button';
  edit.dataset.sourceId = record.sourceId;
  edit.dataset.action = 'edit';
  edit.setAttribute('aria-label', 'Edit entry ' + record.sourceId);
  edit.addEventListener('click', () => beginEntryEdit(record));
  const remove = text('button', 'Remove', 'text-button remove');
  remove.type = 'button';
  remove.setAttribute('aria-label', 'Remove entry ' + record.sourceId);
  remove.addEventListener('click', () => {
    if (!window.confirm('Remove this entry? Download a copy first if you need to keep it.')) return;
    records = records.filter(row => row.sourceId !== record.sourceId);
    if (editingGroupId === record.sourceId) stopGroupEdit();
    if (editingRecordId === record.sourceId) stopEntryEdit();
    clearStatusUndo();
    render();
    $('count').focus();
  });
  actions.append(edit, remove);
  item.append(actions);

  const review = text('details', '', 'entry-review');
  review.append(text('summary', 'Change review status or group'));
  const label = text('label', 'Review status');
  const select = document.createElement('select');
  label.append(select);
  select.setAttribute('aria-label', 'Review status for entry ' + record.sourceId);
  select.dataset.sourceId = record.sourceId;
  for (const status of STATUS_OPTIONS) {
    const option = text('option', statusNames[status]);
    option.value = status;
    select.append(option);
  }
  select.value = record.status;
  select.addEventListener('change', () => {
    try {
      const change = changeReviewStatus(records, record.sourceId, select.value);
      records = change.records;
      if (editingRecordId === record.sourceId) $('status').value = select.value;
      pendingStatusUndo = change.undo;
      $('review-filter').value = 'all';
      render();
      $('undo-status').hidden = !pendingStatusUndo;
      $('undo-status').disabled = !pendingStatusUndo;
      $('change-status-message').textContent = 'Review status updated for ' + record.sourceId + '.';
      $('count').focus();
    } catch {
      $('change-status-message').textContent = 'Status could not be changed. Please try again.';
      render();
    }
  });
  const editGroup = text('button', 'Edit related group', 'text-button');
  editGroup.type = 'button';
  editGroup.dataset.sourceId = record.sourceId;
  editGroup.dataset.action = 'group';
  editGroup.setAttribute('aria-label', 'Edit related group for ' + record.sourceId);
  editGroup.addEventListener('click', () => beginGroupEdit(record));
  review.append(label, editGroup);
  item.append(review);
  return item;
}
function render() {
  visualOffset=0;
  $('visual-error').hidden=true;
  $('visual-status').textContent='';
  const report = summary(records);
  const visible = visibleRecords();
  const filtered = visible.length !== records.length || $('review-filter').value !== 'all' ||
    $('source-find').value !== '' || $('group-find').value !== '' ||
    $('ungrouped-only').checked || $('text-search').value !== '';
  list.replaceChildren(...visible.map(renderRecord));
  $('record-badge').textContent = records.length + (records.length === 1 ? ' entry' : ' entries');
  $('count').textContent = records.length === 0 ? 'Your entries will appear here in date order.' :
    filtered ? 'Showing ' + visible.length + ' of ' + records.length + ' entries · earliest first' :
    records.length + (records.length === 1 ? ' entry' : ' entries') + ' · earliest first';
  $('clear-source-find').disabled = $('source-find').value === '';
  $('clear-group-find').disabled = $('group-find').value === '' && !$('ungrouped-only').checked;
  $('reset-all-filters').hidden = !filtered;
  $('empty').hidden = records.length > 0;
  $('no-results').hidden = records.length === 0 || visible.length > 0;
  $('demo-guide').hidden = !exampleMode;
  $('insights').hidden = records.length === 0;
  if (records.length) {
    const scale=timelineScale(records);
    $('date-span').textContent=prettyDay(isoDay(scale.first))+(scale.first===scale.last?'':' – '+prettyDay(isoDay(scale.last)));
  }
  $('needs-review').textContent = report.counts.unresolved + report.counts.disputed;
  $('linked-groups').textContent = report.reviewGroups.length;
  $('review-summary').textContent = reviewStatusSummary(records);
  $('groups').textContent = formatGroupSummary(report.reviewGroups);
  $('entry-heading').textContent = editingRecordId !== null ? 'Edit this entry' :
    records.length ? 'Add another entry' : 'Add your first entry';
  const risk = csvExportRisk(records);
  $('csv').disabled = records.length === 0 || Boolean(risk);
  for (const id of ['json', 'save-work', 'download-readable', 'clear']) $(id).disabled = records.length === 0;
  $('download-filtered').disabled = visible.length === 0;
  $('csv-warning').textContent = risk ? 'CSV download unavailable because ' + risk.field +
    ' contains ' + risk.reason + '. Use Excel Gantt or JSON to keep the original text.' : '';
  renderVisual();
}
function resetAllFilters() {
  clearFilters();
  render();
  $('count').focus();
}
$('reset-all-filters').addEventListener('click', resetAllFilters);
$('clear-no-results').addEventListener('click', resetAllFilters);
for (const id of ['text-search', 'source-find', 'group-find']) $(id).addEventListener('input', render);
$('review-filter').addEventListener('change', render);
$('clear-source-find').addEventListener('click', () => {
  $('source-find').value = '';
  render();
  $('source-find').focus();
});
$('ungrouped-only').addEventListener('change', () => {
  if ($('ungrouped-only').checked) $('group-find').value = '';
  $('group-find').disabled = $('ungrouped-only').checked;
  render();
});
$('clear-group-find').addEventListener('click', () => {
  $('group-find').value = '';
  $('group-find').disabled = false;
  $('ungrouped-only').checked = false;
  render();
  $('group-find').focus();
});
form.addEventListener('input', () => {
  if (!error.hidden) clearError();
});
form.addEventListener('submit', event => {
  event.preventDefault();
  clearError();
  const data = Object.fromEntries(new FormData(form).entries());
  for (const [id, label] of [['date', 'Date'], ['sourceId', 'Source reference'], ['claim', 'Description']]) {
    if (!String(data[id] ?? '').trim()) {
      showError('Add a ' + label.toLowerCase() + ' before saving this entry.', id);
      return;
    }
  }
  try {
    const previousId = editingRecordId;
    const next = previousId === null ? [...records, data] :
      records.map(record => record.sourceId === previousId ? data : record);
    records = normalizeEvidence(next);
    clearStatusUndo();
    stopGroupEdit();
    stopEntryEdit();
    clearFilters();
    render();
    $('entry-message').textContent = previousId === null ?
      'Entry added. It now appears in your timeline.' : 'Changes saved. Your timeline is up to date.';
    $('date').focus();
  } catch (exception) {
    const message = String(exception.message || exception);
    const field = /source ID/i.test(message) ? 'sourceId' : /End date/i.test(message) ? 'endDate' : /date/i.test(message) ? 'date' :
      /claim/i.test(message) ? 'claim' : null;
    showError(/source ID/i.test(message) ? 'Each entry needs its own source reference. Use a different reference for this entry.' : message, field);
  }
});
$('cancel-entry-edit').addEventListener('click', () => {
  const previousId = editingRecordId;
  stopEntryEdit();
  render();
  focusRecordButton(previousId, 'edit');
  $('entry-message').textContent = 'Editing cancelled.';
});
$('group-edit-value').addEventListener('input', () => {
  $('group-edit-error').hidden = true;
  $('group-edit-value').removeAttribute('aria-invalid');
  $('group-edit-value').setAttribute('aria-describedby', 'group-edit-help');
});
$('group-edit-form').addEventListener('submit', event => {
  event.preventDefault();
  if (editingGroupId === null) return;
  const id = editingGroupId;
  try {
    records = setReviewGroup(records, id, $('group-edit-value').value);
    if (editingRecordId === id) $('group').value = $('group-edit-value').value;
    stopGroupEdit();
    clearStatusUndo();
    clearFilters();
    render();
    focusRecordButton(id, 'edit');
    $('change-status-message').textContent = 'Group saved for ' + id + '.';
  } catch (exception) {
    $('group-edit-error').textContent = String(exception.message || exception);
    $('group-edit-error').hidden = false;
    $('group-edit-value').setAttribute('aria-invalid', 'true');
    $('group-edit-value').setAttribute('aria-describedby', 'group-edit-help group-edit-error');
    $('group-edit-error').focus();
  }
});
$('cancel-group-edit').addEventListener('click', () => {
  const id = editingGroupId;
  stopGroupEdit();
  focusRecordButton(id, 'edit');
});
$('undo-status').addEventListener('click', () => {
  try {
    records = undoReviewStatus(records, pendingStatusUndo);
    clearStatusUndo();
    clearFilters();
    render();
    $('change-status-message').textContent = 'Last review status change undone.';
  } catch {
    clearStatusUndo();
    $('change-status-message').textContent = 'Undo is unavailable because the entries have changed.';
  }
  $('count').focus();
});

function beginDownload(filename, content, type, message) {
  $('export-error').hidden = true;
  $('export-error').textContent = '';
  $('export-status').textContent = '';
  try {
    startLocalDownload({filename, content, type});
    $('export-status').textContent = message + ' Check your browser’s downloads.';
  } catch {
    $('export-error').textContent = 'The download could not start. Your entries are still here. Try again or choose another format.';
    $('export-error').hidden = false;
    $('export-error').focus();
  }
}
function visualSelection() {
  const partial=$('visual-scope').value==='visible';
  return {rows:partial?visibleRecords():records,options:{
    scope:partial?'Filtered entries':'All entries',total:records.length,
    filters:partial?['Search: '+JSON.stringify($('text-search').value),
      'Status: '+$('review-filter').value,'Source: '+JSON.stringify($('source-find').value),
      'Group: '+JSON.stringify($('group-find').value),'Ungrouped only: '+($('ungrouped-only').checked?'yes':'no')].join(' · '):''
  }};
}
function renderVisual() {
  $('visual-panel').hidden=!records.length;
  const {rows,options}=visualSelection();
  const scale=timelineScale(rows);
  $('download-gantt').disabled=!scale;
  $('download-visual').disabled=!scale;
  if(visualOffset>=rows.length)visualOffset=Math.max(0,Math.floor((rows.length-1)/20)*20);
  $('visual-summary').textContent=scale?options.scope+' · '+rows.length+' of '+records.length+' entries · '+prettyDay(isoDay(scale.first))+' – '+prettyDay(isoDay(scale.last)):
    'No entries match this view. Clear the filters or choose All entries.';
  $('visual-chart').replaceChildren();
  const previewOpen=$('chart-preview').open;
  if(scale&&previewOpen) {
    const svg=timelineSVG(rows,{...options,offset:visualOffset,limit:20});
    const parsed=new DOMParser().parseFromString(svg,'image/svg+xml');
    if(parsed.querySelector('parsererror'))throw Error('Timeline visual could not be drawn.');
    $('visual-chart').append(document.importNode(parsed.documentElement,true));
  }
  $('visual-page-note').textContent=rows.length?'Showing entries '+(visualOffset+1)+'–'+Math.min(rows.length,visualOffset+20)+' of '+rows.length+'. Downloads include the entire chosen view.':'';
  $('visual-prev').disabled=visualOffset===0;
  $('visual-next').disabled=visualOffset+20>=rows.length;
  $('visual-prev').hidden=$('visual-next').hidden=rows.length<=20;
}
$('visual-scope').addEventListener('change',()=>{visualOffset=0;$('visual-error').hidden=true;$('visual-status').textContent='';renderVisual();});
$('chart-preview').addEventListener('toggle',renderVisual);
$('visual-prev').addEventListener('click',()=>{visualOffset=Math.max(0,visualOffset-20);renderVisual();});
$('visual-next').addEventListener('click',()=>{visualOffset+=20;renderVisual();});
function downloadVisual(kind) {
  const {rows,options}=visualSelection();
  $('visual-error').hidden=true;
  $('visual-status').textContent='';
  try {
    const content=kind==='xlsx'?exportGantt(rows,options):timelineSVG(rows,options);
    startLocalDownload({filename:'evidence-timeline-'+(options.scope==='All entries'?'all':'filtered')+'.'+kind,
      content,type:kind==='xlsx'?'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'image/svg+xml;charset=utf-8'});
    $('visual-status').textContent=(kind==='xlsx'?'Excel Gantt':'Timeline visual')+' download started · '+rows.length+(rows.length===1?' entry.':' entries.')+' Check your browser’s downloads.';
  } catch(exception) {
    $('visual-error').textContent=String(exception.message||exception);
    $('visual-error').hidden=false;
    $('visual-error').focus();
  }
}
$('download-gantt').addEventListener('click',()=>downloadVisual('xlsx'));
$('download-visual').addEventListener('click',()=>downloadVisual('svg'));
function readableTimeline(rows, partial = false) {
  const ordered = [...rows].sort((a,b) => a.date.localeCompare(b.date) || a.sourceId.localeCompare(b.sourceId));
  const lines = [
    'Evidence & Timeline Builder',
    partial ? 'Filtered timeline — includes only matching entries.' : 'Complete timeline — includes every entry.',
    'Calendar dates. Review labels and related groups were assigned by the person preparing this timeline.',
    'Original values are JSON-quoted to preserve punctuation, spaces, and unusual characters.',
    'Entries: ' + ordered.length, ''
  ];
  for (const [index, record] of ordered.entries()) {
    lines.push((index + 1) + '. ' + record.date + (record.endDate?' – '+record.endDate:'') + ' | Source reference: ' + JSON.stringify(record.sourceId));
    lines.push('   Type: ' + record.kind + ' | Review status: ' + record.status);
    lines.push('   Related group: ' + JSON.stringify(record.group));
    lines.push('   Description: ' + JSON.stringify(record.claim), '');
  }
  return lines.join('\n') + '\n';
}
$('json').addEventListener('click', () => beginDownload(
  'evidence-timeline-exact.json',
  JSON.stringify({schema:'evidence-timeline-v1', records}, null, 2) + '\n',
  'application/json',
  'JSON download started. Keep this file to reopen your timeline.'
));
$('save-work').addEventListener('click', () => $('json').click());
$('csv').addEventListener('click', () => {
  try {
    const content = exportSafeEvidenceCSV(records);
    beginDownload('evidence-timeline-spreadsheet.csv', content, 'text/csv;charset=utf-8', 'Spreadsheet download started.');
  } catch {
    $('export-error').textContent = 'Spreadsheet export is unavailable for this text. Save JSON to keep the original values.';
    $('export-error').hidden = false;
    $('export-error').focus();
  }
});
$('download-readable').addEventListener('click', () => {
  if (!records.length) return;
  beginDownload('evidence-timeline-readable.txt', readableTimeline(records), 'text/plain;charset=utf-8', 'Complete timeline download started.');
});
$('download-filtered').addEventListener('click', () => {
  const visible = visibleRecords();
  if (!visible.length) return;
  const filters = [
    'Text search: ' + JSON.stringify($('text-search').value),
    'Review status: ' + JSON.stringify($('review-filter').value),
    'Exact source search: ' + JSON.stringify($('source-find').value),
    'Group search: ' + JSON.stringify($('group-find').value),
    'Ungrouped only: ' + ($('ungrouped-only').checked ? 'yes' : 'no')
  ];
  const preface = 'PARTIAL FILTERED VIEW — ' + visible.length + ' of ' + records.length + ' entries.\n' +
    'Filters at export time\n' + filters.join('\n') + '\n\n';
  beginDownload('evidence-timeline-filtered-view.txt', preface + readableTimeline(visible, true),
    'text/plain;charset=utf-8', 'Visible entries download started.');
});

const exampleRecords = [
  {sourceId:'EXAMPLE-MINUTES-001', date:'2026-01-12', claim:'The committee proposes opening the project on March 1.', status:'reported', kind:'source', group:'opening-date'},
  {sourceId:'EXAMPLE-EMAIL-002', date:'2026-01-19', claim:'A follow-up email suggests moving the opening date to March 15. It does not confirm a final decision.', status:'unresolved', kind:'source', group:'opening-date'},
  {sourceId:'EXAMPLE-NOTE-003', date:'2026-01-20', claim:'The reviewer needs to check the final decision before reporting an agreed opening date.', status:'unresolved', kind:'observation', group:'opening-date'}
];
function startBlank() {
  if ((records.length || $('claim').value || $('sourceId').value) &&
      !window.confirm('Start a blank timeline? Download a copy first if you want to keep your current entries.')) return;
  records = [];
  exampleMode = false;
  stopEntryEdit();
  stopGroupEdit();
  clearStatusUndo();
  clearFilters();
  $('entry-message').textContent = '';
  $('change-status-message').textContent = '';
  $('export-status').textContent = '';
  render();
  $('date').focus();
}
$('start-own').addEventListener('click', () => {
  if (!records.length) {
    $('date').focus();
    return;
  }
  startBlank();
});
$('start-fresh').addEventListener('click', startBlank);
$('clear').addEventListener('click', startBlank);
$('load-example').addEventListener('click', () => {
  if ((records.length || $('claim').value || $('sourceId').value) &&
      !window.confirm('Replace the current timeline with three fictional entries? Download your work first if you want to keep it.')) return;
  records = normalizeEvidence(exampleRecords);
  exampleMode = true;
  stopEntryEdit();
  stopGroupEdit();
  clearStatusUndo();
  clearFilters();
  $('entry-message').textContent = '';
  render();
  $('count').focus();
  $('change-status-message').textContent = 'Three fictional entries loaded. Try searching for March, editing an entry, or downloading the timeline.';
});
$('empty-example').addEventListener('click', () => $('load-example').click());

const resumePanel = $('resume-panel');
const input = $('resume-json');
const importFeedback = createImportFeedback(input, $('resume-json-help'), resumePanel);
$('open-saved').addEventListener('click', () => {
  resumePanel.open = true;
  input.focus();
});
input.addEventListener('change', async () => {
  const file = input.files?.[0];
  if (!file) return;
  importFeedback.begin();
  const initialRecords = records;
  input.disabled = true;
  try {
    const next = await readExactJSON(file);
    if (records !== initialRecords) throw Error('Entries changed while the file was being read. Choose the file again.');
    if (window.confirm(replacementConfirmation(previewReplacement(records, next)))) {
      records = next;
      exampleMode = false;
      stopEntryEdit();
      stopGroupEdit();
      clearStatusUndo();
      clearFilters();
      render();
      importFeedback.announce(next.length + ' entries opened. Your timeline is ready.');
      $('count').focus();
    } else importFeedback.announce('Opening cancelled. Your current entries are still here.');
  } catch (exception) {
    importFeedback.fail(String(exception.message || exception));
  } finally {
    input.value = '';
    input.disabled = false;
  }
});
render();
