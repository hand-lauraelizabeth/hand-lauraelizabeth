"""Execute the committed synthetic preview's real JavaScript against a minimal DOM.

No external packages, real 311 records, or network access are required.
This is a DOM-behavior regression, not a native screen-reader certification.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

HTML = Path(__file__).with_name("synthetic_coarse_preview.html")
HARNESS = r"""
const vm = require('node:vm');
const script = process.argv[1];
const source = JSON.parse(process.argv[2]);
class Element {
  constructor(tag='div') {
    this.tagName=tag;this.children=[];this.listeners={};this.attributes={};
    this.textContent='';this.value='';this.disabled=false;this.focused=false;
  }
  appendChild(node){this.children.push(node)}
  replaceChildren(...nodes){this.children=nodes.flatMap(n=>n.tagName==='fragment'?n.children:[n])}
  setAttribute(key,value){this.attributes[key]=value}
  addEventListener(type,callback){this.listeners[type]=callback}
  focus(){this.focused=true}
}
function start(fixture) {
  const elements={};
  for(const id of ['synthetic-cells','borough','group','sort','results','summary','reset'])
    elements[id]=new Element();
  elements['synthetic-cells'].textContent=JSON.stringify(fixture);
  elements.sort.value='borough';
  const document={
    getElementById(id){return elements[id]},
    createDocumentFragment(){return new Element('fragment')},
    createElement(tag){return new Element(tag)}
  };
  vm.runInNewContext(script,{document,Intl,JSON,Set,Object,Number,Array,Error});
  return elements;
}
const el=start(source);
const initial={
  count:el.results.children.length,
  headings:el.results.children.filter(tr=>tr.children.length===3 &&
    tr.children[0].tagName==='th' && tr.children[0].attributes.scope==='row').length,
  first:el.results.children[0].children.map(x=>x.textContent),
  status:el.summary.textContent
};
el.borough.value='Queens';el.borough.listeners.change();
el.group.value='Group C';el.group.listeners.change();
const filtered={
  count:el.results.children.length,
  first:el.results.children[0].children.map(x=>x.textContent),
  status:el.summary.textContent
};
el.borough.value='';el.group.value='';el.sort.value='high';el.sort.listeners.change();
const sorted={first:el.results.children[0].children.map(x=>x.textContent)};
el.reset.listeners.click();
const reset={
  count:el.results.children.length,
  borough:el.borough.value,group:el.group.value,sort:el.sort.value,
  focused:el.borough.focused
};
const tampered=JSON.parse(JSON.stringify(source));
tampered[0].requests+=1;
const bad=start(tampered);
const failClosed={
  count:bad.results.children.length,
  disabled:['borough','group','sort','reset'].every(id=>bad[id].disabled),
  role:bad.summary.attributes.role,
  text:bad.summary.textContent
};
process.stdout.write(JSON.stringify({initial,filtered,sorted,reset,failClosed}));
"""

class SyntheticInteractionContract(unittest.TestCase):
    def test_real_committed_javascript_filter_sort_reset_and_fail_closed(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node unavailable")
        html = HTML.read_text(encoding="utf-8")
        match = re.search(r'<script id="synthetic-cells" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(match)
        fixture = json.loads(match.group(1))
        scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
        self.assertEqual(len(scripts), 1)
        proc = subprocess.run(
            [node, "-e", HARNESS, scripts[0], json.dumps(fixture)],
            capture_output=True, text=True, timeout=20, check=True,
        )
        got = json.loads(proc.stdout)
        self.assertEqual(got["initial"]["count"], 20)
        self.assertEqual(got["initial"]["headings"], 20)
        self.assertEqual(got["initial"]["first"], ["Bronx", "Group A", "810"])
        self.assertIn("all boroughs / all groups", got["initial"]["status"])
        self.assertEqual(got["filtered"]["count"], 1)
        self.assertEqual(got["filtered"]["first"], ["Queens", "Group C", "850"])
        self.assertIn("Queens / Group C", got["filtered"]["status"])
        self.assertEqual(got["sorted"]["first"], ["Queens", "Group A", "1,100"])
        self.assertEqual(got["reset"], {
            "count":20,"borough":"","group":"","sort":"borough","focused":True
        })
        self.assertEqual(got["failClosed"]["count"], 0)
        self.assertTrue(got["failClosed"]["disabled"])
        self.assertEqual(got["failClosed"]["role"], "alert")
        self.assertIn("No counts are shown.", got["failClosed"]["text"])

if __name__ == "__main__":
    unittest.main()
