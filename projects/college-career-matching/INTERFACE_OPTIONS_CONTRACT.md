# Interface Options Contract

The interactive matcher must derive selectable college/program choices from the same approved data snapshot used by matching. The frontend must not maintain a separate hand-curated institution, program, credential, state, CIP, or modality universe.

`interface_options_builder.py` consumes an institution × program snapshot and produces a versioned options artifact suitable for `GET /options`.

## Required snapshot identity

Each row represents one authoritative candidate program identity and requires `UNITID`, `institution_name`, `program_id`, `program_name`, `cip_code`, `credential_level`, and `state`. `(UNITID, program_id)` must be unique. Optional `city`, `cip_title`, and `online_available` fields enrich the interface when the approved snapshot supports them.

## Output

The artifact contains `data_version`, generation timestamp, coverage counts, and controlled collections for states, credential levels, institutions, institution-program choices, CIP fields, and supported modality evidence.

Program option values are namespaced by institution (`UNITID:program_id`) so identically named programs at different institutions cannot collapse into one UI choice.

## Freshness and consistency

`GET /options` and `POST /match` should use the same active `data_version`. A UI session may display its data version and should refresh options when the active version changes. A request that pins an unavailable or retired data version should fail explicitly rather than silently switching universes.

## Coverage behavior

A choice is offered only when supported by the active snapshot. Absence from an optional option family does not imply a negative fact about an institution or program. For example, lack of online/modality evidence must not be rendered as “in-person only.”

## Academic-field choices

Academic-field choices are emitted as `cip_fields` from the active institution×program snapshot. The submitted value is the authoritative `cip_code`; the human-readable label is the snapshot's CIP title when available.

The browser must not infer CIP from program-title similarity. Broad interest clusters such as “technology” or “health” require their own governed taxonomy/crosswalk before they can be offered as matcher semantics. Until then, exact CIP choices are preferable to a friendly-looking but undocumented browser mapping.

## Search and accessibility

Large collections such as institutions and programs should be searchable/autocomplete controls rather than enormous select menus. Labels must remain human-readable while stable IDs are submitted. Keyboard navigation, visible focus, descriptive labels, and screen-reader semantics are product requirements, not post-launch enhancements.

## Next integration

Connect the approved current-data/model-ready build to this options builder, add snapshot-level QA for counts/identity/freshness, then expose the artifact through the service boundary. The same versioned snapshot should feed both option discovery and matching candidates.
