// A single browser-local undo step for user-assigned review classifications.
// Source IDs, dates, evidence text and all unrelated records remain unchanged.
import {STATUS_OPTIONS, updateReviewStatus} from './reclassify.mjs';

export function changeReviewStatus(records, sourceId, status) {
  if (!Array.isArray(records) || typeof sourceId !== 'string' || !STATUS_OPTIONS.includes(status)) {
    throw Error('Invalid review status change');
  }
  const previous = records.find(row => row.sourceId === sourceId);
  if (!previous) throw Error('Source ID not found');
  const next = updateReviewStatus(records, sourceId, status);
  return {
    records: next,
    undo: previous.status === status ? null : Object.freeze({sourceId, before: previous.status, after: status})
  };
}

export function undoReviewStatus(records, change) {
  if (!change || typeof change.sourceId !== 'string' ||
      !STATUS_OPTIONS.includes(change.before) || !STATUS_OPTIONS.includes(change.after)) {
    throw Error('Invalid undo request');
  }
  const current = Array.isArray(records) && records.find(row => row.sourceId === change.sourceId);
  if (!current || current.status !== change.after) throw Error('Undo is no longer available');
  return updateReviewStatus(records, change.sourceId, change.before);
}
