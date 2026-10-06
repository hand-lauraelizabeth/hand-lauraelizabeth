# Labor-Market Product Contract

The matching product must keep **current/local labor evidence** separate from **long-term occupational outlook**. They answer different questions and may use different geographies, vintages, and measures.

## Current/local evidence

Current labor evidence is keyed by SOC plus an explicit `market_id` and `market_type`. Examples may include an OEWS metropolitan/nonmetropolitan area or another governed labor-market geography. Employment and wage evidence retain independent evidence states so suppression/missingness is not interpreted as zero.

A user's intended work market is independent of the school's location. The product must not substitute institution-local geography when the user explicitly selects a different intended work market. Institution-local labor evidence may be shown as a separate contextual scenario.

No state or national fallback should silently replace missing local evidence. A fallback, if ever offered, must be explicit and labeled as a different geography.

## Interactive market selection

When the service exposes user-selectable labor markets, the choices must be derived from the governed current-labor evidence actually loaded by that service. A submitted `selected_market` request requires both `market_id` and `market_type`, and the service must reject an identity outside its active market universe rather than fuzzy-matching a place name or silently falling back to another geography.

The public career-first interface may collect current-market and long-term-outlook priorities separately. O*NET work-characteristic preferences remain a distinct alignment layer and must not be activated until their attribute/operator mappings have completed the review required by the career-preference contract.

## Long-term outlook

Long-term projection evidence is keyed by SOC and preserves its projection geography, base year, projection year, employment change, annual openings, and source vintage. National BLS projections are not evidence about current hiring in a selected local market.

## Program-to-career expansion

`labor_market_product_bridge.py` reaches labor evidence only through governed candidate→SOC pathways. A program may therefore produce multiple SOC×market rows and multiple SOC projection rows. The bridge does not average those occupations into one opaque score.

## Product presentation

The eventual result should be able to say, separately:

- what current employment/pay evidence exists in the user's selected work market;
- what current evidence exists around the institution, if requested;
- what the long-term occupational projection indicates;
- which SOC pathway(s) each statement describes;
- when evidence is missing or suppressed.

Recommendation dimensions may summarize these signals later, but the underlying evidence and horizon/geography distinctions must remain inspectable.
