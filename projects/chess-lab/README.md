# Chess Lab

Open `index.html` for a legal-move chess simulator. Modes: local two-player, local computer (depth-limited minimax), annotated Italian Game. FEN support, move record in SAN, PGN copy, castling, en passant, promotions, draw claims and automated tests.

Run: `node tests.js`. Full project model scope and provenance: [Simulation Lab README](../README.md). Rules reference: [FIDE Laws of Chess](https://handbook.fide.com/chapter/E012023).

## Position coach and export

The position coach derives legal checking moves, legal captures, attacks on the side-to-move's non-king pieces, and a simple material difference. It does **not** rank moves or claim a chess-engine evaluation. PGN exported from a loaded custom FEN now preserves the setup tags, starting move number, and starting side to move. Analysis stays in the browser.

## WordPress publishing safeguard

WordPress auto-paragraph formatting can silently insert `<p>` tags into raw inline JavaScript and stop initialization. **Do not paste the engine/app/enhancement source into page content.** After updating these source files, run `python scripts/build_simulation_loader.py chess` at the repository root (`SIMULATOR` is `chess` or `transit`) and embed the resulting single-line script after the tool's HTML shell, replacing the previous loader. It decodes the exact UTF-8 source in the browser and does not require an external network service. Never keep a second executable copy of the modules on the WordPress page. Purge the page cache and verify in an actual browser that the chessboard contains 64 squares or that Start advances the transit model. A valid source test alone does not validate WordPress's rendered output.

## Guided position practice

Five client-side, deterministic exercises (White and Black checkmates, en passant, castling, a knight fork) load legal positions through the existing FEN interface, provide hints and explanations, and recognize the expected move. They are teaching exercises, not best-move engine analysis; no progress leaves the browser. Run `node projects/chess-lab/practice-tests.js` to validate the curated lines.
