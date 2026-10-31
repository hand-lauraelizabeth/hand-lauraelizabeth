import {MAX_BYTES,readCsvBytes,fingerprintCsv,compareRecords,evidenceExport} from "./engine.mjs";
const byId = id => document.getElementById(id);
const input = byId("csv"), label = byId("label"), left = byId("left"), right = byId("right");
const status = byId("status"), error = byId("error"), output = byId("comparison"), table = byId("records");
const compareButton = byId("compare"), exportButton = byId("export");
let records = [], latest = null, fingerprint = null, generation = 0;
function showError(message) { error.textContent = message; error.hidden = false; error.focus(); }
function clearError() { error.textContent = ""; error.hidden = true; }
function setStatus(message) { status.textContent = message; }
function reset() {
  records = []; latest = null; fingerprint = null; compareButton.disabled = true; exportButton.disabled = true;
  left.replaceChildren(); right.replaceChildren(); table.replaceChildren(); output.replaceChildren();
}
function addText(parent, tag, value) {
  const element = document.createElement(tag); element.textContent = String(value); parent.append(element); return element;
}
// Explain annotation semantics without implying that a suppressed or controlled MOE is zero.
function displayMeasure(raw, status) {
  // Preserve exact supplied digits in the preview; Number may round large decimals.
  if (status === "available") return raw;
  const labels = {
    missing:"missing",
    suppressed_insufficient_cases:"suppressed: insufficient cases",
    not_applicable:"not applicable",
    insufficient_observations:"insufficient observations",
    controlled_moe:"controlled: MOE not numeric",
    open_interval_moe:"open-ended median: MOE unavailable",
    insufficient_moe:"insufficient sample: MOE unavailable"
  };
  return "Not numeric (" + (labels[status] || "unavailable") + ")";
}
function render() {
  for (const record of records) {
    for (const select of [left,right]) {
      const option = document.createElement("option");
      option.value = record.source_id;
      option.textContent = record.source_id + " — " + record.geography + " (" + record.period_start + "–" + record.period_end + ")";
      select.append(option);
    }
  }
  if (records.length > 1) right.selectedIndex = 1;
  const body = document.createElement("tbody");
  for (const r of records.slice(0,100)) {
    const tr = document.createElement("tr");
    for (const value of [r.source_id,r.geography,r.variable,r.series,r.period_start+"–"+r.period_end,
      displayMeasure(r.estimate_raw,r.estimate_status),displayMeasure(r.moe_raw,r.moe_status)]) addText(tr,"td",value);
    body.append(tr);
  }
  table.replaceChildren(body);
  compareButton.disabled = records.length < 2;
  exportButton.disabled = false;
  setStatus(records.length + " records loaded locally. Preview shows up to 100. " + (fingerprint?.sha256 ? "Original file SHA-256 computed locally. " : "Original file SHA-256 unavailable. ") + "Source authenticity is not verified.");
}
input.addEventListener("change", async () => {
  const ticket = ++generation;
  const file = input.files?.[0];
  // Release the picker selection so the same corrected file can be retried.
  input.value = "";
  if (!file) { setStatus(records.length ? "Existing records preserved." : "No file selected."); return; }
  clearError();
  setStatus(records.length ? "Checking replacement locally; current records remain available." : "Reading file locally…");
  if (!/\.csv$/i.test(file.name) || file.size > MAX_BYTES) {
    showError("Choose a .csv file no larger than 2,000,000 bytes.");
    setStatus(records.length ? "Import failed; existing records preserved." : "Import failed.");
    return;
  }
  try {
    const bytes = await file.arrayBuffer();
    if (ticket !== generation) return;
    const imported = readCsvBytes(bytes,file.size);
    const computed = await fingerprintCsv(bytes);
    if (ticket !== generation) return;
    // A validated replacement must not silently destroy the current evidence.
    if (records.length && !window.confirm("Replace the current local records and comparison with this CSV? Cancel keeps your current evidence and export.")) {
      setStatus("Replacement cancelled; existing records and export preserved.");
      return;
    }
    reset();
    records = imported; fingerprint = computed; render();
  } catch (e) {
    if (ticket !== generation) return;
    showError(e instanceof Error ? e.message : "Unable to read CSV.");
    setStatus(records.length ? "Import failed; existing records preserved." : "Import failed.");
  }
});
compareButton.addEventListener("click", () => {
  clearError();
  try {
    latest = compareRecords(records,left.value,right.value);
    output.replaceChildren();
    addText(output,"p",latest.comparable
      ? "Comparable on basic series, variable, period and geography gates. Difference (right minus left): " + (latest.difference_exact ?? latest.difference)
      : "Direct comparison blocked.");
    for (const item of [...latest.reasons,...latest.cautions]) addText(output,"p",item);
    setStatus("Comparison reviewed. No statistical significance determination is made.");
  } catch (e) { latest = null; showError(e.message); }
});
for(const select of [left,right]) select.addEventListener("change", () => { latest = null; output.replaceChildren(); setStatus("Selection changed; run comparison again."); });
exportButton.addEventListener("click", () => {
  clearError();
  let url = null;
  let anchor = null;
  let started = false;
  try {
    const evidence = evidenceExport(records,label.value,latest,fingerprint);
    const blob = new Blob([JSON.stringify(evidence,null,2)],{type:"application/json"});
    url = URL.createObjectURL(blob);
    anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "community-data-evidence.json";
    document.body.append(anchor);
    anchor.click();
    started = true;
    // A click initiates a download; the browser may still refuse to save it.
    setStatus("Local JSON download started. Check your browser downloads; no CSV spreadsheet export is provided.");
  } catch {
    // Browser errors can contain local paths or filenames. Never display them.
    showError("Could not start the JSON download. Check browser download permissions and retry; your local records are preserved.");
    setStatus("JSON download could not be started; existing evidence preserved.");
  } finally {
    if (anchor) {
      try { anchor.remove(); } catch { /* The browser may already have detached it. */ }
    }
    if (url !== null) {
      if (started) {
        setTimeout(() => { try { URL.revokeObjectURL(url); } catch { /* Best-effort cleanup. */ } }, 1000);
      } else {
        try { URL.revokeObjectURL(url); } catch { /* Best-effort cleanup. */ }
      }
    }
  }
});
