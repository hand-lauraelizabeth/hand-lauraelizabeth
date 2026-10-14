#!/usr/bin/env python3
"""Build a portable, deploy-ready static site for three responsible-AI demos.

No external JS, accounts, telemetry, or private data. This command ONLY builds
local files; publication requires a separate explicit release action.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist/responsible-ai"

TOOLS = [
    ("prompt-literacy-debugger", "Prompt Literacy Debugger",
     "Diagnose task clarity, evidence limits, verification, and human responsibility."),
    ("evidence-safe-prompt-lab", "Evidence-Safe Prompt Lab",
     "Build evidence-bound prompts with human-assigned source support and counterevidence."),
    ("ethical-ai-scenario-auditor", "Ethical AI Scenario Auditor",
     "Plan controls, accountable owners, validation, oversight, and appeals."),
]

def main() -> None:
    if DEST == ROOT or ROOT in DEST.parents and not str(DEST).startswith(str(ROOT / "dist")):
        raise SystemExit("Output must be an isolated dist directory, not project sources.")
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    manifest = {"tools": []}
    for slug,name,description in TOOLS:
        source=ROOT / "projects" / slug / "index.html"
        assert source.is_file(), source
        raw=source.read_bytes()
        assert b"<main" in raw and b"<script" in raw, f"Missing accessible markup: {source}"
        target=DEST / slug / "index.html"
        target.parent.mkdir(parents=True)
        target.write_bytes(raw)
        manifest["tools"].append({
            "slug":slug, "title":name, "file":f"{slug}/index.html",
            "sha256":sha256(raw).hexdigest()
        })
    cards="\n".join(
        f'<article class="card"><h2>{escape(name)}</h2><p>{escape(desc)}</p>'
        f'<a href="{escape(slug)}/index.html">Open {escape(name)}</a></article>'
        for slug,name,desc in TOOLS
    )
    page="""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Three free browser-based demonstrations for evidence-aware and responsible AI workflows.">
<title>Responsible AI | Interactive Demonstrations</title>
<style>
:root{color-scheme:light;--ink:#1b2a24;--sage:#285c4b;--border:#c7d6ce}
*{box-sizing:border-box}body{margin:0;background:#f7faf8;color:var(--ink);font:16px/1.6 system-ui,sans-serif}
main{max-width:1050px;margin:auto;padding:clamp(24px,5vw,64px) 20px}
.kicker{font-size:.82rem;letter-spacing:.1em;text-transform:uppercase;color:var(--sage);font-weight:700}
h1{font-size:clamp(2rem,5vw,3.1rem);line-height:1.12}h2{line-height:1.25}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin:32px 0}
.card{background:#fff;border:1px solid var(--border);border-radius:16px;padding:24px}
a{color:#1d4e3e;text-decoration:underline;text-underline-offset:3px}
a:focus-visible{outline:3px solid #275a48;outline-offset:4px}
aside{border-top:1px solid var(--border);padding-top:22px}
</style></head><body>
<main>
<p class="kicker">Open teaching and research resources</p>
<h1>Responsible AI: interactive demonstrations</h1>
<p>Three free, client-side tools for examining prompts, source support, and the consequences of AI-assisted workflows. These demonstrations do not call an AI API; you can use them without an account.</p>
<div class="grid">
""" + cards + """
</div>
<aside aria-label="Method and related tools">
<h2>Interpreting your results</h2>
<p>These tools organize human judgments and provide provisional prompts or controls; they do not independently establish factual accuracy, legal compliance, or suitability for consequential decisions. Do not enter private, confidential, or restricted material.</p>
<p>Related published portfolio resources: <a href="https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/prompt-lab/">Prompt Lab</a> and <a href="https://www.lauraelizabethhand.com/resources/learning-curriculum-tools/ai-use-decision-lab/">AI Use Decision Lab</a>.</p>
</aside>
</main></body></html>
"""
    (DEST / "index.html").write_text(page,encoding="utf-8")
    (DEST / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    for item in manifest["tools"]:
        target=DEST / item["file"]
        assert sha256(target.read_bytes()).hexdigest()==item["sha256"]
        assert f'href="{item["file"]}"' in page, item
    print("PASS static responsible-AI bundle: three reachable local demos, provenance hashes, no duplicate source editing")
    print("Staged:",DEST,"(not published)")


if __name__=="__main__":
    main()
