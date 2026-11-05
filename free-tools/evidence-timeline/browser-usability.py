"""Exercise the deployed bundle's entry, edit, search, save and reopen workflow."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import json
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

def main():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with TemporaryDirectory() as folder, sync_playwright() as playwright:
            for engine in ('chromium', 'firefox', 'webkit'):
                browser = getattr(playwright, engine).launch()
                page = browser.new_page(viewport={'width':1280, 'height':900}, accept_downloads=True)
                errors, external = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: external.append(request.url)
                        if not request.url.startswith(base + '/') and not request.url.startswith('blob:') else None)
                assert page.goto(base + '/standalone.html').status == 200
                assert page.get_by_role('button', name='Try the 3-entry example').is_visible()
                assert page.locator('#entry-form [required]').count() == 3
                page.locator('#load-example').click()
                assert page.locator('#records > li').count() == 3
                assert page.locator('#needs-review').inner_text() == '2'
                page.locator('#text-search').fill('March 15')
                assert page.locator('#records > li').count() == 1
                assert 'EXAMPLE-EMAIL-002' in page.locator('#records').inner_text()

                page.get_by_role('button', name='Edit entry EXAMPLE-EMAIL-002', exact=True).click()
                page.locator('#claim').fill('A fictional signed decision confirms March 15.')
                page.locator('#save-entry').click()
                assert page.locator('#records > li').count() == 3
                assert 'signed decision' in page.locator('#records').inner_text()
                page.get_by_role('button', name='Edit entry EXAMPLE-EMAIL-002', exact=True).click()
                page.locator('#sourceId').fill('EXAMPLE-MINUTES-001')
                page.locator('#save-entry').click()
                assert page.locator('#error').is_visible()
                assert page.locator('#sourceId').get_attribute('aria-invalid') == 'true'
                assert page.locator('#records > li').count() == 3
                page.locator('#cancel-entry-edit').click()
                page.locator('#date').fill('2026-01-21')
                page.locator('#date-range-options > summary').click()
                page.locator('#endDate').fill('2026-01-26')
                page.locator('#sourceId').fill('SYNTHETIC-004')
                page.locator('#claim').fill('A fourth fictional record for the review.')
                page.locator('#save-entry').click()
                assert page.locator('#records > li').count() == 4
                page.get_by_role('button', name='Edit entry SYNTHETIC-004', exact=True).click()
                assert page.locator('#endDate').input_value() == '2026-01-26'
                page.locator('#endDate').fill('2026-01-20')
                page.locator('#save-entry').click()
                assert 'End date' in page.locator('#error').inner_text()
                assert page.locator('#endDate').get_attribute('aria-invalid') == 'true'
                page.locator('#cancel-entry-edit').click()

                page.locator('#chart-preview > summary').click()
                page.locator('#visual-chart svg').wait_for(state='visible')
                assert page.locator('#visual-chart svg').count() == 1
                assert page.locator('#visual-chart svg path').count() == 3
                assert 'Jan 26, 2026' in page.locator('#visual-summary').inner_text()
                with page.expect_download() as event:
                    page.locator('#download-gantt').click()
                gantt = Path(folder) / f'{engine}-gantt.xlsx'
                event.value.save_as(gantt)
                with ZipFile(gantt) as archive:
                    assert archive.testzip() is None
                    for name in archive.namelist():
                        ET.fromstring(archive.read(name))
                    ns = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    schedule = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
                    source = ET.fromstring(archive.read('xl/worksheets/sheet2.xml'))
                    assert len(schedule.findall('.//m:row', ns)) == 11
                    assert len(source.findall('.//m:row', ns)) == 11
                    assert 'SYNTHETIC-004' in ''.join(source.itertext())
                    assert schedule.find('.//m:c[@r="C12"]/m:v', ns).text == '46043'
                    assert schedule.find('.//m:c[@r="D12"]/m:v', ns).text == '46048'
                    assert schedule.find('.//m:c[@r="O12"]/m:v', ns).text == '■'
                    assert not source.findall('.//m:f', ns)
                    assert len(schedule.findall('.//m:cfRule',ns)) == 2
                with page.expect_download() as event:
                    page.locator('#download-visual').click()
                visual = Path(folder) / f'{engine}-visual.svg'
                event.value.save_as(visual)
                assert 'Timeline visual download started · 4 entries.' in page.locator('#visual-status').inner_text()
                image = ET.fromstring(visual.read_text())
                assert 'SYNTHETIC-004' in ''.join(image.itertext())
                assert len(image.findall('.//{http://www.w3.org/2000/svg}path')) == 3
                page.screenshot(path=str(ROOT / f'usability-{engine}-visual-desktop.png'), full_page=True)

                with page.expect_download() as event:
                    page.locator('#save-work').click()
                saved = Path(folder) / f'{engine}-timeline.json'
                event.value.save_as(saved)
                payload = json.loads(saved.read_text())
                assert payload['schema'] == 'evidence-timeline-v1'
                assert len(payload['records']) == 4
                assert next(row for row in payload['records'] if row['sourceId']=='SYNTHETIC-004')['endDate']=='2026-01-26'
                assert next(row for row in payload['records']
                            if row['sourceId'] == 'EXAMPLE-EMAIL-002')['claim'] == 'A fictional signed decision confirms March 15.'
                page.locator('#text-search').fill('signed decision')
                assert page.locator('#records > li').count() == 1
                page.locator('#visual-scope').select_option('visible')
                assert '1 of 4 entries' in page.locator('#visual-summary').inner_text()
                with page.expect_download() as event:
                    page.locator('#download-gantt').click()
                filtered_gantt = Path(folder) / f'{engine}-filtered.xlsx'
                event.value.save_as(filtered_gantt)
                assert 'Excel Gantt download started · 1 entry.' in page.locator('#visual-status').inner_text()
                with ZipFile(filtered_gantt) as archive:
                    assert 'EXAMPLE-EMAIL-002' in archive.read('xl/worksheets/sheet2.xml').decode()
                    assert 'EXAMPLE-MINUTES-001' not in archive.read('xl/worksheets/sheet2.xml').decode()
                    assert 'Filtered entries · 1 of 4 entries' in archive.read('xl/worksheets/sheet1.xml').decode()
                page.locator('#text-search').fill('no possible match')
                assert page.locator('#download-gantt').is_disabled()
                assert page.locator('#download-visual').is_disabled()
                page.locator('#visual-scope').select_option('all')
                assert page.locator('#download-gantt').is_enabled()
                page.locator('#text-search').fill('signed decision')
                page.locator('.more-exports > summary').click()
                with page.expect_download() as event:
                    page.locator('#download-filtered').click()
                filtered = Path(folder) / f'{engine}-filtered.txt'
                event.value.save_as(filtered)
                contents = filtered.read_text()
                assert '1 of 4 entries' in contents
                assert 'EXAMPLE-EMAIL-002' in contents
                assert 'EXAMPLE-MINUTES-001' not in contents
                assert 'signed decision' in contents
                with page.expect_download() as event:
                    page.locator('#download-readable').click()
                readable = Path(folder) / f'{engine}-readable.txt'
                event.value.save_as(readable)
                assert 'SYNTHETIC-004' in readable.read_text()
                assert 'EXAMPLE-MINUTES-001' in readable.read_text()

                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#clear').click()
                assert page.locator('#records > li').count() == 0
                page.locator('#open-saved').click()
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#resume-json').set_input_files(saved)
                page.locator('#records > li').nth(3).wait_for(state='visible')
                assert 'signed decision' in page.locator('#records').inner_text()
                assert 'Jan 26, 2026' in page.locator('#visual-summary').inner_text()

                page.set_viewport_size({'width':320, 'height':740})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), engine
                assert page.locator('#save-entry').is_visible()
                assert page.locator('#records > li').count() == 4
                page.screenshot(path=str(ROOT / f'usability-{engine}-320.png'), full_page=True)
                page.evaluate("document.documentElement.style.fontSize='24px'")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (engine, 'enlarged text')
                assert not errors, (engine, errors)
                assert not external, (engine, external)
                browser.close()
                print(f'PASS {engine}: example, editing, date ranges, duplicate recovery, scoped XLSX/SVG bytes and XML, empty filters, search, save/reopen, 320px and enlarged text')
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

if __name__ == '__main__':
    main()
