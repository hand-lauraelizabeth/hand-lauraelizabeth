#!/usr/bin/env python3
"""Build the self-contained WordPress embed for the fixture-mode public explorer.

This packages the default public explorer with the browser service client and
synthetic contract fixtures. It is a publication/build step only; it never
creates staging or production authorization.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path

MODULE_RE=re.compile(r"""<script type="module">\s*import \{MatchingServiceClient,assertContract,validateRuntimeConfig,assertRuntimeMetadata\} from '\./prototype/service-client\.js';([\s\S]*?)</script>""")
FETCH_LOAD="async load(){if(this.mode==='fixture')this.fixtures=await fetch(this.fixtureUrl).then(r=>{if(!r.ok)throw new Error('Unable to load contract fixtures');return r.json()});return this}"
INLINE_LOAD="async load(){if(this.mode==='fixture')this.fixtures=structuredClone(INLINE_FIXTURES);return this}"

def build(source,client_source,fixtures):
 if '"mode":"fixture"' not in source or '"production_authorized":false' not in source:
  raise ValueError("public explorer source must default to non-production fixture mode")
 m=MODULE_RE.search(source)
 if not m:raise ValueError("public explorer module boundary not found")
 client=client_source.replace("export class ","class ").replace("export function ","function ")
 if FETCH_LOAD not in client:raise ValueError("service client fixture load boundary changed")
 client=client.replace(FETCH_LOAD,INLINE_LOAD)
 payload=json.dumps(fixtures,separators=(",",":"),ensure_ascii=False).replace("</","<\\/")
 inline="<script>\nconst INLINE_FIXTURES="+payload+";\n"+client+"\n"+m.group(1)+"\n</script>"
 # Callable replacement is intentional: source code contains $1/$3/etc regex
 # literals that must never be interpreted as replacement-group references.
 out=MODULE_RE.sub(lambda _m:inline,source,count=1)
 checks={
  "module_imports":out.count('<script type="module">'),
  "service_client_classes":out.count("class MatchingServiceClient"),
  "initializers":out.count("(async function(){"),
  "inline_fixture_declarations":out.count("const INLINE_FIXTURES="),
 }
 if checks!={"module_imports":0,"service_client_classes":1,"initializers":1,"inline_fixture_declarations":1}:
  raise ValueError(f"unexpected WordPress explorer embed multiplicity: {checks}")
 return out

def root_fragment(html):
 start=html.find('<div id="leh-ccx">');end=html.rfind('</div>\n</body>')
 if start<0 or end<0:raise ValueError("explorer root bounds not found")
 return html[start:end+6]

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--source",type=Path,required=True);ap.add_argument("--client",type=Path,required=True);ap.add_argument("--fixtures",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--root-only",action="store_true");a=ap.parse_args()
 source=a.source.read_text(encoding="utf-8");client=a.client.read_text(encoding="utf-8");fixtures=json.loads(a.fixtures.read_text(encoding="utf-8"))
 out=build(source,client,fixtures)
 if a.root_only:out=root_fragment(out)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(out,encoding="utf-8")
 print(json.dumps({"output":str(a.output),"fixture_mode":True,"initializer_count":out.count("(async function(){")}))
if __name__=="__main__":main()
