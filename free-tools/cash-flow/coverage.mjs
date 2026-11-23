// Browser-local projection coverage: warn when entered events never affect a modeled day.
// Exact source IDs are retained for comparisons; display-only escaping avoids invisible controls.
export function summarizeEventCoverage(events,baseline,scenario){
  if(!Array.isArray(events)||!Array.isArray(baseline?.days)||!Array.isArray(scenario?.days))throw Error('Invalid event coverage inputs.');
  const sourceIds=events.map(event=>{
    if(typeof event?.id!=='string')throw Error('Invalid source event ID.');
    return event.id;
  });
  const sourceIdSet=new Set(sourceIds);
  if(sourceIdSet.size!==sourceIds.length)throw Error('Duplicate source event ID.');
  const seen=projection=>{
    const ids=new Set();
    for(const day of projection.days){
      if(!Array.isArray(day.events))throw Error('Invalid projection event list.');
      for(const event of day.events){
        if(typeof event?.id!=='string'||!sourceIdSet.has(event.id))
          throw Error('Projection event ID does not match an entered event.');
        ids.add(event.id);
      }
    }
    return ids;
  };
  const baselineIds=seen(baseline),scenarioIds=seen(scenario);
  return {
    baselineMissing:sourceIds.filter(id=>!baselineIds.has(id)),
    scenarioMissing:sourceIds.filter(id=>!scenarioIds.has(id))
  };
}
// Bound each displayed ID independently of the four-ID list limit. Preserve exact IDs in
// coverage comparisons; shorten only the spoken/visible status preview, by Unicode code point.
export function displaySafeText(id,kind='ID'){
  let count=0;
  const first=[],last=[];
  for(const point of id){
    count++;
    if(count<=60)first.push(point);
    last.push(point);
    if(last.length>12)last.shift();
  }
  const shortened=count>80;
  const shown=shortened?first.join('')+'…'+last.join(''):id;
  const escaped=JSON.stringify(shown).replace(/[\p{Default_Ignorable_Code_Point}\p{Cc}\p{Cf}\u2028\u2029\u115f-\u1160\u17b4-\u17b5\ufff9-\ufffb]/gu,
    character=>'\\u'+character.codePointAt(0).toString(16).toUpperCase().padStart(4,'0'));
  return shortened?escaped+' ('+(count-72)+' code points omitted from displayed '+kind+')':escaped;
}
export function coverageText(events,baseline,scenario){
  const {baselineMissing,scenarioMissing}=summarizeEventCoverage(events,baseline,scenario);
  if(events.length===0)return 'No income or bill events were added; only the opening balance is modeled.';
  if(!baselineMissing.length&&!scenarioMissing.length)return 'All '+events.length+' '+(events.length===1?'event has':'events have')+' at least one occurrence within the selected dates in both projections.';
  const preview=ids=>ids.length?' ['+ids.slice(0,4).map(id=>displaySafeText(id)).join(', ')+(ids.length>4?'; '+(ids.length-4)+' more':'')+']':'';
  return 'Events with no occurrence within the selected dates: baseline '+baselineMissing.length+' of '+events.length+preview(baselineMissing)+
    '; shifted scenario '+scenarioMissing.length+' of '+events.length+preview(scenarioMissing)+
    '. These events remain in your editable plan but do not affect the corresponding projected balances. Review dates, recurrence, and any shift.';
}

/**
 * Evidence attached to the downloaded scenario JSON. Source IDs are exact,
 * including whitespace and Unicode; only events without occurrences are listed.
 * Baseline coverage is included for interpretation, not baseline daily balances.
 */
export function coverageEvidence(events,baseline,scenario){
  const {baselineMissing,scenarioMissing}=summarizeEventCoverage(events,baseline,scenario);
  return {
    enteredEventCount:events.length,
    baseline:{modeledEventCount:events.length-baselineMissing.length,withoutOccurrencesIds:baselineMissing},
    shiftedScenario:{modeledEventCount:events.length-scenarioMissing.length,withoutOccurrencesIds:scenarioMissing},
    note:'Counts distinct entered event IDs with at least one occurrence within the selected dates. Events without occurrences do not affect the corresponding projection. This export contains shifted-scenario daily balances only; it does not contain baseline daily balances.'
  };
}
