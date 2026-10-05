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
