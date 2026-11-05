"""Preserve the application engines; build one guided, self-contained workspace."""
from pathlib import Path
from lxml import html, etree
import re
ROOT=Path(__file__).resolve().parent.parent
UI=ROOT/'interface'
page=html.document_fromstring((UI/'base.html').read_text())
body=page.find('body')
header=body.find('header')
main=body.find('main')
existing={n.get('id'):n for n in page.xpath('//*[@id]')}
def get(id):return existing[id] if id in existing else page.get_element_by_id(id)
def fragment(markup):return html.fragment_fromstring(markup)
def append(parent,node):
    if node.getparent() is not None:node.getparent().remove(node)
    parent.append(node)
old_ids={n.get('id') for n in page.xpath('//*[@id]')}
example=get('career-example');example.getparent().remove(example)
header.clear()
header.set('class','studio-hero')
header.append(fragment('''<div class="hero-copy"><p class="studio-eyebrow"><span class="studio-mark" aria-hidden="true">R</span> Reverse ATS · Role Evidence Studio</p><h1>Find the evidence.<br>Make your next move.</h1><p class="hero-lead">See how your résumé supports a job posting, explore roles and local pay, and build a clearer résumé you can edit and download.</p><div class="hero-actions" id="hero-actions"></div><p class="hero-trust">Free to use · No account · Your documents are processed in your browser</p><p class="hero-note">A practical evidence review. Results reflect the text you supply; they do not predict an employer’s ATS score.</p></div>'''))
header.append(fragment('''<aside class="hero-sample" aria-label="Fictional example of a job review"><div class="sample-header"><span>YOUR APPLICATION, AT A GLANCE</span><span class="sample-badge">Example</span></div><h2>Training and development specialist</h2><div class="sample-match"><span class="sample-symbol">✓</span><div><strong>Training delivery</strong><span>Visible in the résumé</span></div></div><div class="sample-match"><span class="sample-symbol amber">?</span><div><strong>Program coordination</strong><span>Clarify the scope of your contribution</span></div></div><div class="sample-next"><strong>A useful next step</strong><p>Find a specific, supportable example before strengthening the claim.</p></div><p>Requirements → evidence → next action</p></aside>'''))
actions=page.get_element_by_id('hero-actions');example.text='Try the example';example.set('class','btn');actions.append(example)
actions.append(fragment('<button type="button" id="studio-start" class="btn ghost">Use my résumé <span aria-hidden="true">→</span></button>'))
steps=fragment('''<nav class="studio-steps" aria-label="How it works"><div><span>1</span><p><strong>Add your résumé</strong>Import PDF/DOCX or paste text.</p></div><div><span>2</span><p><strong>Choose your task</strong>Review a job, explore roles, or revise.</p></div><div><span>3</span><p><strong>Leave with something useful</strong>A clear plan, role leads, or an editable résumé.</p></div></nav>''')
body.insert(body.index(main),steps)
original_grid=main.find('div');job_panel=get('job').getparent();candidate_panel=get('candidate').getparent()
original_grid.remove(job_panel);original_grid.remove(candidate_panel);main.remove(original_grid)
main.set('class','studio-main');main.set('tabindex','-1')
workspace=fragment('''<div class="studio-workspace"><aside id="studio-inputs" class="studio-inputs" aria-labelledby="studio-input-heading"><div class="input-heading"><p class="studio-eyebrow">YOUR STARTING POINT</p><h2 id="studio-input-heading">Your résumé &amp; target</h2><p>Add your résumé once. Every task uses the same text.</p></div><div id="studio-source-mount"></div><div id="studio-job-mount"></div><p id="studio-input-status" class="studio-muted" role="status" aria-live="polite">Ready when you are.</p></aside><section class="studio-work" aria-labelledby="studio-task-heading"><div class="work-heading"><div><p class="studio-eyebrow">YOUR WORKSPACE</p><h2 id="studio-task-heading">What would you like to do?</h2></div><span class="workspace-tag">Private workspace</span></div><div class="studio-tabs" role="tablist" aria-label="Choose a task"><button id="tab-review" type="button" role="tab" aria-selected="true" aria-controls="pane-review" tabindex="0">Review a job</button><button id="tab-roles" type="button" role="tab" aria-selected="false" aria-controls="pane-roles" tabindex="-1">Find roles &amp; pay</button><button id="tab-resume" type="button" role="tab" aria-selected="false" aria-controls="pane-resume" tabindex="-1">Improve résumé</button><button id="tab-evidence" type="button" role="tab" aria-selected="false" aria-controls="pane-evidence" tabindex="-1">Evidence &amp; profile</button></div><p id="studio-demo-note" class="studio-demo" hidden>Fictional example loaded. Explore the review, edit the inputs, or try another task.</p><div id="pane-review" class="studio-pane" role="tabpanel" aria-labelledby="tab-review"><div class="task-intro"><h3>Turn the posting into a practical review.</h3><p>See the stated requirements, what your résumé makes visible, and what to clarify before you apply.</p><button id="studio-review" class="btn" type="button">Review my application <span aria-hidden="true">→</span></button><p id="studio-review-message" class="studio-muted" role="status" aria-live="polite">Add your résumé and a job posting to get started.</p></div><div id="studio-plan" hidden><div class="plan-heading"><div><p class="studio-eyebrow">YOUR NEXT STEPS</p><h3 id="studio-plan-title" tabindex="-1">A clearer plan for this application</h3></div><span class="sample-badge">Text review</span></div><p id="studio-stale" class="studio-warning" role="status" hidden>Your inputs changed. Run the review again to update this plan.</p><div id="studio-counts" class="studio-counts"></div><p class="studio-muted">“Visible” means the text suggests a connection. It does not establish that a requirement is met.</p><ol id="studio-actions" class="studio-actions"></ol><div class="row"><button id="studio-plan-copy" class="btn ghost" type="button">Copy next-step plan</button><button id="studio-plan-download" class="btn ghost" type="button">Download plan (.txt)</button><button id="studio-open-editor" class="btn" type="button">Build my résumé revision →</button></div><p id="studio-plan-message" class="studio-muted" role="status" aria-live="polite"></p><div class="criteria-heading"><h3>Follow each requirement to its evidence.</h3><p>Use these cards to review the connection and keep claims within the support you have.</p></div><div class="criteria-controls"><label>Search requirements or evidence<input id="studio-criteria-search" type="search" placeholder="e.g. leadership, Excel, degree"></label><label>Show<select id="studio-criteria-filter"><option value="all">All criteria</option><option value="attention">Needs attention</option><option value="hard">Required</option><option value="preferred">Preferred</option></select></label></div><p id="studio-criteria-count" class="studio-muted" role="status" aria-live="polite"></p><div id="studio-criteria"></div><button id="studio-criteria-more" class="btn ghost" type="button" hidden>Show 8 more criteria</button></div></div><div id="pane-roles" class="studio-pane" role="tabpanel" aria-labelledby="tab-roles" hidden></div><div id="pane-resume" class="studio-pane" role="tabpanel" aria-labelledby="tab-resume" hidden></div><div id="pane-evidence" class="studio-pane" role="tabpanel" aria-labelledby="tab-evidence" hidden></div></section></div>''')
main.insert(0,workspace)
candidate_panel.set('class','studio-source');get('studio-source-mount').append(candidate_panel)
get('candidate-input-heading').text='Résumé text';get('candidate').set('placeholder','Paste your résumé here, or import a PDF/DOCX above. Add a job posting below when you want an application review.')
candidate_actions=candidate_panel.find('div');candidate_actions.getparent().remove(candidate_actions)
plain=fragment('<details class="studio-secondary"><summary>Plain-text import and sample evidence</summary></details>')
for node in [get('career-file').getprevious(),get('career-file'),get('career-input-status')]:append(plain,node)
sample=get('sampleCandidate');append(plain,sample);candidate_panel.append(plain)
get('sampleCandidate').text='Load sample evidence'
job_panel.set('class','studio-job');get('studio-job-mount').append(job_panel)
get('job-input-heading').clear();get('job-input-heading').set('id','job-input-heading');get('job-input-heading').text='Job posting';job_panel.insert(1,fragment('<p class="studio-muted">Required for a job review; optional for the other tasks.</p>'))
job_actions=job_panel.find('div');job_panel.remove(job_actions);append(get('pane-evidence'),job_actions)
get('analyze').text='Analyze posting structure';get('sampleJob').text='Load sample posting'
for id in ['exportEvidence','export']:append(job_actions,get(id))
append(get('pane-roles'),get('career-workbench'))
quick=fragment('<details id="studio-quick-draft" class="studio-secondary"><summary>Quick plain-text draft and text download</summary></details>');append(quick,get('resume-workbench'));get('pane-resume').append(quick)
advanced=get('career-evidence-tools');advanced.set('open','');append(get('pane-evidence'),advanced)
audit=fragment('<details id="studio-detailed-audit" class="studio-secondary"><summary>Detailed audit, screening questions, and CSV export</summary></details>');append(audit,get('reverse-ats-audit'));get('pane-review').append(audit)
for p in main.xpath('./p'):p.getparent().remove(p)
# Existing application engines run before the document enhancements and interface.
scripts=body.findall('script')
scripts[-1].text=scripts[-1].text.replace("byId('sampleJob').click();", "byId('sampleJob').click();\n    job.value = 'Training and Development Specialist\\nRequired qualifications:\\nExperience designing training materials and learning objectives.\\nExperience facilitating onboarding workshops for new employees.\\nExperience analyzing survey feedback and evaluating training effectiveness.\\nPreferred qualifications:\\nA master’s degree preferred.\\nExperience using Excel to report results.\\nResponsibilities:\\nCoordinate learning programs with stakeholders.\\nMaintain training schedules and learning records.';")
scripts[-1].text=scripts[-1].text.replace("status.textContent = 'Fictional résumé, job posting, and ZIP loaded.';","status.textContent = 'Fictional résumé, job posting, and ZIP loaded.';\n    document.dispatchEvent(new CustomEvent('studio-example-loaded'));")
for name in ['leh-readiness-enhancement.js','leh-document-enhancement.js','studio.js']:
    script=etree.Element('script');script.text=(UI/name).read_text();body.append(script)
style=etree.Element('style');style.text=(UI/'studio.css').read_text();body.append(style)
page.find('head/title').text='Reverse ATS · Role Evidence Studio'
get('studio-inputs').set('tabindex','-1')
skip=fragment('<a class="studio-skip" href="#career-inputs">Skip to workspace</a>');body.insert(0,skip)
new_ids={n.get('id') for n in page.xpath('//*[@id]')}
assert old_ids<=new_ids, old_ids-new_ids
compiled='<!doctype html>\n'+html.tostring(page,encoding='unicode',method='html')
assert compiled.count('id="candidate"')==1 and compiled.count('id="job"')==1
(ROOT/'index.html').write_text(compiled)
print('Preserved',len(old_ids),'existing element IDs; built',len(compiled.encode()),'bytes.')
