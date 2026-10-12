(function () {
  "use strict";

  var PAGE_SIZE = 24;
  var EXPECTED_COUNT = 6243;
  var STATE_NAMES = {
    AK:"Alaska",AL:"Alabama",AR:"Arkansas",AS:"American Samoa",AZ:"Arizona",
    CA:"California",CO:"Colorado",CT:"Connecticut",DC:"District of Columbia",
    DE:"Delaware",FL:"Florida",FM:"Federated States of Micronesia",
    GA:"Georgia",GU:"Guam",HI:"Hawaii",IA:"Iowa",ID:"Idaho",IL:"Illinois",
    IN:"Indiana",KS:"Kansas",KY:"Kentucky",LA:"Louisiana",MA:"Massachusetts",
    MD:"Maryland",ME:"Maine",MH:"Marshall Islands",MI:"Michigan",MN:"Minnesota",
    MO:"Missouri",MP:"Northern Mariana Islands",MS:"Mississippi",MT:"Montana",
    NC:"North Carolina",ND:"North Dakota",NE:"Nebraska",NH:"New Hampshire",
    NJ:"New Jersey",NM:"New Mexico",NV:"Nevada",NY:"New York",OH:"Ohio",
    OK:"Oklahoma",OR:"Oregon",PA:"Pennsylvania",PR:"Puerto Rico",PW:"Palau",
    RI:"Rhode Island",SC:"South Carolina",SD:"South Dakota",TN:"Tennessee",
    TX:"Texas",UT:"Utah",VA:"Virginia",VI:"U.S. Virgin Islands",VT:"Vermont",
    WA:"Washington",WI:"Wisconsin",WV:"West Virginia",WY:"Wyoming"
  };
  var collator = new Intl.Collator("en", { sensitivity:"base", numeric:true });

  function normalize(value) {
    return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  }
  function resetFilterOptions() {
    return {name:"", state:"", sort:"name-asc", control:"", locale:"", size:""};
  }
  function matchesSizeBand(value, band) {
    if (!band) return true;
    if (!Number.isInteger(value) || value < 0) return false;
    if (band === "under-5000") return value < 5000;
    if (band === "5000-14999") return value >= 5000 && value < 15000;
    if (band === "15000-plus") return value >= 15000;
    return false;
  }
  function countUnknowns(records) {
    return {
      total: records.length,
      control: records.filter(function (r) { return r.control === null; }).length,
      locale: records.filter(function (r) { return r.locale === null; }).length,
      size: records.filter(function (r) { return r.undergraduate_size === null; }).length
    };
  }
  function filterSchools(records, options) {
    var name = normalize(options.name);
    var state = options.state || "";
    var control = options.control || "";
    var locale = options.locale || "";
    var size = options.size || "";
    var sort = options.sort === "name-desc" ? -1 : 1;
    return records.filter(function (record) {
      return (!name || normalize(record.name).includes(name)) &&
        (!state || record.state === state) &&
        (!control || record.control === control) &&
        (!locale || record.locale === locale) &&
        matchesSizeBand(record.undergraduate_size, size);
    }).sort(function (a, b) {
      var byName = collator.compare(a.name, b.name);
      return sort * (byName || collator.compare(a.unitid, b.unitid));
    });
  }
  function validatePayload(payload) {
    if (!payload || payload.source !== "College Scorecard" ||
        payload.source_release !== "2026-06-10" ||
        !payload.institutions || typeof payload.institutions !== "object" ||
        Array.isArray(payload.institutions)) {
      throw new Error("The national data has an unexpected format.");
    }
    var entries = Object.entries(payload.institutions);
    if (entries.length !== EXPECTED_COUNT) {
      throw new Error("The national dataset is incomplete.");
    }
    return entries.map(function (entry) {
      var id = entry[0], r = entry[1];
      if (!/^\d{6,8}$/.test(id) || !r ||
          typeof r.name !== "string" || !r.name.trim() ||
          typeof r.city !== "string" || !r.city.trim() ||
          typeof r.state !== "string" || !/^[A-Z]{2}$/.test(r.state) ||
          (r.url !== null && (typeof r.url !== "string" || !/^https?:\/\//i.test(r.url))) ||
          !Object.prototype.hasOwnProperty.call(r, "control") ||
          !["public","private_nonprofit","private_for_profit",null].includes(r.control) ||
          !Object.prototype.hasOwnProperty.call(r, "locale") ||
          !["city","suburb","town","rural",null].includes(r.locale) ||
          !Object.prototype.hasOwnProperty.call(r, "undergraduate_size") ||
          !(r.undergraduate_size === null ||
            (Number.isInteger(r.undergraduate_size) && r.undergraduate_size >= 0))) {
        throw new Error("An institution record failed validation.");
      }
      return {unitid:id, name:r.name, city:r.city, state:r.state, url:r.url,
        control:r.control, locale:r.locale, undergraduate_size:r.undergraduate_size};
    });
  }

  // Pure functions are exposed for later unit tests; the UI has no dependencies.
  if (typeof window !== "undefined") {
    window.CollegeSearchCore = Object.freeze({filterSchools:filterSchools, matchesSizeBand:matchesSizeBand, countUnknowns:countUnknowns, resetFilterOptions:resetFilterOptions, validatePayload:validatePayload});
  }

  var root = document.getElementById("college-search");
  if (!root) return;
  var nameInput = root.querySelector("#cs-name");
  var stateSelect = root.querySelector("#cs-state");
  var sortSelect = root.querySelector("#cs-sort");
  var controlSelect = root.querySelector("#cs-control");
  var localeSelect = root.querySelector("#cs-locale");
  var sizeSelect = root.querySelector("#cs-size");
  var clearButton = root.querySelector("#cs-clear");
  var moreButton = root.querySelector("#cs-show-more");
  var list = root.querySelector("#cs-results-list");
  var count = root.querySelector("#cs-result-count");
  var activeList = root.querySelector("#cs-active-list");
  var activeNone = root.querySelector("#cs-active-none");
  var activeSort = root.querySelector("#cs-active-sort");
  var empty = root.querySelector("#cs-empty");
  var section = root.querySelector("#cs-results-section");
  var progress = root.querySelector("#cs-load-status");
  var errorBox = root.querySelector("#cs-error");
  var errorText = root.querySelector("#cs-error-text");
  var retryButton = root.querySelector("#cs-retry");
  var completeness = root.querySelector("#cs-data-completeness");
  var coverageTotal = root.querySelector("#cs-coverage-total");
  var controlUnknown = root.querySelector("#cs-control-unknown");
  var localeUnknown = root.querySelector("#cs-locale-unknown");
  var sizeUnknown = root.querySelector("#cs-size-unknown");
  var records = [], matches = [], rendered = 0;
  var loading = false;

  function setControls(enabled) {
    [nameInput, stateSelect, sortSelect, controlSelect, localeSelect, sizeSelect].forEach(function (element) {
      element.disabled = !enabled;
    });
    clearButton.disabled = !enabled || !hasChanges();
  }
  function hasChanges() {
    return !!nameInput.value || !!stateSelect.value || !!controlSelect.value ||
      !!localeSelect.value || !!sizeSelect.value || sortSelect.value !== "name-asc" ||
      rendered > PAGE_SIZE;
  }
  function showDataCompleteness() {
    var missing = countUnknowns(records);
    coverageTotal.textContent = missing.total.toLocaleString("en-US");
    controlUnknown.textContent = missing.control.toLocaleString("en-US");
    localeUnknown.textContent = missing.locale.toLocaleString("en-US");
    sizeUnknown.textContent = missing.size.toLocaleString("en-US");
    completeness.hidden = false;
  }
  function stateOptions() {
    var codes = Array.from(new Set(records.map(function (r) { return r.state; })));
    codes.sort(function (a, b) {
      return collator.compare(STATE_NAMES[a] || a, STATE_NAMES[b] || b);
    });
    stateSelect.replaceChildren(new Option("All states and territories", ""));
    codes.forEach(function (code) {
      stateSelect.add(new Option((STATE_NAMES[code] || code) + " (" + code + ")", code));
    });
  }
  function makeCard(record) {
    var item = document.createElement("li");
    item.className = "cs-card";
    var heading = document.createElement("h3");
    heading.textContent = record.name;
    var locality = document.createElement("p");
    locality.textContent = record.city + ", " + record.state;
    var unitid = document.createElement("p");
    unitid.className = "cs-visually-hidden";
    unitid.textContent = "Institution identifier " + record.unitid;
    item.append(heading, locality, unitid);
    if (record.url) {
      var link = document.createElement("a");
      link.textContent = "Visit " + record.name + " website";
      link.href = record.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      var screenReader = document.createElement("span");
      screenReader.className = "cs-visually-hidden";
      screenReader.textContent = " in " + record.city + ", " + record.state + " (opens in a new tab)";
      link.appendChild(screenReader);
      item.appendChild(link);
    } else {
      var unknown = document.createElement("span");
      unknown.className = "cs-unavailable";
      unknown.textContent = "School website not reported";
      item.appendChild(unknown);
    }
    return item;
  }
  function updateActiveSelections() {
    var selections = [];
    if (normalize(nameInput.value)) selections.push("School name: “" + nameInput.value.trim() + "”");
    if (stateSelect.value) selections.push("State or territory: " + stateSelect.selectedOptions[0].textContent);
    if (controlSelect.value) selections.push("Institution control: " + controlSelect.selectedOptions[0].textContent);
    if (localeSelect.value) selections.push("Campus setting: " + localeSelect.selectedOptions[0].textContent);
    if (sizeSelect.value) selections.push("Undergraduate size: " + sizeSelect.selectedOptions[0].textContent);
    var fragment = document.createDocumentFragment();
    selections.forEach(function (label) {
      var item = document.createElement("li");
      item.textContent = label;
      fragment.appendChild(item);
    });
    activeList.replaceChildren(fragment);
    activeList.hidden = selections.length === 0;
    activeNone.hidden = selections.length !== 0;
    activeSort.textContent = "Sort: " + sortSelect.selectedOptions[0].textContent;
  }
  function render(append) {
    var start = append ? rendered : 0;
    if (!append) {
      rendered = 0;
      list.replaceChildren();
    }
    var end = Math.min(start + PAGE_SIZE, matches.length);
    var fragment = document.createDocumentFragment();
    for (var i=start; i<end; i++) fragment.appendChild(makeCard(matches[i]));
    list.appendChild(fragment);
    rendered = end;
    count.textContent = matches.length.toLocaleString("en-US") +
      (matches.length === 1 ? " school" : " schools") + " found" +
      (matches.length ? " · showing " + rendered.toLocaleString("en-US") : "");
    empty.hidden = matches.length !== 0;
    moreButton.hidden = rendered >= matches.length;
    moreButton.textContent = "Show " + Math.min(PAGE_SIZE, matches.length - rendered) + " more";
    updateActiveSelections();
    clearButton.disabled = !hasChanges();
  }
  function applyFilters() {
    matches = filterSchools(records, {
      name:nameInput.value, state:stateSelect.value, sort:sortSelect.value,
      control:controlSelect.value, locale:localeSelect.value, size:sizeSelect.value
    });
    render(false);
  }
  function clear() {
    var defaults = resetFilterOptions();
    nameInput.value = defaults.name;
    stateSelect.value = defaults.state;
    sortSelect.value = defaults.sort;
    controlSelect.value = defaults.control;
    localeSelect.value = defaults.locale;
    sizeSelect.value = defaults.size;
    applyFilters();
    nameInput.focus();
  }
  function showError(message) {
    completeness.hidden = true;
    progress.hidden = true;
    errorText.textContent = message;
    errorBox.hidden = false;
    section.hidden = true;
    setControls(false);
  }
  async function loadData() {
    if (loading) return;
    loading = true;
    progress.hidden = false;
    progress.dataset.state = "loading";
    progress.textContent = "Loading national college data…";
    errorBox.hidden = true;
    section.hidden = true;
    completeness.hidden = true;
    retryButton.disabled = true;
    setControls(false);
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 20000);
    try {
      var src = root.getAttribute("data-src");
      if (!src) throw new Error("The data source is not configured.");
      var response = await fetch(src, {signal:controller.signal, credentials:"omit"});
      if (!response.ok) throw new Error("Data request failed (" + response.status + ").");
      var payload = await response.json();
      records = validatePayload(payload);
      stateOptions();
      showDataCompleteness();
      matches = filterSchools(records, resetFilterOptions());
      rendered = 0;
      nameInput.value = "";
      stateSelect.value = "";
      sortSelect.value = "name-asc";
      controlSelect.value = "";
      localeSelect.value = "";
      sizeSelect.value = "";
      section.hidden = false;
      progress.hidden = true;
      render(false);
      setControls(true);
    } catch (e) {
      // No cached or fictional records are substituted on failure.
      records = [];
      matches = [];
      showError("Unable to load and verify the national college data. Check your connection and try again.");
    } finally {
      clearTimeout(timer);
      loading = false;
      retryButton.disabled = false;
    }
  }
  nameInput.addEventListener("input", applyFilters);
  stateSelect.addEventListener("change", applyFilters);
  sortSelect.addEventListener("change", applyFilters);
  controlSelect.addEventListener("change", applyFilters);
  localeSelect.addEventListener("change", applyFilters);
  sizeSelect.addEventListener("change", applyFilters);
  clearButton.addEventListener("click", clear);
  moreButton.addEventListener("click", function () { render(true); });
  retryButton.addEventListener("click", loadData);
  loadData();
}());
