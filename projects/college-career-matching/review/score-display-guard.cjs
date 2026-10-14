'use strict';
// Review-only display guard. Preserve pinned numeric overlay unchanged.
function describeScoreRecord(unitid, view) {
  if (!/^\d{6}$/.test(String(unitid))) return null;
  const c=view.describe(String(unitid));
  if(c) {
    const fmt=n=>Number.isFinite(n)?String(n):'Not reported';
    return {unitid:String(unitid),source:c.source,cohort:c.cohort,heading:'Scores among submitting students',sat:'SAT 25th–75th: '+fmt(c.sat.p25)+'–'+fmt(c.sat.p75),act:'ACT 25th–75th: '+fmt(c.act.p25)+'–'+fmt(c.act.p75),satSubmitterPercent:c.sat.percent,actSubmitterPercent:c.act.percent,admissionCategory:null,allowScoreBasedCategory:false,note:'Reported percentiles are not all-student averages.'};
  }
  const b=view.baselineEntry(String(unitid));
  if(!b) return null;
  return {unitid:String(unitid),source:'Pinned Scorecard overlay',admissionCategory:null,allowScoreBasedCategory:view.canClassify(String(unitid)),note:view.canClassify(String(unitid))?null:'Scores not considered for admission; do not classify.'};
}
module.exports={describeScoreRecord};
