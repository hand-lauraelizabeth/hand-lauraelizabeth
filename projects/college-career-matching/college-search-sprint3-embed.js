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
    return {name:"", state:"", sort:"name-asc", control:"", locale:"", size:"", cities:[], netMax:null, costMax:null, satRange:null, actRange:null, ownSAT:null, ownACT:null};
  }
  function matchesSizeBand(value, band) {
    if (!band) return true;
    if (!Number.isInteger(value) || value < 0) return false;
    if (band === "under-5000") return value < 5000;
    if (band === "5000-14999") return value >= 5000 && value < 15000;
    if (band === "15000-plus") return value >= 15000;
    return false;
  }
  // A score interval limits schools by the published institutional score measure,
  // not by a prediction about an individual's chance of admission.
  function matchesScoreRange(value, range) {
    return !range || (Number.isFinite(value) && value >= range.min && value <= range.max);
  }
  function admissionsCategory(record, ownSAT, ownACT) {
    var labels=[];
    function category(score,low,median,high) {
      if (!Number.isFinite(score) || !Number.isFinite(low) || !Number.isFinite(median) || !Number.isFinite(high) || low > median || median > high) return null;
      return score < low ? "REACH" : score > high ? "SAFETY" : "TARGET";
    }
    if (Number.isFinite(ownSAT)) {
      var satLabel=category(ownSAT,record.sat_p25,record.sat_p50,record.sat_p75);
      if (satLabel) labels.push(satLabel);
    }
    if (Number.isFinite(ownACT)) {
      var actLabel=category(ownACT,record.act_p25,record.act_p50,record.act_p75);
      if (actLabel) labels.push(actLabel);
    }
    // Avoid an arbitrary decision when the two examinations disagree.
    return labels.length && labels.every(function(v){return v===labels[0];}) ? labels[0] : null;
  }
  function countUnknowns(records) {
    return {
      total: records.length,
      control: records.filter(function (r) { return r.control === null; }).length,
      locale: records.filter(function (r) { return r.locale === null; }).length,
      size: records.filter(function (r) { return r.undergraduate_size === null; }).length,
      net: records.filter(function (r) { return r.average_net_price === null; }).length,
      cost: records.filter(function (r) { return r.annual_cost === null; }).length,
      sat: records.filter(function (r) { return !Number.isFinite(r.sat_avg); }).length,
      act: records.filter(function (r) { return !Number.isFinite(r.act_mid); }).length,
      satBands: records.filter(function (r) { return !Number.isFinite(r.sat_p25) || !Number.isFinite(r.sat_p75); }).length,
      actBands: records.filter(function (r) { return !Number.isFinite(r.act_p25) || !Number.isFinite(r.act_p75); }).length
    };
  }
  function filterSchools(records, options) {
    var name = normalize(options.name);
    var state = options.state || "";
    var control = options.control || "";
    var locale = options.locale || "";
    var size = options.size || "";
    var cities = options.cities || [];
    var netMax = Number.isFinite(options.netMax) ? options.netMax : null;
    var costMax = Number.isFinite(options.costMax) ? options.costMax : null;
    var sort = options.sort || "name-asc";
    var satRange = options.satRange || null;
    var actRange = options.actRange || null;
    return records.filter(function (record) {
      return (!name || normalize(record.name).includes(name)) &&
        (!state || record.state === state) &&
        (!control || record.control === control) &&
        (!locale || record.locale === locale) &&
        matchesSizeBand(record.undergraduate_size, size) &&
        (!cities.length || cities.includes(record.state + "|" + record.city)) &&
        (netMax === null || (record.average_net_price !== null && record.average_net_price <= netMax)) &&
        (costMax === null || (record.annual_cost !== null && record.annual_cost <= costMax)) &&
        matchesScoreRange(record.sat_avg, satRange) &&
        matchesScoreRange(record.act_mid, actRange) &&
        (typeof window==='undefined' || !window.CollegeProgramSearch || window.CollegeProgramSearch.matches(record.unitid));
    }).sort(function (a, b) {
      // Missing average net price is always last for either price direction.
      // Ties are stable by school name and exact Scorecard source record key.
      var byName = collator.compare(a.name, b.name) || collator.compare(a.unitid, b.unitid);
      if (sort === "net-asc" || sort === "net-desc") {
        var aHasPrice = Number.isFinite(a.average_net_price);
        var bHasPrice = Number.isFinite(b.average_net_price);
        if (aHasPrice !== bHasPrice) return aHasPrice ? -1 : 1;
        if (aHasPrice) {
          var byPrice = a.average_net_price - b.average_net_price;
          if (byPrice !== 0) return sort === "net-asc" ? byPrice : -byPrice;
        }
        return byName;
      }
      return sort === "name-desc" ? -byName : byName;
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
            (Number.isInteger(r.undergraduate_size) && r.undergraduate_size >= 0)) ||
          !["annual_cost","average_net_price","tuition_in_state","tuition_out_state"].every(function (field) {
            return Object.prototype.hasOwnProperty.call(r,field) &&
              (r[field] === null || Number.isInteger(r[field]));
          })) {
        throw new Error("An institution record failed validation.");
      }
      return {unitid:id, name:r.name, city:r.city, state:r.state, url:r.url,
        control:r.control, locale:r.locale, undergraduate_size:r.undergraduate_size,
        annual_cost:r.annual_cost, average_net_price:r.average_net_price,
        tuition_in_state:r.tuition_in_state, tuition_out_state:r.tuition_out_state};
    });
  }

  // Pure functions are exposed for later unit tests; the UI has no dependencies.
  if (typeof window !== "undefined") {
    window.CollegeSearchCore = Object.freeze({filterSchools:filterSchools, matchesSizeBand:matchesSizeBand, matchesScoreRange:matchesScoreRange, admissionsCategory:admissionsCategory, countUnknowns:countUnknowns, resetFilterOptions:resetFilterOptions, validatePayload:validatePayload});
  }

  var root = document.getElementById("college-search");
  if (!root) return;
  var nameInput = root.querySelector("#cs-name");
  var stateSelect = root.querySelector("#cs-state");
  var sortSelect = root.querySelector("#cs-sort");
  var controlSelect = root.querySelector("#cs-control");
  var localeSelect = root.querySelector("#cs-locale");
  var sizeSelect = root.querySelector("#cs-size");
  var citySearch = root.querySelector("#cs-city-search");
  var cityOptions = root.querySelector("#cs-city-options");
  var cityFeedback = root.querySelector("#cs-city-feedback");
  var cityChosen = root.querySelector("#cs-city-selected");
  var citySummaryCount = root.querySelector("#cs-city-count");
  var netSlider = root.querySelector("#cs-net-max");
  var costSlider = root.querySelector("#cs-cost-max");
  var netOutput = root.querySelector("#cs-net-output");
  var costOutput = root.querySelector("#cs-cost-output");
  var netUnknown = root.querySelector("#cs-net-unknown");
  var costUnknown = root.querySelector("#cs-cost-unknown");
  var satLow=root.querySelector("#cs-sat-low"), satHigh=root.querySelector("#cs-sat-high");
  var actLow=root.querySelector("#cs-act-low"), actHigh=root.querySelector("#cs-act-high");
  var ownSATInput=root.querySelector("#cs-own-sat"), ownACTInput=root.querySelector("#cs-own-act");
  var satLowOutput=root.querySelector("#cs-sat-low-output"),satHighOutput=root.querySelector("#cs-sat-high-output");
  var actLowOutput=root.querySelector("#cs-act-low-output"),actHighOutput=root.querySelector("#cs-act-high-output");
  var satUnknown=root.querySelector("#cs-sat-unknown"),actUnknown=root.querySelector("#cs-act-unknown");
  var satBandsUnknown=root.querySelector("#cs-sat-band-unknown"),actBandsUnknown=root.querySelector("#cs-act-band-unknown");
  var scoresStatus=root.querySelector("#cs-scores-status");
  var scoresReady=false;
  function rangeValue(lo,hi,min,max) {
    var a=Number(lo.value),b=Number(hi.value);
    return a===min && b===max ? null : {min:a,max:b};
  }
  function ownScore(input,min,max) {
    if (!input.value.trim()) return null;
    var number=Number(input.value);
    return Number.isInteger(number)&&number>=min&&number<=max ? number : null;
  }
  function currentSATRange(){return scoresReady ? rangeValue(satLow,satHigh,400,1600) : null;}
  function currentACTRange(){return scoresReady ? rangeValue(actLow,actHigh,1,36) : null;}
  function drawScoreLabels(){
    satLowOutput.value=satLow.value; satHighOutput.value=satHigh.value;
    actLowOutput.value=actLow.value; actHighOutput.value=actHigh.value;
  }
  function changeScoreRange(lo,hi,which) {
    if(Number(lo.value)>Number(hi.value)) {
      if(which==="low")hi.value=lo.value;else lo.value=hi.value;
    }
    drawScoreLabels();applyFilters();
  }
  function validateScoreOverlay(payload,allRecords) {
    if(!payload || payload.schema_version!==3 || payload.source!=="College Scorecard" ||
      payload.source_release!=="2026-06-10" || payload.school_count!==EXPECTED_COUNT ||
      !payload.institutions || Array.isArray(payload.institutions)) throw Error("Invalid score source.");
    var known=new Set(allRecords.map(function(r){return r.unitid;}));
    var data=payload.institutions;
    if(payload.percentile_source_status!=="verified_2026_scorecard" ||
       payload.source_archive_sha256!=="f56a181b000ca4914e924c16b6b81dcc656e25aeb2ac68ab7d271ac0f29ffd58") {
      throw Error("Percentile provenance cannot be verified.");
    }
    var sources=payload.source_registry;
    if(!sources||typeof sources!=="object"||Array.isArray(sources)||
       !sources.scorecard_2026||
       sources.scorecard_2026.url!=="https://collegescorecard.ed.gov/data/"||
       !Number.isInteger(payload.verified_band_counts?.sat_complete_bands)||
       !Number.isInteger(payload.verified_band_counts?.act_complete_bands)||
       payload.verified_band_counts.sat_complete_bands<1051||
       payload.verified_band_counts.act_complete_bands<965||
       payload.verified_band_counts.sat_complete_bands>EXPECTED_COUNT||
       payload.verified_band_counts.act_complete_bands>EXPECTED_COUNT)throw Error("Source registry or coverage could not be verified.");
    if(payload.historical_archive_sha256!=="bfe3add63069fea1fa61c8b910bfaef9d29baa3ae68702e6595b04d2023293a1" ||
       !payload.historical_backfill ||
       payload.historical_backfill.do_not_mix_years_within_exam!==true ||
       payload.historical_backfill.report_as_historical!==true)
      throw Error("Historical source validation failed.");
    Object.keys(sources).forEach(function(id){
      var source=sources[id];
      if(source.is_historical &&
        (!["Fall 2022","Fall 2023"].includes(source.cohort)||
         source.source_archive_sha256!==payload.historical_archive_sha256||
         !/^MERGED202[23]_[0-9]{2}_PP\.csv$/.test(source.source_file)))throw Error("Unverified historical source.");
      if(!source||typeof source.provider!=="string"||typeof source.cohort!=="string"||
         !source.url||!/^https:\/\//.test(source.url))throw Error("Invalid source metadata.");
    });
    for(var id of Object.keys(data)) {
      if(!known.has(id))throw Error("Score UNITID not in the national catalog.");
      var v=data[id];
      if(!Array.isArray(v)||v.length!==10)throw Error("Malformed score row.");
      if(![8,9].every(function(i){return v[i]===null||(typeof v[i]==="string" && Object.hasOwn(sources,v[i]));}))throw Error("Unknown score source.");
      if((v[0]!==null || v[2]!==null) && !v[8])throw Error("SAT score source missing.");
      if((v[1]!==null || v[5]!==null) && !v[9])throw Error("ACT score source missing.");
      function valid(value,min,max){return value==null||(Number.isInteger(value)&&value>=min&&value<=max);}
      if(!valid(v[0],400,1600)||!valid(v[1],1,36) ||
        ![2,3,4].every(function(i){return valid(v[i],400,1600);}) ||
        ![5,6,7].every(function(i){return valid(v[i],1,36);})) throw Error("Score out of range.");
      function ordered(a,b,c){return (a==null&&b==null&&c==null)||
        (a!=null&&b!=null&&c!=null&&a<=b&&b<=c);}
      if(!ordered(v[2],v[3],v[4])||!ordered(v[5],v[6],v[7]))throw Error("Invalid score percentiles.");
    }
    return data;
  }
  async function loadScores(signal){
    scoresReady=false;
    var source=root.getAttribute("data-scores-src");
    if(!source){scoresStatus.textContent="Test-score filters unavailable: no data source configured.";return;}
    try{
      var response=await fetch(source,{signal:signal,credentials:"omit"});
      if(!response.ok)throw Error("Scores request failed.");
      var payload=await response.json();
      var data=validateScoreOverlay(payload,records);
      var sourceRegistry=payload.source_registry;
      records.forEach(function(r){
        var v=data[r.unitid]||[];
        r.sat_avg=v[0]??null;r.act_mid=v[1]??null;
        r.sat_p25=v[2]??null;r.sat_p50=v[3]??null;r.sat_p75=v[4]??null;
        r.act_p25=v[5]??null;r.act_p50=v[6]??null;r.act_p75=v[7]??null;
        r.sat_source=(v[8]&&sourceRegistry[v[8]])||null;
        r.act_source=(v[9]&&sourceRegistry[v[9]])||null;
      });
      scoresReady=true;
      var bandCounts=payload.verified_band_counts;
      scoresStatus.textContent="SAT uses a reported institutional average; ACT uses a reported midpoint or historical median. Verified 2022–23 admissions cohorts fill exam-level gaps only when 2024 metrics are unavailable. "+
        (bandCounts ? ("Percentile data: "+bandCounts.sat_complete_bands+" SAT and "+bandCounts.act_complete_bands+" ACT institutions. ") : "Percentile bands are not yet included in this verified national extract. ")+
        "Comparison labels require a personal score and verified complete percentile data; TOEFL is not included in the federal source.";
    }catch(err){
      scoresStatus.textContent="SAT/ACT score filters currently unavailable; the other college filters still work.";
    }
  }
  var selectedCities = new Set(), cityCatalog = [];
  function money(value) { return "$" + value.toLocaleString("en-US"); }
  function activeMax(input) {
    return Number(input.value) < Number(input.max) ? Number(input.value) : null;
  }
  function drawMoneyLabels() {
    netOutput.textContent = activeMax(netSlider) === null ? "Any" : money(Number(netSlider.value));
    costOutput.textContent = activeMax(costSlider) === null ? "Any" : money(Number(costSlider.value));
  }
  function populateCostSliders() {
    [[netSlider,"average_net_price"],[costSlider,"annual_cost"]].forEach(function (pair) {
      var values = records.map(function (r) { return r[pair[1]]; }).filter(Number.isFinite);
      var ceiling = Math.max(100000, Math.ceil((Math.max.apply(null, values) + 5000) / 5000) * 5000);
      pair[0].max = String(ceiling);
      pair[0].value = String(ceiling);
    });
    drawMoneyLabels();
  }
  function redrawSelectedCities() {
    cityChosen.replaceChildren();
    Array.from(selectedCities).sort(function (a,b) { return collator.compare(a,b); }).forEach(function (key) {
      var parts = key.split("|"), button=document.createElement("button");
      button.type="button"; button.className="cs-city-chip";
      button.textContent="Remove " + parts[1] + ", " + parts[0] + " ×";
      button.addEventListener("click",function () {
        selectedCities.delete(key);redrawSelectedCities();renderCityOptions();applyFilters();
      });
      cityChosen.appendChild(button);
    });
    citySummaryCount.textContent = selectedCities.size ? "(" + selectedCities.size + " selected)" : "(all cities)";
  }
  function renderCityOptions() {
    cityOptions.replaceChildren();
    var query=normalize(citySearch.value);
    if(query.length < 2) {
      cityFeedback.textContent="Type at least 2 letters to find cities.";
      return;
    }
    var found=cityCatalog.filter(function (r) { return normalize(r.label).includes(query); });
    found.slice(0,30).forEach(function (r) {
      var li=document.createElement("li"), button=document.createElement("button");
      button.type="button";button.className="cs-city-option";
      button.textContent=(selectedCities.has(r.key)?"✓ ":"+ ") + r.label;
      button.setAttribute("aria-pressed",String(selectedCities.has(r.key)));
      button.addEventListener("click",function () {
        if(selectedCities.has(r.key))selectedCities.delete(r.key);else selectedCities.add(r.key);
        redrawSelectedCities();renderCityOptions();applyFilters();
      });
      li.appendChild(button);cityOptions.appendChild(li);
    });
    cityFeedback.textContent=found.length ? "Showing " + Math.min(30,found.length) +
      " of " + found.length + " matching cities. Select to add or remove." : "No matching cities.";
  }
  function populateCities() {
    var map=new Map();
    records.forEach(function (r) {
      var key=r.state + "|" + r.city;
      if(!map.has(key))map.set(key,{key:key,label:r.city + ", " + r.state});
    });
    cityCatalog=Array.from(map.values()).sort(function(a,b){return collator.compare(a.label,b.label);});
    redrawSelectedCities();renderCityOptions();
  }
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
    [nameInput, stateSelect, sortSelect, controlSelect, localeSelect, sizeSelect, citySearch, netSlider, costSlider].forEach(function (element) {
      element.disabled = !enabled;
    });
    [satLow,satHigh,actLow,actHigh,ownSATInput,ownACTInput].forEach(function(element){element.disabled=!enabled||!scoresReady;});
    if(window.CollegeProgramSearch)window.CollegeProgramSearch.setEnabled(enabled);
    clearButton.disabled = !enabled || !hasChanges();
  }
  function hasChanges() {
    return !!nameInput.value || !!stateSelect.value || !!controlSelect.value ||
      !!localeSelect.value || !!sizeSelect.value || selectedCities.size > 0 ||
      activeMax(netSlider) !== null || activeMax(costSlider) !== null ||
      currentSATRange()!==null || currentACTRange()!==null ||
      !!ownSATInput.value || !!ownACTInput.value || sortSelect.value !== "name-asc" ||
      (window.CollegeProgramSearch && window.CollegeProgramSearch.selected()) || rendered > PAGE_SIZE;
  }
  function showDataCompleteness() {
    var missing = countUnknowns(records);
    coverageTotal.textContent = missing.total.toLocaleString("en-US");
    controlUnknown.textContent = missing.control.toLocaleString("en-US");
    localeUnknown.textContent = missing.locale.toLocaleString("en-US");
    sizeUnknown.textContent = missing.size.toLocaleString("en-US");
    netUnknown.textContent = missing.net.toLocaleString("en-US");
    costUnknown.textContent = missing.cost.toLocaleString("en-US");
    satUnknown.textContent = scoresReady ? missing.sat.toLocaleString("en-US") : "Unavailable";
    actUnknown.textContent = scoresReady ? missing.act.toLocaleString("en-US") : "Unavailable";
    satBandsUnknown.textContent = scoresReady ? missing.satBands.toLocaleString("en-US") : "Unavailable";
    actBandsUnknown.textContent = scoresReady ? missing.actBands.toLocaleString("en-US") : "Unavailable";
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
    var category=admissionsCategory(record,ownScore(ownSATInput,400,1600),ownScore(ownACTInput,1,36));
    if(category){
      item.classList.add("cs-has-badge");
      var badge=document.createElement("a");
      badge.className="cs-admission-badge cs-admission-"+category.toLowerCase();
      badge.href="#cs-admissions-note";
      badge.textContent=category+"*";
      var historicMatch=(Number.isFinite(ownScore(ownSATInput,400,1600))&&Number.isFinite(record.sat_p50)&&record.sat_source?.is_historical)||
        (Number.isFinite(ownScore(ownACTInput,1,36))&&Number.isFinite(record.act_p50)&&record.act_source?.is_historical);
      badge.setAttribute("aria-label",category+(historicMatch?" based partly or wholly on historical admissions data":"")+" — see approximate test score categorization note");
      if(historicMatch)badge.setAttribute("title","Historical test-score comparison; see reported cohort on the card");
      item.appendChild(badge);
    }
    var heading = document.createElement("h3");
    heading.textContent = record.name;
    var locality = document.createElement("p");
    locality.textContent = record.city + ", " + record.state;
    var unitid = document.createElement("p");
    unitid.className = "cs-visually-hidden";
    unitid.textContent = "Institution identifier " + record.unitid;
    item.append(heading, locality, unitid);
    var costs=document.createElement("div");
    costs.className="cs-costs";
    function addCost(label,value) {
      if(value === null)return;
      var p=document.createElement("p");
      var title=document.createElement("strong");title.textContent=label+": ";
      p.append(title,document.createTextNode(money(value)));costs.appendChild(p);
    }
    addCost("Annual cost (estimated)",record.annual_cost);
    addCost("Average net price after grant aid",record.average_net_price);
    addCost("Tuition and fees — in-state",record.tuition_in_state);
    if(record.tuition_out_state!==null && record.tuition_out_state!==record.tuition_in_state)
      addCost("Tuition and fees — out-of-state",record.tuition_out_state);
    if(costs.childElementCount)item.appendChild(costs);
    if(window.CollegeProgramSearch){var evidence=window.CollegeProgramSearch.cardFor(record.unitid);if(evidence)item.appendChild(evidence);}
    if(record.sat_source||record.act_source){
      var testing=document.createElement("div");
      testing.className="cs-card-scores";
      function addScore(label,average,p25,p50,p75,source){
        if(!source)return;
        var entry=document.createElement("p");
        var header=document.createElement("strong");header.textContent=(source.is_historical?"Historical ":"")+label+" ("+source.cohort+"): ";
        entry.appendChild(header);
        var middle=(Number.isFinite(p25)&&Number.isFinite(p50)&&Number.isFinite(p75)) ?
          "25th / 50th / 75th: "+p25+" / "+p50+" / "+p75 : "25th–75th percentile unavailable";
        var measure=label.startsWith("ACT") ? (source.act_reference_field==="ACTCM50"?"reported median":"reported midpoint") : "reported average";
        entry.appendChild(document.createTextNode((Number.isFinite(average)?(measure+" "+average+" · "):"")+middle));
        testing.appendChild(entry);
      }
      addScore("SAT (estimated total percentiles)",record.sat_avg,record.sat_p25,record.sat_p50,record.sat_p75,record.sat_source);
      addScore("ACT composite",record.act_mid,record.act_p25,record.act_p50,record.act_p75,record.act_source);
      var uniqueSources=[];
      [record.sat_source,record.act_source].forEach(function(source){
        if(source&&!uniqueSources.some(function(prev){return prev.url===source.url&&prev.cohort===source.cohort;}))uniqueSources.push(source);
      });
      uniqueSources.forEach(function(source){
        var cite=document.createElement("p");cite.className="cs-score-source";
        cite.appendChild(document.createTextNode((source.is_historical?"Historical ":"")+"Test-score source: "+source.provider+" · "+source.dataset+" · "+source.cohort+" · "));
        var link=document.createElement("a");link.textContent="Source data";link.href=source.url;
        link.target="_blank";link.rel="noopener noreferrer";cite.appendChild(link);
        testing.appendChild(cite);
      });
      item.appendChild(testing);
    }
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
    if (selectedCities.size) selections.push("Cities: " + Array.from(selectedCities).map(function(k){var p=k.split("|");return p[1]+", "+p[0];}).join("; "));
    if (activeMax(netSlider)!==null) selections.push("Max average net price: " + money(activeMax(netSlider)));
    if (activeMax(costSlider)!==null) selections.push("Max annual cost: " + money(activeMax(costSlider)));
    var satRange=currentSATRange(),actRange=currentACTRange();
    if(satRange)selections.push("SAT institution average: "+satRange.min+"–"+satRange.max);
    if(actRange)selections.push("ACT institution midpoint: "+actRange.min+"–"+actRange.max);
    if(ownScore(ownSATInput,400,1600)!==null)selections.push("My SAT comparison: "+ownSATInput.value);
    if(ownScore(ownACTInput,1,36)!==null)selections.push("My ACT comparison: "+ownACTInput.value);

    // The collapsed testing panel always discloses active controls and preserves
    // their values; closing the panel never resets or disables a filter.
    var activeTestingCount = (satRange ? 1 : 0) + (actRange ? 1 : 0)
      + (ownScore(ownSATInput,400,1600)!==null ? 1 : 0)
      + (ownScore(ownACTInput,1,36)!==null ? 1 : 0);
    var testingStatus = root.querySelector("#cs-testing-active");
    if (testingStatus) testingStatus.textContent = activeTestingCount
      ? activeTestingCount + " active testing " + (activeTestingCount===1 ? "setting" : "settings")
      : "No testing settings applied";
    if(window.CollegeProgramSearch)selections.push.apply(selections,window.CollegeProgramSearch.labels());
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
      control:controlSelect.value, locale:localeSelect.value, size:sizeSelect.value,
      cities:Array.from(selectedCities), netMax:activeMax(netSlider), costMax:activeMax(costSlider),
      satRange:currentSATRange(),actRange:currentACTRange()
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
    selectedCities.clear();citySearch.value="";
    netSlider.value=netSlider.max;costSlider.value=costSlider.max;
    satLow.value=400;satHigh.value=1600;actLow.value=1;actHigh.value=36;
    ownSATInput.value="";ownACTInput.value="";drawScoreLabels();
    if(window.CollegeProgramSearch)window.CollegeProgramSearch.clear();
    drawMoneyLabels();redrawSelectedCities();renderCityOptions();
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
      await loadScores(controller.signal);
      if(window.CollegeProgramSearch)window.CollegeProgramSearch.configure(records,applyFilters);
      stateOptions();
      populateCities();
      populateCostSliders();
      drawScoreLabels();
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
  citySearch.addEventListener("input", renderCityOptions);
  netSlider.addEventListener("input", function () {drawMoneyLabels();applyFilters();});
  costSlider.addEventListener("input", function () {drawMoneyLabels();applyFilters();});
  satLow.addEventListener("input",function(){changeScoreRange(satLow,satHigh,"low");});
  satHigh.addEventListener("input",function(){changeScoreRange(satLow,satHigh,"high");});
  actLow.addEventListener("input",function(){changeScoreRange(actLow,actHigh,"low");});
  actHigh.addEventListener("input",function(){changeScoreRange(actLow,actHigh,"high");});
  ownSATInput.addEventListener("input",applyFilters);
  ownACTInput.addEventListener("input",applyFilters);
  clearButton.addEventListener("click", clear);
  moreButton.addEventListener("click", function () { render(true); });
  retryButton.addEventListener("click", loadData);
  loadData();
}());
