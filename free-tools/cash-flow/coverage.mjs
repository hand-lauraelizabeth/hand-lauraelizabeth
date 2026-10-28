// Browser-local projection coverage: warn when entered events never affect a modeled day.
// Exact source IDs are retained for comparisons; display-only escaping avoids invisible controls.
export function summarizeEventCoverage(events,baseline,scenario){
  if(!Array.isArray(events)||!Array.isArray(baseline?.days)||!Array.isArray(scenario?.days))throw Error('Invalid event coverage inputs.');
  const seen=projection=>{
    const ids=new Set();
    for(const day of projection.days){
      if(!Array.isArray(day.events))throw Error('Invalid projection event list.');
      for(const event of day.events)ids.add(event.id);
    }
    return ids;
  };
  const baselineIds=seen(baseline),scenarioIds=seen(scenario);
  const sourceIds=events.map(event=>{
    if(typeof event?.id!=='string')throw Error('Invalid source event ID.');
    return event.id;
  });
  return {
    baselineMissing:sourceIds.filter(id=>!baselineIds.has(id)),
    scenarioMissing:sourceIds.filter(id=>!scenarioIds.has(id))
  };
}
function visibleId(id){
  return JSON.stringify(id).replace(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u061c\u202a-\u202e\u2066-\u2069]/gu,
    character=>'\\u'+character.codePointAt(0).toString(16).toUpperCase().padStart(4,'0'));
}
export function coverageText(events,baseline,scenario){
  const {baselineMissing,scenarioMissing}=summarizeEventCoverage(events,baseline,scenario);
  if(events.length===0)return 'No income or bill events were added; only the opening balance is modeled.';
  if(!baselineMissing.length&&!scenarioMissing.length)return 'All '+events.length+' '+(events.length===1?'event has':'events have')+' at least one occurrence within the selected dates in both projections.';
  const preview=ids=>ids.length?' ['+ids.slice(0,4).map(visibleId).join(', ')+(ids.length>4?'; '+(ids.length-4)+' more':'')+']':'';
  return 'Events with no occurrence within the selected dates: baseline '+baselineMissing.length+' of '+events.length+preview(baselineMissing)+
    '; shifted scenario '+scenarioMissing.length+' of '+events.length+preview(scenarioMissing)+
    '. These events remain in your editable plan but do not affect the corresponding projected balances. Review dates, recurrence, and any shift.';
}
