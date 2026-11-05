from pathlib import Path
import base64
import hashlib
import html
import re

root = Path(__file__).parent
source = root
modules = {}
import_line = re.compile(r"^import \{([^}]+)\} from '\./([a-z-]+\.mjs)';[ \t]*$", re.M)
export_declaration = re.compile(r'^export ((?:async )?function|const) (\w+)', re.M)

def collect(name):
    if name in modules:
        return
    code = (source / name).read_text()
    for _, dependency in import_line.findall(code):
        collect(dependency)
    exports = [symbol for _, symbol in export_declaration.findall(code)]
    def require(match):
        names, dependency = match.groups()
        binding = re.sub(r'\s+as\s+', ': ', names.strip())
        return f'const {{{binding}}} = modules[{dependency!r}];'
    code = import_line.sub(require, code)
    code = export_declaration.sub(r'\1 \2', code)
    assert not re.search(r'^\s*(?:import|export)\s', code, re.M), name
    modules[name] = f'modules[{name!r}] = (() => {{\n{code}\nreturn {{{", ".join(exports)}}};\n}})();'

collect('app.mjs')
script = "(() => {\n'use strict';\nconst modules = Object.create(null);\n" + '\n'.join(modules.values()) + '\n})();'
skip_handler = """
document.querySelector('a.skip').addEventListener('click', event => {
  event.preventDefault();
  const main = document.getElementById('main');
  main.focus();
  main.scrollIntoView({block: 'start'});
});
const reportHeight = () => {
  if (window.parent === window) return;
  window.parent.postMessage({
    type: 'leh-evidence-timeline-height',
    height: Math.ceil(document.body.getBoundingClientRect().height) + 16
  }, '*');
};
new ResizeObserver(reportHeight).observe(document.body);
window.addEventListener('message', event => {
  if (event.source === window.parent && event.data?.type === 'leh-evidence-timeline-measure') reportHeight();
});
reportHeight();
"""
script = script[:-5] + skip_handler + '\n})();'
style = (source / 'styles.css').read_text()
assert '</script' not in script.lower() and '</style' not in style.lower()
def csp_hash(text):
    return base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()

csp = (
    "default-src 'none'; "
    f"script-src 'sha256-{csp_hash(script)}'; style-src 'sha256-{csp_hash(style)}'; "
    "connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)
page = (source / 'index.html').read_text()
page, n = re.subn(r'<meta http-equiv="Content-Security-Policy" content="[^"]*">', f'<meta http-equiv="Content-Security-Policy" content="{csp}">', page)
assert n == 1
page = page.replace('<link rel="stylesheet" href="styles.css">', f'<style>{style}</style>')
page = page.replace('<script type="module" src="app.mjs"></script>\n', '')
page = page.replace('</body>', f'<script>{script}</script>\n</body>')
page = page.replace('Evidence &amp; Timeline Builder — Local Review', 'Evidence &amp; Timeline Builder')
page = page.replace('Free tools · Review prototype', 'Free tools · Research and writing')
page = page.replace('Local-only review prototype', 'Browser-local evidence review')
page = page.replace('<main id="main">', '<main id="main" tabindex="-1">')
assert '<link ' not in page and '<script type=' not in page
(root/'bundle.js').write_text(script)
(root/'standalone.html').write_text(page)
host_style = """
body.page-id-1644 #sidebar,body.page-id-1644 #main-content .container:before,body.page-id-1644 .entry-title{display:none}
body.page-id-1644 #left-area{width:100%;padding-right:0;float:none}
body.page-id-1644 #main-content>.container{width:94%;max-width:1280px;padding-top:24px}
body.page-id-1644 #post-1644 .entry-content{padding-top:0}
body.page-id-1644 #leh-evidence-timeline-builder{display:block;width:100%;height:1500px;border:1px solid #dce4dc;border-radius:20px;background:#faf9f4}
@media(max-width:700px){body.page-id-1644 #main-content>.container{width:100%;padding-top:0}body.page-id-1644 #leh-evidence-timeline-builder{border:0;border-radius:0}}
"""
host_script = """
(() => {
  const frame = document.getElementById('leh-evidence-timeline-builder');
  if (!frame) return;
  window.addEventListener('message', event => {
    if (event.source !== frame.contentWindow || event.data?.type !== 'leh-evidence-timeline-height') return;
    const height = event.data.height;
    if (typeof height !== 'number' || !Number.isFinite(height)) return;
    frame.style.height = Math.min(16000, Math.max(650, Math.ceil(height))) + 'px';
  });
  frame.addEventListener('load', () => {
    frame.contentWindow.postMessage({type: 'leh-evidence-timeline-measure'}, '*');
  });
})();
"""
embed = f'''<!-- wp:html -->
<style id="leh-evidence-timeline-page-layout">{host_style}</style>
<iframe id="leh-evidence-timeline-builder" title="Interactive Evidence and Timeline Builder" sandbox="allow-scripts allow-forms allow-downloads allow-modals" referrerpolicy="no-referrer" srcdoc="{html.escape(page, quote=True)}"></iframe>
<script>{host_script}</script>
<!-- /wp:html -->'''
(root/'wordpress.html').write_text(embed)
print(f'{len(modules)} production modules, {len(embed.encode())} bytes of WordPress markup.')
