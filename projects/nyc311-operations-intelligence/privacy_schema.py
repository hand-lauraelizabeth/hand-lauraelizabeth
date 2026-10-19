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
