"""Package the same tested workspace and tracker for the existing Divi page."""
from pathlib import Path
import base64
ROOT=Path(__file__).parent
analysis=(ROOT/'index.html').read_text()
tracker=(ROOT/'career-discovery-tracker.html').read_text()
def embed(id,title,content):
    data=base64.b64encode(content.encode()).decode()
    return f'''<iframe id="{id}" data-srcdoc-base64="{data}" title="{title}" srcdoc="&lt;p&gt;Loading your workspace…&lt;/p&gt;" referrerpolicy="no-referrer" style="display:block;width:100%;height:1800px;border:0;background:#faf9f4;"></iframe>'''
host_style='''#leh-reverse-ats{max-width:1280px;margin:auto;color:#193b35;font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}#leh-reverse-ats *{box-sizing:border-box}#leh-reverse-ats>h1{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}#leh-reverse-ats #leh-role-analysis{border:1px solid #dce4dc!important;border-radius:20px}#leh-reverse-ats .tracker-details{margin:24px auto 0;border:1px solid #cad9cc;border-radius:16px;background:#fff;overflow:hidden}#leh-reverse-ats .tracker-details>summary{cursor:pointer;padding:20px 24px;color:#245c49;font-size:20px;font-weight:650}#leh-reverse-ats .tracker-copy{padding:0 24px;color:#526b62;font-size:14px}#leh-reverse-ats .privacy-copy{font-size:12px;color:#526b62;padding:0 24px;margin:20px 0}#leh-reverse-ats summary:focus-visible{outline:3px solid #b9542f;outline-offset:-4px}@media(max-width:700px){#leh-reverse-ats #leh-role-analysis{border:0!important;border-radius:0}#leh-reverse-ats .tracker-details{margin:16px 8px}#leh-reverse-ats .tracker-details>summary{font-size:17px;padding:16px}#leh-reverse-ats .tracker-copy{padding:0 16px}}'''
host_script='''(() => {
  const frames=[document.getElementById('leh-role-analysis'),document.getElementById('leh-role-discovery')];
  window.addEventListener('message',event=>{
    const frame=frames.find(f=>f?.contentWindow===event.source);
    if(!frame||event.data?.type!=='leh-reverse-ats-height')return;
    const height=event.data.height;
    if(typeof height==='number'&&Number.isFinite(height)&&height>300&&height<35000)frame.style.height=Math.ceil(height)+'px';
  });
  frames.forEach(frame=>{const bytes=Uint8Array.from(atob(frame.getAttribute('data-srcdoc-base64')),c=>c.charCodeAt(0));frame.srcdoc=new TextDecoder().decode(bytes);});
})();'''
wrapper=f'''<div id="leh-reverse-ats"><style>{host_style}</style><h1>Reverse ATS · Role Evidence Studio</h1>{embed('leh-role-analysis','Role Evidence Analysis interactive tool',analysis)}<details id="leh-tracker-workspace" class="tracker-details"><summary>Application tracker &amp; career discovery</summary><p class="tracker-copy">Keep role leads, application statuses, and notes in one place. In Evidence &amp; profile above, choose Save profile locally; load that profile here to reuse your evidence. JSON transfer is also available. Existing application notes and statuses are preserved.</p>{embed('leh-role-discovery','Career Discovery and Tracking interactive tool',tracker)}</details><p class="privacy-copy">Your documents and text are processed in your browser. Document libraries and public occupation/wage files load when needed. Optional external-profile/GitHub tools make a request when you use them. Saved profiles and tracker data can remain on this device. Downloads can contain your source details; keep them private.</p><script>{host_script}</script></div>'''
divi='[et_pb_section fb_built="1" _builder_version="4.27.4" custom_padding="18px||36px||true|false" background_color="#faf9f4"][et_pb_row _builder_version="4.27.4" width="98%" max_width="1320px"][et_pb_column type="4_4" _builder_version="4.27.4"][et_pb_code admin_label="Reverse ATS interactive workspaces" _builder_version="4.27.4"]'+wrapper+'[/et_pb_code][/et_pb_column][/et_pb_row][/et_pb_section]'
(ROOT/'wordpress.html').write_text(divi)
(ROOT/'preview.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reverse ATS</title></head><body style="margin:0;background:#faf9f4">'+wrapper+'</body></html>')
print('Built production embed and matching integrated preview:',len(divi.encode()),'bytes.')
