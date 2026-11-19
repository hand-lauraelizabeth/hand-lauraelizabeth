#!/usr/bin/env python3
"""Generate WordPress-safe, browser-local simulation script bootstraps.

Usage:
    python scripts/build_simulation_loader.py chess > chess-loader.html
    python scripts/build_simulation_loader.py transit > transit-loader.html

Place the generated tag after each simulator's HTML shell in WordPress. Remove
older raw inline script blocks. Do not paste the source modules directly:
WordPress's auto-paragraph filter can insert HTML into JavaScript and prevent
the chessboard and transit controls from initializing.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "chess": ("projects/chess-lab/engine.js", "projects/chess-lab/app.js", "projects/chess-lab/coach-enhancements.js", "projects/chess-lab/practice.js"),
    "transit": ("projects/transit-lab/models.js", "projects/transit-lab/app.js", "projects/transit-lab/accuracy-enhancements.js", "projects/transit-lab/missions.js", "projects/transit-lab/experiments.js", "projects/transit-lab/visuals.js"),
}


def generate(mode: str, root: Path = REPO_ROOT) -> str:
    if mode not in MODULES:
        raise ValueError(f"Unknown simulator: {mode}")
    payloads = []
    for file in MODULES[mode]:
        source = (root / file).read_bytes()
        if not source.strip():
            raise ValueError(f"Empty source file: {file}")
        payloads.append(base64.b64encode(source).decode("ascii"))
    check = (
        'if(document.querySelectorAll("#cl-board button").length!==64)'
        'throw Error("Chessboard did not initialize")'
        if mode == "chess" else
        'if(!document.getElementById("tl-play"))'
        'throw Error("Transit controls unavailable")'
    )
    fallback_id = "cl-board" if mode == "chess" else "tl-status"
    js = (
        '!function(){try{for(const code of ' + json.dumps(payloads, separators=(",", ":")) +
        '){const s=document.createElement("script");'
        's.textContent=new TextDecoder().decode(Uint8Array.from(atob(code),c=>c.charCodeAt(0)));'
        'document.body.appendChild(s)}' + check +
        '}catch(e){console.error("Simulation loader:",e);'
        f'const x=document.getElementById("{fallback_id}");'
        'if(x)x.textContent="Simulator could not initialize. Reload this page; if it persists, report the issue."}}();'
    )
    if "\n" in js or "</script" in js.lower():
        raise ValueError("The loader must remain one line without script delimiters")
    return f'<script id="leh-{mode}-safe-loader">{js}</script>'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("simulator", choices=sorted(MODULES))
    parser.add_argument("--output", type=Path, help="Save the HTML instead of printing it")
    args = parser.parse_args()
    html = generate(args.simulator)
    if args.output:
        args.output.write_text(html + "\n", encoding="utf-8")
    else:
        print(html)


if __name__ == "__main__":
    main()
