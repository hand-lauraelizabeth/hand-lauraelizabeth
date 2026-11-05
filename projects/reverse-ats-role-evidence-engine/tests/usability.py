"""User journeys against the production workspace, including real document bytes."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from zipfile import ZipFile
import json
import re
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright,expect
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
RESUME='''Jordan Example
jordan@example.test

EXPERIENCE
Learning and Development Specialist | Example Organization | 2021–2026
- Facilitated onboarding workshops for 120 employees.
- Designed training materials and learning objectives for instructor-led courses.
- Analyzed survey feedback and evaluated training effectiveness.

EDUCATION
Bachelor of Arts, Example University, 2021

SKILLS
Instructional design, training needs assessment, facilitation, evaluation, Excel, project management, data analysis, stakeholder communication, operations.
'''
JOB='''Learning Programs Manager
Required qualifications:
5+ years of experience in learning programs.
Bachelor's degree required; master's preferred.
Responsibilities:
Manage a team of learning facilitators and own the budget.
Design learning objectives and evaluate training effectiveness.
Preferred qualifications:
Experience using Excel dashboards.
'''

def main():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
    worker=Thread(target=server.serve_forever,daemon=True);worker.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
      with TemporaryDirectory() as folder,sync_playwright() as pw:
        for engine in ('chromium','firefox','webkit'):
          browser=getattr(pw,engine).launch()
          page=browser.new_page(viewport={'width':1360,'height':950},accept_downloads=True)
          errors=[];requests=[]
          page.on('pageerror',lambda error:errors.append(str(error)))
          page.on('request',lambda req:requests.append((req.url,req.method,req.post_data)))
          page.goto(base+'/index.html')
          expect(page.locator('#studio-inputs')).to_be_visible()
          assert page.locator('#leh-import-file').count()==1
          assert page.locator('#studio-revision-build').count()==1
          page.screenshot(path=str(ROOT/f'usability-{engine}-start.png'),full_page=True)
          page.locator('#studio-review').click()
          assert 'at least 80 characters' in page.locator('#studio-review-message').inner_text()
          assert page.locator('#candidate').evaluate('(e)=>e===document.activeElement')
          page.locator('#career-example').click()
          expect(page.locator('#studio-plan')).to_be_visible()
          assert page.locator('#studio-actions > li').count()>=1
          assert page.locator('#studio-criteria article').count()>=1
          page.screenshot(path=str(ROOT/f'usability-{engine}-review.png'),full_page=True)
          page.locator('#studio-criteria-filter').select_option('preferred')
          assert 'master' in page.locator('#studio-criteria').inner_text().lower()
          assert 'Required' not in page.locator('#studio-criteria').inner_text()
          page.locator('#studio-criteria-search').fill('impossible-criterion')
          assert 'No criteria match' in page.locator('#studio-criteria').inner_text()
          page.locator('#studio-criteria-search').fill('')
          page.locator('#studio-criteria-filter').select_option('all')
          with page.expect_download() as event:page.locator('#studio-plan-download').click()
          plan=Path(folder)/f'{engine}-plan.txt';event.value.save_as(plan)
          assert 'COMPLETE CRITERIA REVIEW' in plan.read_text()
          assert 'PRIORITY ACTIONS' in plan.read_text()
          assert 'master' in plan.read_text().lower()
          page.locator('#candidate').fill(RESUME)
          expect(page.locator('#studio-stale')).to_be_visible()
          assert page.locator('#studio-plan-download').is_disabled()
          page.locator('#job').fill(JOB)
          page.locator('#studio-review').click()
          assert page.locator('#studio-stale').is_hidden()
          assert 'Experience duration unresolved' in page.locator('#studio-criteria').inner_text()

          # Accessible task switching and the existing complete evidence review.
          page.locator('#tab-review').focus();page.locator('#tab-review').press('ArrowRight')
          assert page.locator('#tab-roles').get_attribute('aria-selected')=='true'
          page.locator('#tab-roles').press('End')
          assert page.locator('#tab-evidence').get_attribute('aria-selected')=='true'
          page.locator('#analyze').click()
          assert page.locator('#evidenceRows tr').count()>=3
          options=page.locator('#nodeSelect option').all()
          node_id=next(o.get_attribute('value') for o in options if o.get_attribute('value'))
          page.locator('#nodeSelect').select_option(node_id)
          page.locator('#nodeRole').fill('Reviewed synthetic role')
          page.locator('#nodeSource').fill('Synthetic source record')
          page.locator('#nodeDates').fill('2017–2026')
          page.locator('#nodeVerify').select_option('verified')
          page.locator('#nodeConf').select_option('public')
          page.locator('#nodeAuthority').fill('Confirmed scope for a synthetic browser test.')
          page.locator('#saveNode').click()
          assert 'verified' in page.locator('#evidenceRows').inner_text()
          assert 'calendar coverage, not elapsed experience' in page.locator('#interpret').inner_text()
          assert 'Experience duration unresolved' in page.locator('#rows').inner_text()
          page.locator('#profileSave').click()
          saved=page.evaluate("JSON.parse(localStorage.getItem('role-evidence.shared-profile.v1'))")
          assert any(n['verification_status']=='verified' for n in saved['evidence_nodes'])
          with page.expect_download() as event:page.locator('#profileDownload').click()
          profile=Path(folder)/f'{engine}-profile.json';event.value.save_as(profile)
          assert json.loads(profile.read_text())['format']=='role-evidence-candidate-profile'

          page.locator('#tab-roles').click()
          page.locator('#career-focus').fill('Training and development specialist')
          page.locator('#career-zip').fill('11432')
          page.locator('#career-run').click()
          expect(page.locator('#career-results .career-card').first).to_be_visible(timeout=90000)
          expect(page.locator('#career-results .career-pay').first).to_be_visible(timeout=90000)
          assert page.locator('#career-results a[href*="onetonline.org/link/summary/"]').count()>=1
          assert '25th–75th percentile' in page.locator('#career-results').inner_text()
          page.locator('#career-zip').fill('bad')
          page.locator('#career-run').click()
          expect(page.locator('#career-status')).to_contain_text('five-digit ZIP',timeout=30000)

          page.locator('#tab-review').click();page.locator('#studio-review').click()
          page.locator('#studio-open-editor').click()
          expect(page.locator('#leh-edits .leh-row').first).to_be_visible()
          assert page.locator('#tab-resume').get_attribute('aria-selected')=='true'
          page.locator('#leh-edits .leh-row details summary').first.click()
          assert 'Entered résumé' in page.locator('#leh-edits').inner_text()
          quantity=page.locator('#leh-edits textarea').all()
          quantity=next(e for e in quantity if '120 employees' in e.input_value())
          quantity.fill(quantity.input_value().replace('120','999'))
          assert 'Numbers changed' in page.locator('#leh-edits').inner_text()
          quantity.fill(quantity.input_value().replace('999','120'))
          page.locator('#leh-doc-editor > label input[type=checkbox]').uncheck()
          with page.expect_download(timeout=60000) as event:
            page.get_by_role('button',name='Download DOCX',exact=True).click()
          docx=Path(folder)/f'{engine}-resume.docx';event.value.save_as(docx)
          with ZipFile(docx) as archive:
            assert archive.testzip() is None
            xml=archive.read('word/document.xml')
            assert b'Jordan Example' in xml and b'120 employees' in xml
            assert b'999 employees' not in xml
            ET.fromstring(xml)
          with page.expect_download(timeout=60000) as event:
            page.get_by_role('button',name='Download PDF',exact=True).click()
          pdf=Path(folder)/f'{engine}-resume.pdf';event.value.save_as(pdf)
          text='\n'.join(p.extract_text() for p in PdfReader(pdf).pages)
          assert 'Jordan Example' in text and '120 employees' in text

          # The files actually generated above must reopen with real import libraries.
          page.once('dialog',lambda dialog:dialog.accept())
          page.locator('#leh-import-file').set_input_files(docx)
          expect(page.locator('#leh-upload [role=status]')).to_contain_text('Imported',timeout=60000)
          page.locator('#studio-revision-build').click()
          assert 'DOCX' in page.locator('#leh-edits').inner_text()
          page.once('dialog',lambda dialog:dialog.accept())
          page.locator('#leh-import-file').set_input_files(pdf)
          expect(page.locator('#leh-upload [role=status]')).to_contain_text('Imported',timeout=60000)
          page.locator('#studio-revision-build').click()
          assert 'PDF' in page.locator('#leh-edits').inner_text()
          assert 'page 1' in page.locator('#leh-edits').inner_text()
          assert page.locator('#studio-stale').is_visible() or page.locator('#studio-stale').text_content()
          page.screenshot(path=str(ROOT/f'usability-{engine}-desktop.png'),full_page=True)

          # Quick text draft, structure review and export remain available.
          page.locator('#studio-quick-draft > summary').click()
          page.locator('#resume-build').click()
          expect(page.locator('#resume-output')).to_be_visible()
          with page.expect_download() as event:page.locator('#resume-download').click()
          plain=Path(folder)/f'{engine}-draft.txt';event.value.save_as(plain)
          assert 'Jordan Example' in plain.read_text()
          page.locator('#studio-readiness-run').click()
          assert 'Next edits' in page.locator('#leh-readiness').inner_text()

          page.goto(base+'/career-discovery-tracker.html')
          page.locator('#profileLoad').click()
          expect(page.locator('article.card[data-id]').first).to_be_visible()
          card=page.locator('article.card[data-id]').first;card_id=card.get_attribute('data-id')
          card.locator('[data-k=s]').select_option(label='Applied')
          page.locator(f'article.card[data-id="{card_id}"] [data-k=n]').fill('Preserve this synthetic application note.')
          page.reload()
          assert page.locator(f'article.card[data-id="{card_id}"] [data-k=s]').input_value()=='Applied'
          page.locator('#profileLoad').click()
          assert page.locator(f'article.card[data-id="{card_id}"] [data-k=s]').input_value()=='Applied'
          assert 'synthetic application note' in page.locator(f'article.card[data-id="{card_id}"] [data-k=n]').input_value()
          for id,suffix in [('csv','csv'),('json','json')]:
            with page.expect_download() as event:page.locator('#'+id).click()
            path=Path(folder)/f'{engine}-tracker.{suffix}';event.value.save_as(path)
            assert path.stat().st_size>30

          # Exact embedded release, narrow-screen reflow and persistent task controls.
          page.goto(base+'/preview.html')
          frame=page.frame_locator('#leh-role-analysis')
          expect(frame.locator('#studio-inputs')).to_be_visible()
          frame.locator('#career-example').click()
          expect(frame.locator('#studio-plan')).to_be_visible()
          with page.expect_download() as event:frame.locator('#studio-plan-download').click()
          embedded=Path(folder)/f'{engine}-embedded.txt';event.value.save_as(embedded)
          assert 'COMPLETE CRITERIA REVIEW' in embedded.read_text()
          page.set_viewport_size({'width':320,'height':740})
          assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(engine,'parent overflow')
          assert frame.locator('html').evaluate('(e)=>e.scrollWidth<=innerWidth+1'),(engine,'frame overflow')
          frame.locator('#tab-resume').click()
          frame.locator('#studio-revision-build').click()
          assert frame.locator('html').evaluate('(e)=>e.scrollWidth<=innerWidth+1'),(engine,'editor overflow')
          page.screenshot(path=str(ROOT/f'usability-{engine}-320.png'),full_page=True)
          frame.locator('html').evaluate("(e)=>e.style.fontSize='24px'")
          assert frame.locator('html').evaluate('(e)=>e.scrollWidth<=innerWidth+1'),(engine,'enlarged text')
          assert not errors,(engine,errors)
          assert not any('Jordan' in url or body for url,method,body in requests if not url.startswith(base)),(engine,'unexpected candidate transmission')
          browser.close()
          print(f'PASS {engine}: one-click review, required/preferred cards, plan bytes, stale state, keyboard tabs, reviewed graph/profile, O*NET and regional wages, real DOCX/PDF export and re-import, text draft, tracker persistence, integrated iframe, 320px/enlarged text')
    finally:
      server.shutdown();server.server_close();worker.join(timeout=5)

if __name__=='__main__':main()
