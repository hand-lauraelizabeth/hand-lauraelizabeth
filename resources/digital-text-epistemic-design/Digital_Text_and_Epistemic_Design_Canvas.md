# Digital Text & Epistemic Design Canvas

A reusable planning and critique resource for digital editions, archives, learning experiences, and other interfaces that mediate evidence.

## Origin and scope

Created in 2026, this resource develops methods explored in a 2019 collaborative Columbia University course project in *Transforming Text: Textual Analysis* into a reusable design canvas.

The 2019 project proposed an interface for the Making and Knowing Project's Digital Critical Edition that used wireframing to foreground material and structural features of manuscript pages, with a possible genetic/time-based view. The documented project team was Gregory Houser, Laura Elizabeth Hand, and Sandra Lehnert. Laura's documented roles included co-presentation; visual/graphic and time-lapse technical knowledge; epistemic design/wireframing; co-program management; and textual insight.

Use this canvas before building an interface, while reviewing an existing one, or when asking what a digital representation enables a reader to know.

## 1. Object and evidence

**Primary object or corpus:**  
**Rights / reuse status:**  
**What survives in the source that users should be able to encounter?**

Evidence types:

- [ ] Text / transcription
- [ ] Images / facsimiles
- [ ] Layout / spatial relationships
- [ ] Marginalia / annotations
- [ ] Material features
- [ ] Revisions / chronology
- [ ] Metadata
- [ ] Uncertainty / competing interpretations
- [ ] Other

**What is lost, flattened, transformed, or newly created when the object becomes digital?**

## 2. Page decomposition and material / structural layer map

Break the source into meaningful regions before deciding what the interface should do.

| Region / layer | Source evidence | Why it matters | Relationship to other regions | Proposed representation |
| --- | --- | --- | --- | --- |
| Text block |  |  |  |  |
| Heading / title |  |  |  |  |
| Margin / side note |  |  |  |  |
| Image / diagram |  |  |  |  |
| Cross-out / revision |  |  |  |  |
| Stain / watermark / binding / paper feature |  |  |  |  |
| Other |  |  |  |  |

**Which divisions are visible in the source itself, and which are analytical divisions introduced by the project?**

## 3. Users, questions, and user stories

**Primary users:**  
**What specialist knowledge should not be assumed?**  
**What do users arrive wanting to know or do?**  
**What questions should the interface make easier to ask—not merely answer?**

Write at least one user story for each major audience:

> As a ______, I want to ______ so that I can ______.

Then test it:

- What evidence must be visible for that task?
- What interaction is actually necessary?
- What could the design accidentally encourage the user to assume?
- What alternate path is needed for accessibility or low-bandwidth use?

## 4. Epistemic design

Every interface makes an argument through selection, hierarchy, categorization, and interaction.

**What does the default view foreground?**  
**What does it hide or make difficult to notice?**  
**What categories does the interface impose on the evidence?**  
**Which categories come from the source, and which are created by the designer?**  
**Could another reasonable categorization produce a different interpretation?**  
**What does the interface treat as the basic unit: page, region, word, object, revision state, annotation, event, or something else?**

## 5. Interaction map

For each important evidence type, define the user's path.

**Evidence / object:**  
**User action:** hover, focus, click, filter, search, compare, zoom, sequence, etc.  
**System response:**  
**Information revealed:**  
**Interpretive value:**  
**Accessibility alternative:**  
**Failure / empty state:**

Repeat as needed.

## 6. Layers, comparison, and genetic views

**Default layer:**  
**Optional analytical layers:**  
**What becomes visible when layers are combined?**  
**Should users be able to turn interpretive layers off?**  
**What should remain visually anchored to the source image or transcription?**

For change over time:

- What evidence supports a sequence or chronology?
- Which steps are observed and which are inferred?
- Could more than one sequence be plausible?
- Would a comparison, slider, stack, animation, or time-lapse clarify the change?
- Can the same evidence be inspected without animation?

## 7. Context of use: location, device, and reading situation

The same interface can produce different reading conditions depending on where and how it is encountered.

**Likely settings:** classroom, archive, home, library, field site, mobile, exhibition, other  
**Likely devices / screen sizes:**  
**Connectivity assumptions:**  
**Input assumptions:** mouse, touch, keyboard, assistive technology, other

Ask:

- What does a large desktop view make possible that a phone view does not?
- Does the design assume access to the physical object, a facsimile, or neither?
- Would being physically near the original object change what the digital layer should do?
- Does the interface require side-by-side comparison that collapses on a small screen?
- What information should remain usable if images fail to load or bandwidth is limited?

## 8. Search, filter, and discovery

**What should be searchable?**  
**What should be filterable?**  
**Which metadata fields support discovery?**  
**What might users search for that the current data model cannot represent?**  
**How will variant terminology, spelling, uncertain metadata, and zero-result searches be handled?**

Consider whether users need to search *within* structural or material categories—for example headings, margins, images, stains, revisions, or page regions—rather than only across transcription text.

## 9. Uncertainty and provenance

**Which claims are observations, metadata, scholarly interpretations, or hypotheses?**  
**How will the interface distinguish them?**  
**What provenance should users be able to inspect?**  
**Where should uncertainty be preserved instead of resolved?**

For each interpretive claim, record where possible:

- source / object identifier;
- page / region;
- transcriber or annotator;
- date and version;
- evidence type;
- confidence or uncertainty note;
- citation / authority;
- revision history.

## 10. Accessibility and inclusion

- [ ] Every interaction works without hover alone.
- [ ] Keyboard path is defined and tested.
- [ ] Images / regions have usable text alternatives.
- [ ] Meaning is not carried by color alone.
- [ ] Contrast is sufficient.
- [ ] Zoom and reflow are supported.
- [ ] Plain-language guidance is available where specialist terms appear.
- [ ] Motion / animation has a non-motion alternative.
- [ ] Low-bandwidth fallback is considered.

**What assumptions about language, ability, disciplinary knowledge, hardware, or bandwidth are embedded in the design?**

## 11. Data and technical model

**Minimum fields required:**  
**Relationships among objects:**  
**Stable identifiers needed:**  
**Structured vs. free-text fields:**  
**Version / history requirements:**  
**What must be validated before publication?**

Check whether the data model can represent:

- one source region linked to multiple interpretations;
- one interpretation linked to multiple evidence types;
- uncertainty or competing readings;
- revisions over time;
- relationships among page regions;
- display order that differs from source order without erasing the source order.

## 12. QA and testing

### Content QA

- [ ] Source fidelity checked
- [ ] Citations / provenance checked
- [ ] Missing values reviewed
- [ ] Terminology consistent
- [ ] Source observation is distinguished from interpretation

### Interaction QA

- [ ] Primary paths tested
- [ ] Keyboard path tested
- [ ] Responsive behavior tested
- [ ] Empty / error states tested
- [ ] Touch and non-hover behavior tested where relevant

### Interpretive QA

- [ ] Default view does not imply unsupported certainty
- [ ] Labels distinguish source evidence from interpretation
- [ ] Alternative readings remain possible where appropriate
- [ ] Interface categories have documented rationale

**User-testing question:** What did users notice because of the interface that they might otherwise have missed?

## 13. Minimum viable prototype

**One user:**  
**One source / object:**  
**One core question:**  
**One interaction:**  
**One interpretive payoff:**  
**One accessibility path:**  

**What can be tested before building the full system?**

## 14. Design decision log

**Decision:**  
**Evidence / reason:**  
**Alternative considered:**  
**Tradeoff:**  
**Validation needed:**  
**Date / version:**

## 15. Reflection

**What argument does this interface make about its object?**  
**What forms of reading does it encourage?**  
**What forms of reading might it discourage?**  
**What becomes legible only because of the interface?**  
**What becomes less legible because of it?**  
**If the interface disappeared and only its data model remained, what assumptions would still be encoded?**

## Portfolio / teaching extension

For a course or portfolio project, document:

- problem and audience;
- source / corpus and rights status;
- research / design question;
- page or object decomposition;
- user stories;
- data model;
- wireframe or prototype;
- accessibility decisions;
- context-of-use decisions;
- QA / testing method;
- findings from user testing;
- limitations;
- revision history;
- what was individually created versus collaborative.

A useful extension would be a small prototype using a public-domain manuscript or openly licensed archival object, clearly distinguishing the historical project from newly authored code and design work.

## About this resource

This canvas extends Laura Elizabeth Hand's documented 2019 collaborative work into a reusable teaching and design tool. The 2019 work centered on research, wireframing, interface concepts, presentation, and epistemic design; the canvas broadens those methods for other digital-text and evidence-interface projects.
