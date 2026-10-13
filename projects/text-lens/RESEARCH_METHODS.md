# Text Lens: Research Methods and Development Directions

Text Lens is a privacy-conscious, in-browser textual analysis instrument designed to support both literary interpretation and business research. It provides descriptive lexical evidence and comparative statistics; it does not infer an author's intentions, diagnose emotions, or claim that surface words establish customers' true opinions.

## Implemented methods (v7, October 2026)

| Layer | Evidence | Visualization | Interpretation limit |
|---|---|---|---|
| Context-adjusted evaluative polarity | Locally defined positive/negative cues, short-scope negation, scalar modifiers, contrast indicators | Polarity meter, passage trajectory, highlighting | Cannot reliably interpret irony, quoted voices, long-distance negation or metaphor |
| Literary affective themes | Curated keywords for foreboding, mortality, malevolence, grief, renewal, wonder, conflict | Category bars, passage heatmap, thematic word cloud | A theme word is not a direct report of narrator or character emotion |
| Business textual themes | Curated keywords for trust, friction, compliance risk, satisfaction, growth, change | Category bars, passage heatmap, frequency word cloud | A cue is not proof of product failure, organizational risk or sentiment toward a target |
| Cross-document comparison | Counts per 1,000 words, relative word-frequency comparison | Two-document thematic comparison and corpus document profile | Very short texts and low-frequency cues produce unstable rates; descriptive, not inferential |
| Linguistic style and corpus exploration | Token/sentence counts, MATTR, readability estimates, phrases, collocations, keyword-in-context, keyness and lexical similarity | Existing metrics, tables and document charts | Surface lexical similarity is not semantic similarity |

**Reproducibility:** Source text is processed locally in the user's browser and is not included in exported analysis JSON. Analysis exports include model/version metadata, per-document descriptive metrics, contextual sentiment, matched thematic vocabulary counts and counts by passage. A saved corpus setup stores local file metadata and settings, not source text. Reproducing results still requires the same source texts and a matching Text Lens lexicon version.

**Vocabulary policy:** The embedded thematic vocabulary is independently curated; there is no redistribution of the NRC Emotion Lexicon or other restricted commercial datasets. Category memberships are transparent and adjustable through future user-defined lexicons. No categorical emotion percentages should be interpreted as probabilities.


## Evidence register and long-form parsing (v6)

- Text A and Text B each accept up to **400,000 characters**; up to 800,000 characters can be compared in two-text mode. Local text/Markdown/CSV imports enforce the same per-text cap. An existing browser-local PDF/DOCX text extraction widget is also updated to that cap; it loads external extraction libraries as necessary but does not upload documents to Text Lens. Scans still need OCR, and extracted PDF lines/pages should not be assumed accurate.
- Sentence boundaries are determined from punctuation end stops (periods, exclamation marks, question marks) and a bounded abbreviation/initial exception list. Single line breaks, double line breaks, pagination wraps, and inserted returns **do not themselves end a sentence**. This is intentionally designed for hard-wrapped book text; punctuation in dialogue, ellipses, editorial abbreviation conventions, poetry and OCR can still be ambiguous. Both readability and contextual sentiment use the same segmentation.
- The searchable evidence register merges sentiment and thematic cues occurring at the same token into one row. Rows include source text (A/B), imported file name or pasted origin, categorical memberships, polarity, negation, intensity and contrast adjustments, short source passage, sentence number, source line number, source-relative 1-based character offset, text-level word number and percentage position within the source.
- When multiple local documents are concatenated, source passages are bounded by each original document. Physical source lines are based on imported line-break characters and are **not** verified printed book line numbers or PDF page coordinates.
- Evidence register search matches term, source, sentence excerpt, polarity and category. Additional filters select Text A/B, positive/negative/thematic-only, and category. Results are paged at 40 rows; filtering and CSV export cover all cues.
- The evidence CSV intentionally includes **short verbatim source excerpts**, unlike the default source-free analysis JSON. Users should consider permissions, confidentiality and copyright before sharing CSV. CSV cells with formula-like prefixes are escaped for safer spreadsheet import.
- For large inputs, inline highlighting is limited to the first 60,000 characters to keep the browser responsive. The evidence index analyzes and searches the complete input; it does not apply that visual limit to cue detection.
- All metrics are descriptive and heuristic. No author/speaker identification, aspect-target attachment, LLM inference, or machine-learned classifier has been introduced in v6.


## Speaker-aware and aspect-aware exploratory evidence (v7, October 2026)

Text Lens v7 extends the *existing* cue evidence register instead of introducing a separate scoring tool. For each evaluative or thematic cue, it uses a bounded, transparent rule set to assign these **suggested** distinctions:

- **Voice:** directly quoted text, an explicitly reported claim (e.g., “according to the manager” / “customers reported”), or unattributed prose. Unattributed prose is intentionally *not* labeled as the narrator's opinion or the author's beliefs.
- **Reported speaker/source:** only an adjacent explicit speech-reporting construction such as “Maria said, ‘…’” or “‘…,’ the customer replied” produces a named mention. Third-person pronouns (“he”, “she”, “they”) are recorded as *unresolved pronoun mentions*, never silently linked to named characters. Quoted phrases without a speech-reporting construction have an unknown source.
- **Evaluated aspect:** a local, interpretable phrase pattern such as “the wait was terrible”, “staff were helpful”, “hated the pricing”, or “the wicked king”. It does not currently perform dependency parsing, entity resolution, semantic role labeling, or aspect clustering. A thematic cue such as “death” without evaluative use is **not** forced to carry an aspect.
- **Inspection:** users can search and filter the register by voice type and whether an aspect was suggested, inspect the rule used, and view cue-count bar charts grouped by suggested aspect. The bars show positive/negative *matched cues*, not model probabilities, entity sentiment scores, or business outcome indicators.
- **Export:** additional CSV fields for voice type, source mention, source resolution, attribution rule, candidate aspect, and local matching rule. Short source passages remain in evidence CSV by explicit user download, not in the source-free analysis JSON.

**Boundaries:** straight double quotes and typographic curly double quotes are detected; single-quoted dialogue, nested dialogue, ambiguous scare quotes, unclosed quotations, long-distance speakers, discourse shifts, paraphrases without explicit reporting cues, polysemy, and cross-sentence target mentions may be unresolved or misleading. Phrase heuristics can produce false positives. Review the original source sentence, document context and genre before treating any association as substantive evidence. For book-length scientific annotation, manually labeled datasets and benchmark evaluation are still required.

**Literature:** Elson & McKeown (2010), *Automatic Attribution of Quoted Speech in Literary Narrative*, https://ojs.aaai.org/index.php/AAAI/article/view/7720 ; Vishnubhotla et al. (2023), *Improving Automatic Quotation Attribution in Literary Novels*, https://aclanthology.org/2023.acl-short.64/ ; Yang & Wang (2024), *Automatic Quote Attribution in Chinese Literary Works*, https://aclanthology.org/2024.sighan-1.1/ . These studies motivate annotation and attribution, but none of their algorithms or trained models has been bundled.

**Next validation:** build human-annotated literary and business samples with quote span, speaker, target, cue position and sentiment gold labels; report precision and recall separately for speaker identification and aspect assignment by type, genre, and document length. Only then consider opt-in pretrained language models to resolve ambiguous speaker identities and target associations.

## Research-informed next features

### P1 — Evidence inspection and calibration (highest priority)
- Extend the implemented evidence register with human review/correction, annotation tags, saved research annotations, passage citation anchors and per-cue provenance audit trails.
- User-created domain lexicons and synonym mappings; versioned imports/exports with escaped strings and no automatic upload.
- More precise negation scope, double negation, negated intensifiers, conditional statements, passive voice and discourse boundaries.
- Human-annotated evaluation corpora across novel excerpts, criticism, service feedback, meeting notes and reports. Report precision/recall by category, stratified by genre and document length, together with disagreements and gaps.
- Contrast windows configurable by paragraph, sentence, fixed word count, normalized passage length and chapter boundaries.

### P2 — Target-aware interpretation
- Literary: distinguish narrated description, character dialogue, reported speech, and the apparent target of positive/negative descriptions. Named characters and pronoun resolution are hypotheses requiring validation.
- Business: target/aspect-based sentiment, linking evaluative words to product features, services or stakeholders (e.g., *great staff, terrible wait time*). Avoid collapsing opposite sentiments to neutral.
- Topic/cue co-occurrence networks and collocates around a selected affective term, supporting metaphorical and semantic-prosody inquiry.
- Temporal change and cross-document divergence plots with sample size and interval counts visible.

### P3 — Optional on-device model layer
- Trial browser-executed, opt-in neural classifiers for emotion, stance, subjectivity and aspect/target associations using Transformers.js and ONNX Runtime Web. Make model name, version, task, domain, size, accuracy caveats and download consent explicit.
- Offer a transparent lexical baseline alongside learned predictions and flag disagreement. Model confidence is not a calibrated probability of author intent.
- Browser CPU/WASM fallback and careful gating of model size, mobile memory and performance. Do not turn Text Lens into a server-side text uploader by default.
- Optional bilingual and multilingual analysis only after language-specific benchmarking; English readability, tokenization and lexicons do not transfer automatically.

### P4 — Corpus ingestion and advanced exploratory analysis
- Improve the existing local PDF/DOCX extraction workflow with explicit page-span provenance, extraction diagnostics and preservation of section/table markers. PDF.js and Mammoth.js are already used by a current optional import widget; do not imply they are absent. OCR is not currently included. Avoid network transfer of source material.
- Corpus-level thematic distribution matrix and group-wise comparisons normalized by document length, with sampling warnings.
- Optional topic modeling or semantic grouping in separately versioned research workflows. BERTopic is a candidate *approach*, not something already running in the current client-side tool.
- Optional export-ready charts, signed source annotations, and CSV of cue occurrences with user consent for inclusion of verbatim excerpts.

## Methodological research and references

1. Hutto, C. J. & Gilbert, E. E. (2014), *VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text.* VADER incorporates negation, booster/dampener expressions, emphasis and contrast. Reference implementation, MIT license: https://github.com/cjhutto/vadersentiment . Text Lens is inspired by the general methodology; it does not bundle VADER's lexicon.
2. Mohammad, S. M. & Turney, P. D., *NRC Word–Emotion Association Lexicon.* Emotion dimensions offer a more informative conceptual vocabulary than positive/negative sentiment alone: https://www.saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm . NRC requires attribution and prohibits redistribution without an appropriate agreement; review https://www.saifmohammad.com/WebPages/AccessResource.htm before considering inclusion.
3. Reagan, A. J. et al. (2016), *The emotional arcs of stories are dominated by six basic shapes*, EPJ Data Science. Motivates normalized progression views and corpus-level caution: https://link.springer.com/article/10.1140/epjds/s13688-016-0093-1 .
4. Vieira Santin, R. & Rezende, S. O. (published online 2025), *Systematic review on aspect-based sentiment analysis in cross-domain*, Artificial Intelligence Review: https://link.springer.com/article/10.1007/s10462-025-11437-x . Motivates distinguishing product aspects and entities from global document sentiment.
5. **quanteda**, keyness and collocations: https://quanteda.io/reference/textstat_keyness.html and https://quanteda.io/reference/textstat_collocations.html . Reference for corpus comparison and association measures.
6. **Voyant Tools**, browser-accessible text exploration and corpus visualizations: https://www.voyant-tools.org/docs/tutorial-start.html . Reference for visual reading workflows and interpretability.
7. **BERTopic**, topic representations, cluster and temporal visualizations: https://maartengr.github.io/BERTopic/getting_started/visualization/visualization.html . Exploratory modeling option, not synonymous with sentiment classification.
8. **Transformers.js**, on-device text classification, named entity recognition and feature extraction via WebGPU or WASM: https://huggingface.co/docs/transformers.js/index . Browser model storage/download disclosures and hardware compatibility are required.
9. **Mammoth.js**, browser raw text extraction from DOCX: https://github.com/mwilliamson/mammoth.js . An ingestion candidate, not presently integrated.

## Research cautions

- Base-rate differences, writing period, genre, quotations, negations, domain and sample length all change apparent signal rates.
- Comparing theme cues per 1,000 words improves length comparability but does not make terms interchangeable or justify causal claims.
- Counts from multiple categories may overlap because a single word can register for more than one theme.
- Word clouds are useful entry points but should not replace counts, source passages or comparative statistics.
- If a reader wants to infer authorial intention, a character's private feelings, a user's satisfaction, or operational performance, Text Lens outputs must remain hypotheses to test against primary evidence.
