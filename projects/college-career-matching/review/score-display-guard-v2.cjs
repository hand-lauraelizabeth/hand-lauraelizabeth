'use strict';
function describeScoreRecord(unitid, view) {
 const id=String(unitid);
 if(!/^\d{6}$/.test(id)) return null;
 const fmt=n=>Number.isFinite(n)?String(n):'Not reported';
 const c=view.describe(id);
 if(c) return {
  unitid:id, source:c.source, heading:'Scores among submitting students',
  sat:'SAT 25th–75th: '+fmt(c.sat.p25)+'–'+fmt(c.sat.p75),
  act:'ACT 25th–75th: '+fmt(c.act.p25)+'–'+fmt(c.act.p75),
  note:'Only students submitting scores are represented. SAT submitters: '+fmt(c.sat.percent)+'%; ACT submitters: '+fmt(c.act.percent)+'%.',
  admissionCategoryAllowed:false, admissionCategory:null,
  categoryExplanation:'No safety/target/reach label: reported scores do not establish admission probability.'
 };
 const b=view.baselineEntry(id);
 if(!b) return null;
 return {
  unitid:id, source:'Pinned College Scorecard overlay', heading:'Reported test-score evidence',
  sat:'SAT section-derived 25th–75th: '+fmt(b[2])+'–'+fmt(b[4]),
  act:'ACT composite 25th–75th: '+fmt(b[5])+'–'+fmt(b[7]),
  note:'SAT bands are section-derived, not directly reported composite percentiles.',
  admissionCategoryAllowed:false, admissionCategory:null,
  categoryExplanation:id==='208822'?'Scores not considered for admission.':'Admissions testing policy not independently verified here.'
 };
}
module.exports={describeScoreRecord};
