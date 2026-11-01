# Text Lens

**Current standalone version:** 3.5

Text Lens is a browser-only text-analysis tool for research, writing, and digital-humanities workflows.

## What it does

- counts words, sentences, paragraphs, characters, unique words, and reading time;
- reports Flesch Reading Ease and Flesch–Kincaid grade estimates;
- summarizes sentence-length distribution and vocabulary concentration;\n- reports length-aware lexical-diversity measures including MATTR-50 and Herdan's C;
- surfaces high-frequency words and configurable repeated 2–4 word phrases;\n- identifies recurring bigram collocations with pointwise mutual information (PMI) and a user-controlled minimum-frequency safeguard;\n- provides exact-token KWIC/concordance search with adjustable context windows;\n- loads one or more local `.txt`, `.md`, `.markdown`, or `.csv` files into either comparison pane without uploading them;\n- retains each loaded file as a separate document for per-file word, sentence, readability, MATTR-50, and Herdan's C reporting before corpus concatenation;\n- compares loaded documents with word-frequency cosine similarity and surfaces per-document distinctive terms using positive signed log-likelihood G² against the remainder of the corpus with a user-controlled minimum-frequency floor;\n- lets users focus a single loaded document for keyness and concordance;\n- lets users reorder or remove loaded documents without losing the remaining files' local provenance;\n- supports the remainder of the corpus, one explicitly selected document, or a custom multi-document reference set as the keyness reference;\n- saves and restores corpus setups as source-free JSON containing analysis settings plus file name/size/last-modified/order metadata, never document contents;\n- groups loaded documents visibly by Text A and Text B, labels active focus/reference roles, and provides select-all/clear controls for custom reference sets;\n- presents document keyness as an explicit target/reference/distinctive-terms comparison table rather than a card grid;\n- adds accessible within-corpus visual bars for word count, MATTR-50, Flesch reading ease, or sentence count, plus native similarity meters;
- provides a transparent lexicon-and-negation sentiment signal with in-context highlighting;
- compares two texts using word-frequency cosine similarity, Jaccard vocabulary overlap, normalized lexical differences, and side-by-side descriptive metrics;
- copies a compact summary, exports JSON analysis without source text, and exports frequency/collocation/current-concordance tables as CSV.

## Method boundaries

Readability and syllable counts are English-language heuristics. The sentiment panel is not a trained sentiment model. Cosine/Jaccard and frequency differences describe lexical overlap and prominence, not semantic equivalence. MATTR-50 is withheld below 50 words. PMI can over-emphasize rare word pairs, so the tool requires a user-selected minimum occurrence count. Concordance uses exact normalized tokens rather than stemming or semantic search. Cross-document cosine similarity is lexical rather than semantic, and signed log-likelihood G² is a distributional keyness statistic rather than a measure of importance or quality. Document-profile bars are scaled only within the currently loaded corpus and are not benchmark scores. Reordering changes presentation/export order only; removing a document rebuilds the relevant Text A/Text B corpus from the remaining local files. An explicit or custom keyness reference changes the comparison distribution but does not convert keyness into a semantic or evaluative score. Custom references exclude the target document from its own reference distribution. Setup files are configuration aids, not corpus archives: the matching local source files must still be loaded for full restoration. Text and locally selected files are processed in the browser and are not uploaded by the tool.

## Portfolio implementation

The public WordPress version uses the same dark-navy / sage / cream system as the rest of Laura Elizabeth Hand's portfolio and is scoped to avoid leaking CSS into the surrounding theme.

The standalone file is `text-lens.html`.

## Exporting unavailable metrics

Analysis-table CSV and JSON downloads explicitly label non-finite calculated values as `not available (non-finite metric)` rather than showing `NaN`/`Infinity` in CSV or silently converting them to `null` in JSON. Finite numeric scores, including negative values and zero, remain numeric; original source names and identifiers remain unchanged. A missing score is not zero. Table CSV refuses formula-like or control-character text; use the exact table JSON for such source values. These local exports may contain sensitive passages.

Table CSV/JSON downloads report when a browser download was **started**, not when the file was saved. If a download is blocked, Text Lens reports a recoverable error, retains local analysis and exact source identifiers, and cleans up temporary browser resources. Check the browser downloads list to confirm completion.

## Local source identity

Local file names and cross-tool source labels may contain ordinary Unicode, including accents, CJK characters, and emoji. Text Lens rejects source labels with control characters, line breaks, Unicode directional formatting marks, or invalid surrogate sequences rather than displaying a misleading filename. The text and exact accepted label are not normalized.

A local `text-lens:import` integration must supply a nonempty UTF-8 text string, its **actual UTF-8 byte count** as `size`, and a display-safe `name`. UTF-16 character counts are not UTF-8 byte counts. A mismatched byte count, malformed Unicode, or deceptive label produces a text error without replacing the previously analyzed source. This consistency check does not prove that the supplied text came from a particular external file; verify file identity separately when it matters.

A rejected cross-tool import leaves your current text and local evidence unchanged and keeps its error visible, even if an earlier text edit was waiting to be analyzed. A subsequent valid import replaces that pending edit and analyzes the accepted text.
