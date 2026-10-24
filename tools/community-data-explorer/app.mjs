import {MAX_BYTES,readCsvBytes,compareRecords,evidenceExport} from "./engine.mjs";
const byId = id => document.getElementById(id);
const input = byId("csv"), label = byId("label"), left = byId("left"), right = byId("right");
const status = byId("status"), error = byId("error"), output = byId("comparison"), table = byId("records");
const compareButton = byId("compare"), exportButton = byId("export");
let records = [], latest = null, generation = 0;
function showError(message) { error.textContent = message; error.hidden = false; error.focus(); }
function clearError() { error.textContent = ""; error.hidden = true; }
function setStatus(message) { status.textContent = message; }
function reset() {
  records = []; latest = null; compareButton.disabled = true; exportButton.disabled = true;
  left.replaceChildren(); right.replaceChildren(); table.replaceChildren(); output.replaceChildren();
}
function addText(parent, tag, value) {
  const element = document.createElement(tag); element.textContent = String(value); parent.append(element); return element;
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
      r.estimate ?? "Missing",r.moe ?? "Missing"]) addText(tr,"td",value);
    body.append(tr);
  }
  table.replaceChildren(body);
  compareButton.disabled = records.length < 2;
  exportButton.disabled = false;
  setStatus(records.length + " records loaded locally. Preview shows up to 100. Source authenticity is not verified.");
}
input.addEventListener("change", async () => {
  const ticket = ++generation; reset(); clearError(); setStatus("Reading file locally…");
  const file = input.files?.[0];
  if (!file) { setStatus("No file selected."); return; }
  if (!/\.csv$/i.test(file.name) || file.size > MAX_BYTES) {
    showError("Choose a .csv file no larger than 2,000,000 bytes."); setStatus("Import failed."); return;
  }
  try {
    const bytes = await file.arrayBuffer();
    if (ticket !== generation) return;
    records = readCsvBytes(bytes,file.size);
    render();
  } catch (e) {
    if (ticket !== generation) return;
    reset(); showError(e instanceof Error ? e.message : "Unable to read CSV.");
    setStatus("Import failed. Existing results were cleared.");
  }
});
compareButton.addEventListener("click", () => {
  clearError();
  try {
    latest = compareRecords(records,left.value,right.value);
    output.replaceChildren();
    addText(output,"p",latest.comparable
      ? "Comparable on basic series, variable, period and geography gates. Difference (right minus left): " + latest.difference
      : "Direct comparison blocked.");
    for (const item of [...latest.reasons,...latest.cautions]) addText(output,"p",item);
    setStatus("Comparison reviewed. No statistical significance determination is made.");
  } catch (e) { latest = null; showError(e.message); }
});
for(const select of [left,right]) select.addEventListener("change", () => { latest = null; output.replaceChildren(); setStatus("Selection changed; run comparison again."); });
exportButton.addEventListener("click", () => {
  clearError();
  try {
    const evidence = evidenceExport(records,label.value,latest);
    const blob = new Blob([JSON.stringify(evidence,null,2)],{type:"application/json"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "community-data-evidence.json";
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    setStatus("Local JSON evidence exported; no CSV spreadsheet export is provided.");
  } catch (e) { showError(e.message); }
});
