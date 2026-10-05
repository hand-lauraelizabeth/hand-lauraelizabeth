# Text Lens

**Current standalone version:** 3.0

Text Lens is a browser-only text-analysis tool for research, writing, and digital-humanities workflows.

## What it does

- counts words, sentences, paragraphs, characters, unique words, and reading time;
- reports Flesch Reading Ease and Flesch–Kincaid grade estimates;
- summarizes sentence-length distribution and vocabulary concentration;\n- reports length-aware lexical-diversity measures including MATTR-50 and Herdan's C;
- surfaces high-frequency words and configurable repeated 2–4 word phrases;\n- identifies recurring bigram collocations with pointwise mutual information (PMI) and a user-controlled minimum-frequency safeguard;\n- provides exact-token KWIC/concordance search with adjustable context windows;\n- loads one or more local `.txt`, `.md`, `.markdown`, or `.csv` files into either comparison pane without uploading them;\n- retains each loaded file as a separate document for per-file word, sentence, readability, MATTR-50, and Herdan's C reporting before corpus concatenation;
- provides a transparent lexicon-and-negation sentiment signal with in-context highlighting;
- compares two texts using word-frequency cosine similarity, Jaccard vocabulary overlap, normalized lexical differences, and side-by-side descriptive metrics;
- copies a compact summary, exports JSON analysis without source text, and exports frequency/collocation/current-concordance tables as CSV.

## Method boundaries

Readability and syllable counts are English-language heuristics. The sentiment panel is not a trained sentiment model. Cosine/Jaccard and frequency differences describe lexical overlap and prominence, not semantic equivalence. MATTR-50 is withheld below 50 words. PMI can over-emphasize rare word pairs, so the tool requires a user-selected minimum occurrence count. Concordance uses exact normalized tokens rather than stemming or semantic search. Text and locally selected files are processed in the browser and are not uploaded by the tool.

## Portfolio implementation

The public WordPress version uses the same dark-navy / sage / cream system as the rest of Laura Elizabeth Hand's portfolio and is scoped to avoid leaking CSS into the surrounding theme.

The standalone file is `text-lens.html`.
