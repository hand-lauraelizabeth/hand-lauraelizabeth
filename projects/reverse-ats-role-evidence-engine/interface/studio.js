(() => {
  'use strict';
  const byId=id=>document.getElementById(id);
  const candidate=byId('candidate'),job=byId('job');
  const tabs=['review','roles','resume','evidence'];
  const displayType={hard:'Required',preferred:'Preferred',scope:'Scope / authority',tool:'Tool or method',responsibility:'Responsibility',context:'Context'};
  const statusName={strong:'Textual evidence visible',visible:'Textual evidence visible',partial:'Partial textual evidence','not visible':'Evidence not surfaced'};
  let active='review',reviewRows=[],reviewKey='',shown=8,planText='';
  const key=()=>JSON.stringify([candidate.value,job.value,GRAPH.map(node=>[node.evidence_id,node.verification_status,node.reviewed])]);
  const make=(tag,value,className)=>{const e=document.createElement(tag);if(value!==undefined)e.textContent=value;if(className)e.className=className;return e;};
  function choose(name,focus=false){
    active=name;
    tabs.forEach(id=>{
      const selected=id===name,tab=byId('tab-'+id);
      tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;
      byId('pane-'+id).hidden=!selected;
    });
    if(focus)byId('tab-'+name).focus();
    if(typeof atsReportHeight==='function')atsReportHeight();
  }
  tabs.forEach((name,index)=>{
    const tab=byId('tab-'+name);
    tab.addEventListener('click',()=>choose(name));
    tab.addEventListener('keydown',event=>{
      const next=event.key==='ArrowRight'?(index+1)%tabs.length:event.key==='ArrowLeft'?(index+tabs.length-1)%tabs.length:event.key==='Home'?0:event.key==='End'?tabs.length-1:null;
      if(next!==null){event.preventDefault();choose(tabs[next],true);}
    });
  });
  byId('studio-start').addEventListener('click',()=>{candidate.focus();candidate.scrollIntoView({block:'center',behavior:'smooth'});});
  const upload=byId('leh-upload');
  if(!upload||!byId('leh-doc-editor')||!byId('leh-readiness'))throw Error('A required document or readiness feature did not initialize.');
  candidate.parentNode.insertBefore(upload,byId('candidate-input-heading'));
  const readiness=byId('leh-readiness');
  const documentEditor=byId('leh-doc-editor');
  byId('pane-resume').insertBefore(documentEditor,byId('studio-quick-draft'));
  byId('pane-resume').append(readiness);
  const buildRevision=documentEditor.querySelector('button');buildRevision.id='studio-revision-build';
  buildRevision.textContent='Build and edit my résumé';
  documentEditor.querySelector('h2').textContent='Build a résumé you can trace to its source.';
  readiness.querySelector('h2').textContent='Check your résumé’s structure and clarity';
  const readinessButtons=readiness.querySelectorAll('button');
  readinessButtons[0].id='studio-readiness-run';readinessButtons[1].textContent='Build quick text draft';
  byId('resume-heading').textContent='Quick text draft';
  const moreTools=byId('career-evidence-tools');moreTools.querySelector('summary').textContent='Source evidence, saved profiles, and claim review';
  byId('analyze').addEventListener('click',()=>choose('evidence'));
  byId('resume-build').addEventListener('click',()=>{choose('resume');byId('studio-quick-draft').open=true;});
  byId('studio-open-editor').addEventListener('click',()=>{
    choose('resume');buildRevision.click();documentEditor.scrollIntoView({block:'start',behavior:'smooth'});buildRevision.focus();
  });
  // Show area selection only after a ZIP resolves to more than one labor market.
  const area=byId('career-area'),areaLabel=document.querySelector('label[for="career-area"]');
  const updateArea=()=>{const show=!area.disabled&&area.options.length>2;area.hidden=!show;areaLabel.hidden=!show;};
  new MutationObserver(updateArea).observe(area,{childList:true,attributes:true,attributeFilter:['disabled']});updateArea();
  function inputState(){
    const words=candidate.value.trim().split(/\s+/).filter(Boolean).length;
    byId('studio-input-status').textContent=words?words.toLocaleString()+' résumé words · '+(job.value.trim()?'Posting added':'Add a posting for an application review'):'Import a résumé or paste your text to begin.';
    const stale=Boolean(reviewKey)&&reviewKey!==key();
    byId('studio-stale').hidden=!stale;
    byId('studio-plan-download').disabled=byId('studio-plan-copy').disabled=stale||!planText;
    if(stale)byId('studio-review-message').textContent='Your inputs changed. Review again to refresh the results.';
  }
  [candidate,job].forEach(input=>input.addEventListener('input',inputState));
  for(const id of ['sampleCandidate','sampleJob','profileLoad'])byId(id).addEventListener('click',inputState);
  for(const id of ['saveNode','clearNodeReview'])byId(id).addEventListener('click',inputState);
  new MutationObserver(inputState).observe(byId('profileMsg'),{childList:true});
  // Profile imports and document imports also update the shared text asynchronously.
  byId('profileImport').addEventListener('change',()=>setTimeout(inputState,0));
  function needsAttention(row){return !['strong','visible'].includes(row.ev.status)||Boolean(row.hard_check&&/unresolved|not visible|does not yet support|not clearly supported/i.test(row.hard_check))||/not usable externally|blocked/i.test(row.g);}
  function prioritized(rows){
    return [...rows].sort((a,b)=>(a.type==='hard'&&needsAttention(a)?0:needsAttention(a)?1:a.type==='preferred'?3:2)-(b.type==='hard'&&needsAttention(b)?0:needsAttention(b)?1:b.type==='preferred'?3:2)||a.id-b.id);
  }
  function sourceExcerpt(row){return row.ev.found||'No source excerpt surfaced in the supplied material.';}
  function renderCriteria(){
    const query=byId('studio-criteria-search').value.toLocaleLowerCase(),filter=byId('studio-criteria-filter').value;
    const selected=prioritized(reviewRows).filter(row=>(filter==='all'||filter==='attention'&&needsAttention(row)||row.type===filter)&&
      [row.text,row.ev.found,row.ev.source,atsAction(row)].join(' ').toLocaleLowerCase().includes(query));
    const host=byId('studio-criteria');host.replaceChildren();
    for(const row of selected.slice(0,shown)){
      const card=make('article',undefined,'criterion-card');
      const labels=make('div',undefined,'criterion-labels');
      labels.append(make('span',displayType[row.type]||row.type,'criterion-type'),make('span',statusName[row.ev.status]||row.ev.status,'criterion-status '+(needsAttention(row)?'attention':'visible')));
      card.append(labels,make('h4',row.text));
      if(row.hard_check)card.append(make('p',row.hard_check,'criterion-condition'));
      card.append(make('p','Source connection','criterion-caption'),make('p',sourceExcerpt(row),'criterion-excerpt'),make('p',atsAction(row),'criterion-action'));
      if(row.ev.source)card.append(make('p','Source: '+row.ev.source+' · Review: '+reviewedSupport(row.ev),'studio-muted'));
      host.append(card);
    }
    if(!selected.length)host.append(make('p','No criteria match this view. Try another search or choose All criteria.','studio-empty'));
    byId('studio-criteria-count').textContent='Showing '+Math.min(shown,selected.length)+' of '+selected.length+' matching criteria · '+reviewRows.length+' total';
    byId('studio-criteria-more').hidden=shown>=selected.length;
  }
  byId('studio-criteria-search').addEventListener('input',()=>{shown=8;renderCriteria();});
  byId('studio-criteria-filter').addEventListener('change',()=>{shown=8;renderCriteria();});
  byId('studio-criteria-more').addEventListener('click',()=>{shown+=8;renderCriteria();});
  function buildPlan(){
    reviewRows=DATA.filter(row=>row.type!=='context');reviewKey=key();shown=8;
    byId('studio-plan').hidden=false;byId('studio-stale').hidden=true;
    const required=reviewRows.filter(row=>row.type==='hard');
    const visible=reviewRows.filter(row=>['strong','visible'].includes(row.ev.status));
    const attention=reviewRows.filter(needsAttention);
    const counts=byId('studio-counts');counts.replaceChildren();
    for(const [count,label] of [[required.length,'Stated required criteria'],[visible.length,'Text connections surfaced'],[attention.length,'Criteria needing attention']]){
      const card=make('div',undefined,'plan-count');card.append(make('strong',count),make('span',label));counts.append(card);
    }
    const actions=byId('studio-actions');actions.replaceChildren();
    const top=prioritized(attention.length?attention:reviewRows).slice(0,3);
    if(!top.length)actions.append(make('li','No reviewable criteria were identified. Add the full qualifications and responsibilities, then run the review again.'));
    top.forEach(row=>{
      const item=make('li');item.append(make('strong',row.type==='hard'?'Clarify a required criterion':needsAttention(row)?'Strengthen the evidence connection':'Verify the visible connection'),make('p',row.text),make('p',atsAction(row),'studio-muted'));actions.append(item);
    });
    const heading=job.value.trim().split(/\n/).find(Boolean)||'Application review';
    planText=['REVERSE ATS · APPLICATION NEXT-STEP PLAN',heading,'',reviewRows.length+' criteria reviewed; '+required.length+' stated required; '+visible.length+' textual connections; '+attention.length+' need attention.',
      'Textual visibility is not proof that a requirement is met. This is a review aid, not an employer ATS score.','',
      'PRIORITY ACTIONS',...top.flatMap((row,i)=>[(i+1)+'. '+row.text,atsAction(row),'']),
      'COMPLETE CRITERIA REVIEW',...prioritized(reviewRows).flatMap(row=>[displayType[row.type]+': '+row.text,'Visibility: '+row.ev.status,'Evidence: '+sourceExcerpt(row),row.hard_check?'Condition: '+row.hard_check:'','Next action: '+atsAction(row),'']),
      'Prepared from the résumé and posting supplied in this browser. Keep source details private. Review exact dates, authority, credentials and employer application questions before sharing claims.'].join('\n');
    byId('studio-plan-copy').disabled=byId('studio-plan-download').disabled=false;
    byId('studio-plan-message').textContent='';
    byId('studio-review-message').textContent='Review ready. Start with the next steps, then check the source connection for each criterion.';
    renderCriteria();
  }
  byId('ats-run').addEventListener('click',()=>{if(job.value.trim()&&jobClauses(job.value).length){buildPlan();inputState();}});
  function review(){
    choose('review');
    if(candidate.value.trim().length<80){byId('studio-review-message').textContent='Add a résumé or evidence summary of at least 80 characters first.';candidate.focus();return;}
    if(!job.value.trim()||!jobClauses(job.value).length){byId('studio-review-message').textContent='Add the job posting, including qualifications and responsibilities, then review your application.';job.focus();return;}
    byId('ats-run').click();
    byId('studio-readiness-run').click();
    byId('studio-plan-title').focus();
  }
  byId('studio-review').addEventListener('click',review);
  document.addEventListener('studio-example-loaded',()=>{byId('studio-demo-note').hidden=false;inputState();review();});
  function currentPlan(){
    if(reviewKey!==key()){inputState();byId('studio-plan-message').textContent='Run the review again before exporting a plan for changed inputs.';return null;}
    return planText||null;
  }
  byId('studio-plan-download').addEventListener('click',()=>{
    const content=currentPlan();if(!content)return;
    let href,link;
    try{
      href=URL.createObjectURL(new Blob([content+'\n'],{type:'text/plain;charset=utf-8'}));link=make('a');link.href=href;link.download='application-next-step-plan.txt';document.body.append(link);link.click();
      byId('studio-plan-message').textContent='Plan download started. Check your browser’s downloads.';
    }catch{byId('studio-plan-message').textContent='The download could not start. Copy the plan or try again.';}
    finally{link?.remove();if(href)setTimeout(()=>URL.revokeObjectURL(href),1500);}
  });
  byId('studio-plan-copy').addEventListener('click',async()=>{
    const content=currentPlan();if(!content)return;
    try{await navigator.clipboard.writeText(content);byId('studio-plan-message').textContent='Next-step plan copied.';}
    catch{byId('studio-plan-message').textContent='Clipboard access is unavailable. Use Download plan instead.';}
  });
  // Retain existing in-page links while revealing the task that contains the target.
  document.addEventListener('click',event=>{
    const link=event.target.closest('a[href^="#"]');if(!link)return;
    const target=byId(link.getAttribute('href').slice(1));if(!target)return;
    event.preventDefault();
    const pane=target.closest('.studio-pane');if(pane)choose(pane.id.slice(5));
    for(let ancestor=target.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;
    target.scrollIntoView({block:'start',behavior:'smooth'});target.setAttribute('tabindex','-1');target.focus();
  });
  inputState();choose(active);
})();
