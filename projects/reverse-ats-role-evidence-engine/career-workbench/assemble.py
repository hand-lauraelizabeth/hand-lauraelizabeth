"""Integrate the workbench into the existing analysis document without changing its engine."""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--data-base', required=True, help='Directory URL for the generated public data files')
parser.add_argument('--source', default='analysis.html')
parser.add_argument('--output', default='wordpress-analysis.html')
args = parser.parse_args()

html = Path(args.source).read_text()


def replace(old, new):
    global html
    if html.count(old) != 1:
        raise ValueError(f'Expected a unique source marker: {old[:90]}')
    html = html.replace(old, new, 1)


replace('</head>', '<style>\n' + Path('workbench.css').read_text() + '</style>\n</head>')
replace('Career intelligence · explainable evidence matching · local-first prototype', 'Career planning · Résumé evidence · Regional wages')
replace('v2.6</span>', 'v3.0</span>')
replace('  <p>Parse a job description into requirements, compare them with candidate evidence, and separate likely capability gaps from evidence-visibility gaps. This does not emulate a proprietary ATS.</p>', '''  <p>Start with your résumé to explore roles and regional pay, or add a job posting to see what evidence a reviewer could find.</p>
  <nav class="career-start" aria-label="Choose a task">
    <a href="#career-inputs">1. Add your résumé</a>
    <a href="#career-workbench">2. Explore roles &amp; pay</a>
    <a href="#resume-workbench">3. Draft a résumé</a>
    <a href="#reverse-ats-audit">Review a posting</a>
    <button class="btn ghost" id="career-example" type="button">Try a fictional example</button>
  </nav>''')
replace('<main>\n<div class="grid">', '<main id="career-inputs">\n<div class="grid">')
replace('<h2>Target job</h2>\n<textarea id="job"', '<h2 id="job-input-heading">Target job <small class="muted">(optional)</small></h2>\n<textarea id="job" aria-labelledby="job-input-heading"')
replace('<h2>Candidate evidence</h2>\n<textarea id="candidate"', '<h2 id="candidate-input-heading">Résumé &amp; evidence</h2>\n<textarea id="candidate" aria-labelledby="candidate-input-heading"')
replace('<div class="row"><button class="btn ghost" id="sampleCandidate">', '<label for="career-file" class="career-file-label">Open a plain-text résumé (.txt)</label><input id="career-file" type="file" accept=".txt,text/plain"><p id="career-input-status" class="muted" role="status"></p>\n<div class="row"><button class="btn ghost" id="sampleCandidate">')
replace('<section class="panel ats-review"', Path('workbench.html').read_text() + '\n<section class="panel ats-review"')
replace('</section>\n<div class="panel" style="margin-top:12px">\n<h3>Shared candidate profile</h3>', '</section>\n<details class="panel career-advanced" id="career-evidence-tools"><summary>Evidence tools · profile, requirements, and claim review</summary>\n<div class="panel" style="margin-top:12px">\n<h3>Shared candidate profile</h3>')
replace('</details>\n</main>', '</details>\n</details>\n</main>')

names = sorted(path.stem for path in Path('data').glob('*.b64'))
if len(names) < 3 or not {'occupations', 'geography'} <= set(names):
    raise ValueError('Missing source-data assets')
assets = {name: f'{args.data_base.rstrip("/")}/{name}.b64' for name in names}
script = Path('career-workbench.js').read_text()
if '</script' in script.lower():
    raise ValueError('Unexpected script delimiter')
replace('</body></html>', f'<script>\nwindow.roleEvidenceData = {json.dumps(assets)};\n{script}\n</script>\n</body></html>')
Path(args.output).write_text(html)
