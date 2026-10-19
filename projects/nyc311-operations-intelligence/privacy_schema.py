"""Fail-closed field allowlists for private NYC 311 aggregate payloads.

Unknown fields are rejected, not forwarded, to prevent a future pipeline
change from silently including raw service-request data in viewer JSON.
This does not establish comprehensive disclosure safety.
"""

INPUT_FIELDS = frozenset({
    'source', 'dataset_id', 'snapshot_as_of', 'source_sha256', 'source_bytes',
    'publication_authorized', 'rules', 'quality', 'aggregates',
})
RULE_FIELDS = frozenset({
    'grain', 'display_minimum_cell_count', 'test_only_threshold', 'closure',
    'closure_suppression', 'privacy', 'limitations',
})
DETAIL_FIELDS = frozenset({
    'month', 'borough', 'agency', 'problem', 'requests',
    'closed_with_valid_interval', 'closure_count_suppressed',
})


def assert_approved_payload_fields(payload):
    if not isinstance(payload, dict) or set(payload) - INPUT_FIELDS:
        raise ValueError('Unapproved aggregate payload fields')
    rules = payload.get('rules')
    if not isinstance(rules, dict) or set(rules) - RULE_FIELDS:
        raise ValueError('Unapproved aggregate rule fields')
    rows = payload.get('aggregates')
    if not isinstance(rows, list):
        raise ValueError('Missing aggregate list')
    if any(not isinstance(row, dict) or set(row) - DETAIL_FIELDS for row in rows):
        raise ValueError('Unapproved aggregate detail fields')
    assert_approved_payload_values(payload)

# Value-shape validation is separate from field-name validation. Without it,
# a new upstream version could place nested raw records under an approved key.
_TEXT_METADATA = frozenset({'source', 'dataset_id', 'snapshot_as_of', 'source_sha256'})
_TEXT_RULES = frozenset({'grain', 'closure', 'closure_suppression', 'privacy', 'limitations'})
_TEXT_DETAIL = frozenset({'month', 'borough', 'agency', 'problem'})


def assert_approved_payload_values(payload):
    for key in _TEXT_METADATA & payload.keys():
        value = payload[key]
        if type(value) is not str or len(value) > 512:
            raise ValueError('Invalid aggregate metadata value')
    if 'source_bytes' in payload and (type(payload['source_bytes']) is not int or payload['source_bytes'] < 0):
        raise ValueError('Invalid source byte count')
    if 'publication_authorized' in payload and payload['publication_authorized'] is not False:
        raise ValueError('Private aggregate must not authorize publication')
    quality = payload.get('quality')
    if quality is not None and (not isinstance(quality, dict) or
        any(type(v) is not int or v < 0 for v in quality.values())):
        raise ValueError('Invalid aggregate quality counters')
    rules = payload['rules']
    for key in _TEXT_RULES & rules.keys():
        if type(rules[key]) is not str or len(rules[key]) > 1000:
            raise ValueError('Invalid aggregate rule text')
    if 'display_minimum_cell_count' in rules and (type(rules['display_minimum_cell_count']) is not int or rules['display_minimum_cell_count'] < 10):
        raise ValueError('Invalid aggregate disclosure threshold')
    if 'test_only_threshold' in rules and type(rules['test_only_threshold']) is not bool:
        raise ValueError('Invalid aggregate test threshold flag')
    for row in payload['aggregates']:
        for key in _TEXT_DETAIL & row.keys():
            if type(row[key]) is not str or len(row[key]) > 160:
                raise ValueError('Invalid aggregate detail text')
        for key in ('requests', 'closed_with_valid_interval'):
            if key in row and row[key] is not None and (type(row[key]) is not int or row[key] < 0):
                raise ValueError('Invalid aggregate detail count')
        if 'closure_count_suppressed' in row and type(row['closure_count_suppressed']) is not bool:
            raise ValueError('Invalid aggregate suppression flag')
