import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, "navigator JavaScript is present");

class Element {
  constructor(tag, document) {
    this.tag = tag; this.document = document; this.children = [];
    this.attrs = {}; this.events = {}; this.style = {};
    this.value = ""; this.checked = false; this.disabled = false;
    this.className = ""; this._text = ""; this.open = false;
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  setAttribute(key, value) {
    this.attrs[key] = value;
    if (key === "id") this.document.ids[value] = this;
    if (key === "class") this.className = value;
  }
  appendChild(element) { this.children.push(element); return element; }
  replaceChildren() { this.children = []; this._text = ""; }
  addEventListener(type, fn) { (this.events[type] ??= []).push(fn); }
  emit(type) { for (const fn of this.events[type] || []) fn(); }
  click() { this.emit("click"); }
  focus() {}
  scrollIntoView() {}
  remove() {}
  select() {}
}

function start() {
  const document = {
    ids: {},
    createElement(tag) { return new Element(tag, document); },
    getElementById(id) { return document.ids[id]; },
    execCommand() { return true; }
  };
  document.body = new Element("body", document);
  for (const id of ["pane","error","status","count","progress-label","fill","back","next","reset"])
    document.ids[id] = new Element("div", document);
  document.clipboardWrites = [];
  document.downloadPayloads = [];
  const navigator = { clipboard: { writeText: async (value) => { document.clipboardWrites.push(value); } } };
  const URL = { createObjectURL: () => "blob:test", revokeObjectURL: () => {} };
  class Blob { constructor(parts) { document.downloadPayloads.push(parts.join("")); } }
  new Function("document","navigator","URL","Blob","setTimeout",script)(
    document,navigator,URL,Blob,() => {}
  );
  return document;
}
function nodes(root, match) {
  const found = [];
  function visit(node) { if (match(node)) found.push(node); for (const child of node.children) visit(child); }
  visit(root);
  return found;
}
function resultTitle(document) {
  return nodes(document.ids.pane,n => n.tag === "h2")[0]?.textContent;
}
function chooseExample(name) {
  const document = start();
  const example = nodes(document.ids.pane,n => n.tag === "button" && n.textContent === name)[0];
  assert.ok(example, "Missing example: " + name);
  example.click();
  for(let step=0;step<6;step++) document.ids.next.click();
  return document;
}
function chooseCustom({goal,cat,tools=[],freq,pattern,outcome,scope,risk}) {
  const document = start();
  const input = document.ids.goal;
  input.value = goal; input.emit("input");
  const category = document.ids.category;
  category.value = cat; category.emit("change");
  document.ids.next.click();
  for (const name of tools) {
    const box = nodes(document.ids.pane,n => n.tag === "input" && n.attrs.value === name)[0];
    assert.ok(box, "Tool choice missing: " + name);
    box.checked = true; box.emit("change");
  }
  document.ids.next.click();
  for (const [index,choice] of [[2,freq],[3,pattern],[4,outcome]]) {
    const radio = nodes(document.ids.pane,n => n.tag === "input" && n.attrs.value === choice)[0];
    assert.ok(radio, "Radio option missing: " + index + " " + choice);
    radio.checked = true; radio.emit("change");
    document.ids.next.click();
  }
  for (const value of [scope,risk]) {
    const radio = nodes(document.ids.pane,n => n.tag === "input" && n.attrs.value === value)[0];
    assert.ok(radio, "Final radio missing: " + value);
    radio.checked = true; radio.emit("change");
  }
  document.ids.next.click();
  return document;
}

test("code parses and all 29 software entries are present", () => {
  assert.doesNotThrow(() => new Function(script));
  const list = html.match(/const apps=\[([\s\S]*?)\];/)?.[1] || "";
  const entries = [...list.matchAll(/\["[^"]+","[^"]+"\]/g)];
  assert.equal(entries.length, 29);
});

for (const [example,title] of [
  ["Clean a weekly spreadsheet","Use an existing feature"],
  ["Draft similar documents","Use a reusable prompt workflow"],
  ["Route new requests","Automate predictable steps"],
  ["Review complex requests","Pilot a supervised agent"],
  ["Build a public service","Build a focused custom tool"]
]) {
  test("example: " + example, () => {
    const doc=chooseExample(example);
    assert.equal(resultTitle(doc),title);
    assert.equal(nodes(doc.ids.pane,n=>n.className.includes("pathrow")).length,6);
    assert.equal(nodes(doc.ids.pane,n=>n.className==="kb").length,4);
    assert.equal(nodes(doc.ids.pane,n=>n.textContent.startsWith("Cost status:")).length,4);
  });
}

test("standard public form can use software already available",() => {
  const d=chooseCustom({goal:"Create a public registration form",cat:"service",tools:["gforms"],freq:"repeat",pattern:"same",outcome:"interface",scope:"one",risk:"routine"});
  assert.equal(resultTitle(d),"Use an existing feature");
});
test("interactive cost calculator requires a focused custom prototype",() => {
  const d=chooseCustom({goal:"Build an interactive calculator that estimates costs",cat:"service",tools:["wordpress"],freq:"repeat",pattern:"mixed",outcome:"interface",scope:"one",risk:"routine"});
  assert.equal(resultTitle(d),"Build a focused custom tool");
});
test("consequential external decisions do not recommend an autonomous agent",() => {
  const d=chooseCustom({goal:"Rank applicants, then send decisions automatically",cat:"workflow",tools:["asana"],freq:"trigger",pattern:"judgment",outcome:"act",scope:"many",risk:"high"});
  assert.notEqual(resultTitle(d),"Pilot a supervised agent");
});
test("cannot proceed without a task",() => {
  const d=start();
  d.ids.next.click();
  assert.match(d.ids.error.textContent,/Add a short task description/);
  assert.equal(d.ids.count.textContent,"Question 1 of 6");
});

test("every example returns an accessible worked example and three reusable prompts", () => {
  for (const label of ["Clean a weekly spreadsheet","Draft similar documents","Route new requests","Review complex requests","Build a public service"]) {
    const d=chooseExample(label);
    assert.equal(nodes(d.ids.pane,n=>n.className==="worked-example").length,1,label);
    const texts=nodes(d.ids.pane,n=>n.className==="prompt").map(n=>n.value);
    assert.equal(texts.length,3,label);
    assert.ok(texts.every(text=>text.includes("Do not invent")||text.includes("Do not")||text.includes("never claim")),label);
    assert.equal(nodes(d.ids.pane,n=>n.textContent==="Copy all three prompts").length,1,label);
  }
});

test("worked example selector changes its steps and downloaded brief", () => {
  const d=chooseExample("Clean a weekly spreadsheet");
  const selector=d.ids["worked-pick"];
  assert.ok(selector);
  selector.value="form"; selector.emit("change");
  const panel=nodes(d.ids.pane,n=>n.className==="worked-example")[0];
  assert.match(panel.textContent,/Google Forms \+ Sheets/);
  const download=nodes(d.ids.pane,n=>n.tag==="button"&&n.textContent.includes("Download decision brief"))[0];
  assert.ok(download);
  download.click();
  assert.equal(d.downloadPayloads.length,1);
  assert.match(d.downloadPayloads[0],/Collect requests with Google Forms \+ Sheets/);
  assert.match(d.downloadPayloads[0],/REUSABLE PROMPTS/);
  assert.match(d.downloadPayloads[0],/Verify before scaling/);
});

test("agent recipe forbids immediate external actions", () => {
  const d=chooseExample("Review complex requests");
  const prompts=nodes(d.ids.pane,n=>n.className==="prompt").map(n=>n.value);
  assert.match(prompts[1],/suggestion-only pilot/);
  assert.match(prompts[1],/prohibited actions/);
});

test("public form example includes response access check", () => {
  const d=chooseCustom({goal:"Create a public registration form",cat:"service",tools:["gforms"],freq:"repeat",pattern:"same",outcome:"interface",scope:"one",risk:"routine"});
  const panel=nodes(d.ids.pane,n=>n.className==="worked-example")[0];
  assert.match(panel.textContent,/Google Forms/);
  assert.match(panel.textContent,/permission/);
});
