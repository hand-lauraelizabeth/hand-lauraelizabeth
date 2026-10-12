const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Exercise the actual browser module against a minimal synthetic DOM.
// No fictional institution records enter the national dataset or published UI.
function fixture() {
  const source = fs.readFileSync(path.join(__dirname, "../college-program-search.js"), "utf8");
  const marker = "window.CollegeProgramSearch=Object.freeze({";
  assert.equal(source.split(marker).length, 2);
  const elements = new Map();
  function element(tag = "div") {
    return {
      tagName: tag, children: [], textContent: "", value: "", hidden: false,
      disabled: false, handlers: {},
      append(...xs) { this.children.push(...xs); },
      appendChild(x) { this.children.push(x); return x; },
      replaceChildren(...xs) { this.children = [...xs]; },
      addEventListener(kind, callback) { this.handlers[kind] = callback; },
      querySelector() { return null; },
      focus() {}
    };
  }
  const root = element();
  root.querySelector = selector => {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  };
  const document = {
    getElementById: id => id === "college-search" ? root : null,
    createElement: element,
    createTextNode: value => ({ textContent: String(value) })
  };
  const window = {};
  const setup = [
    'titles={"000001":"Zero Studies","000002":"Positive Studies","000003":"Unavailable Studies"};',
    "keys=Object.keys(titles);reportedCips=new Set(keys);",
    'positiveCips=new Set(["000002"]);zeroOnlyCips=new Set(["000001"]);',
    'index=new Map([["123456",[["000001","5",0,"reported"],["000002","5",7,"reported"],["000003","5",null,"missing_or_suppressed"]]]]);',
    "ready=true;enabled=true;"
  ].join("");
  vm.runInNewContext(source.replace(marker, setup + marker), { document, window });
  return { api: window.CollegeProgramSearch, elements };
}
function textOf(element) {
  return (element.textContent || "") + " " + (element.children || []).map(textOf).join(" ");
}
test("positive, zero-only and unavailable classifications are distinct", () => {
  const { api } = fixture();
  const zero = api.searchSuggestions("CIP 00.0001", 5).options[0];
  const positive = api.searchSuggestions("CIP 00.0002", 5).options[0];
  const unavailable = api.searchSuggestions("CIP 00.0003", 5).options[0];
  assert.equal(zero.zeroOnly, true);
  assert.equal(zero.positive, false);
  assert.equal(positive.positive, true);
  assert.equal(unavailable.positive, false);
  assert.equal(unavailable.zeroOnly, false);
  assert.equal(unavailable.reported, true);
});
test("zero-only suggestion and selection never assert current offering", () => {
  const { api, elements } = fixture();
  const query = elements.get("#cs-program-query");
  query.value = "CIP 00.0001";
  query.handlers.input();
  const button = elements.get("#cs-program-options").children[0].children[0];
  assert.match(textOf(button), /Reported zero awards/);
  button.handlers.click();
  assert.match(elements.get("#cs-program-status").textContent, /Zero awards do not establish/);
  assert.equal(api.matches("123456"), true);
});
test("cards distinguish positive, zero and suppressed observations", () => {
  const { api, elements } = fixture();
  elements.get("#cs-award-level").value = "5";
  const card = api.cardFor("123456");
  assert.match(textOf(card), /1 positive, 1 zero, 1 unavailable/);
  assert.match(textOf(card), /0 reported awards \(not proof of current availability\)/);
  assert.match(textOf(card), /count missing or suppressed/);
  assert.equal(api.matches("654321"), false);
  assert.ok(card.children.some(x => x.href === "https://nces.ed.gov/ipeds/complete-data-files/C2025_A.zip"));
});
