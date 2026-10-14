export function renderFindings(report, list, summary) {
 list.replaceChildren();
 summary.textContent=report.findings.length+' findings. These are preliminary checks, not an accessibility certification.';
 for(const f of report.findings){
  const li=document.createElement('li');
  const heading=document.createElement('strong');heading.textContent=f.id+': '+f.rule+' ('+f.severity+')';
  const description=document.createElement('p');description.textContent=f.message+' Location: '+f.location+'. Reference: '+f.reference+'.';
  li.append(heading,description);list.append(li);
 }
 if(!report.findings.length){const li=document.createElement('li');li.textContent='No selected findings. Manual checks remain necessary.';list.append(li);}
}
