# Chess Lab

Open `index.html` for a legal-move chess simulator. Modes: local two-player, local computer (depth-limited minimax), annotated Italian Game. FEN support, move record in SAN, PGN copy, castling, en passant, promotions, draw claims and automated tests.

Run: `node tests.js`. Full project model scope and provenance: [Simulation Lab README](../README.md). Rules reference: [FIDE Laws of Chess](https://handbook.fide.com/chapter/E012023).

## Position coach and export

The position coach derives legal checking moves, legal captures, attacks on the side-to-move's non-king pieces, and a simple material difference. It does **not** rank moves or claim a chess-engine evaluation. PGN exported from a loaded custom FEN now preserves the setup tags, starting move number, and starting side to move. Analysis stays in the browser.
