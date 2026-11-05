// Accessible feedback for local JSON imports; no records leave the browser.
export function createImportFeedback(input, instructions, section) {
  const status = document.createElement('p');
  status.id = 'resume-json-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  const error = document.createElement('p');
  error.id = 'resume-json-error';
  error.className = 'error';
  error.tabIndex = -1;
  error.setAttribute('role', 'alert');
  error.hidden = true;
  input.setAttribute('aria-describedby', instructions.id);
  section.append(status, error);

  function clearError() {
    error.hidden = true;
    error.textContent = '';
    input.removeAttribute('aria-invalid');
    input.setAttribute('aria-describedby', instructions.id);
  }
  function begin() {
    clearError();
    status.textContent = 'Reading local JSON file…';
  }
  function announce(message) {
    clearError();
    status.textContent = message;
  }
  function fail(message) {
    status.textContent = '';
    error.textContent = 'Import failed: ' + message;
    error.hidden = false;
    input.setAttribute('aria-invalid', 'true');
    input.setAttribute('aria-describedby', instructions.id + ' ' + error.id);
    error.focus();
  }
  return {begin, announce, fail, clearError, status, error};
}
