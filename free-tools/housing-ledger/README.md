# Housing Evidence Ledger (prototype)

A browser-local organizer for dated rent, deposit, repair, inspection, and communication records. Preserve exact source identifiers; record missing evidence rather than inferring facts. This tool does not determine legal rights, deadlines, payment status, or deposit entitlement. Do not upload personal housing records to a website.

Downloads contain saved records only. If an event correction is open and changed, the download status identifies that the unsaved correction was excluded without displaying private values. Switching to another event asks before discarding unsaved changes. Unchanged editors do not trigger warnings. Store exported JSON securely; it may contain personal housing records.

If a browser blocks a JSON download, the organizer shows a focused recovery message, retains the saved records in the current tab, and removes temporary download links and object URLs. A successful click means the download was **started**, not that the file was saved; verify it in your browser's downloads. Reopen the downloaded JSON locally to check your copy before closing the tab. Browser-local records are not persistent without an export.
