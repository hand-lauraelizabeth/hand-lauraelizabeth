# Text Lens

Text Lens is a browser-only text-analysis tool for research, writing, and digital-humanities workflows.

## What it does

- counts words, sentences, paragraphs, characters, unique words, and reading time;
- reports Flesch Reading Ease and Flesch–Kincaid grade estimates;
- summarizes sentence-length distribution and vocabulary concentration;
- surfaces high-frequency words and configurable repeated 2–4 word phrases;
- provides a transparent lexicon-and-negation sentiment signal with in-context highlighting;
- compares two texts using word-frequency cosine similarity, Jaccard vocabulary overlap, normalized lexical differences, and side-by-side descriptive metrics;
- copies a compact summary and exports a JSON analysis without including the source text.

## Method boundaries

Readability and syllable counts are English-language heuristics. The sentiment panel is not a trained sentiment model. Cosine/Jaccard and frequency differences describe lexical overlap and prominence, not semantic equivalence. Text is processed locally in the browser and is not uploaded by the tool.

## Portfolio implementation

The public WordPress version uses the same dark-navy / sage / cream system as the rest of Laura Elizabeth Hand's portfolio and is scoped to avoid leaking CSS into the surrounding theme.

The standalone file is `text-lens.html`.
