"""Fail-closed QA for captured public NYC 311 monthly aggregate evidence.

Checks source-query contracts and internal totals; does not fetch raw records
or establish a raw CSV checksum. Never commit request-level data.
"""
import calendar
from datetime import date
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

DATASET = 'erm2-nwe9'
ENDPOINT = 'https://data.cityofnewyork.us/resource/erm2-nwe9.json'


def validate(snapshot):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(isinstance(snapshot, dict), 'JSON object required')
    require(snapshot.get('dataset_id') == DATASET, 'wrong dataset')
    month = snapshot.get('month', '')
    require(isinstance(month, str) and len(month) == 7 and month[4] == '-', 'invalid month')
    try:
        year, number = map(int, month.split('-'))
        start = date(year, number, 1)
        stop = date(year + (number == 12), number % 12 + 1, 1)
        observation = date.fromisoformat(snapshot['rechecked_date'])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError('invalid dates') from exc
    require(start <= observation, 'observation precedes reporting month')
    where = (f"created_date >= '{start.isoformat()}T00:00:00' "
             f"and created_date < '{stop.isoformat()}T00:00:00'")
    contracts = [
        {'$select': 'count(*) as total,count(distinct unique_key) as distinct_ids', '$where': where},
        {'$select': 'borough,count(*) as n', '$where': where, '$group': 'borough', '$order': 'n desc'},
        {'$select': 'date_trunc_ymd(created_date) as day,count(*) as n', '$where': where,
         '$group': 'date_trunc_ymd(created_date)', '$order': 'day asc', '$limit': '40'},
        {'$select': 'complaint_type,count(*) as n', '$where': where, '$group': 'complaint_type',
         '$order': 'n desc', '$limit': '12'},
    ]
    queries = snapshot.get('queries')
    require(isinstance(queries, list) and len(queries) == 4, 'four queries required')
    for item, expected in zip(queries, contracts):
        require(isinstance(item, dict), 'invalid query')
        parsed = urlsplit(item.get('url', ''))
        require(parsed.scheme == 'https' and parsed.hostname == 'data.cityofnewyork.us'
                and parsed.path == '/resource/erm2-nwe9.json' and parsed.port is None
                and not parsed.username and not parsed.password and not parsed.fragment,
                'not official HTTPS endpoint')
        require(parse_qs(parsed.query, strict_parsing=True) == {k: [v] for k, v in expected.items()},
                'query contract mismatch')
        require(item.get('params') == expected, 'query/params mismatch')
    results = snapshot.get('results', {})
    total = results.get('total')
    require(type(total) is int and total >= 0, 'invalid count')
    require(type(results.get('distinct_ids')) is int and results['distinct_ids'] == total,
            'duplicate or missing identifiers')
    boroughs = results.get('borough_counts')
    require(isinstance(boroughs, dict) and boroughs and
            all(type(v) is int and v >= 0 for v in boroughs.values()) and
            sum(boroughs.values()) == total, 'borough reconciliation failed')
    days = results.get('daily_counts')
    require(isinstance(days, list) and len(days) == calendar.monthrange(year, number)[1],
            'incomplete daily series')
    require([r.get('day') for r in days] ==
            [date(year, number, i).isoformat() for i in range(1, len(days) + 1)],
            'daily date coverage')
    require(all(type(r.get('requests')) is int and r['requests'] >= 0 for r in days)
            and sum(r['requests'] for r in days) == total, 'daily totals mismatch')
    top = results.get('top_complaint_types')
    require(isinstance(top, list) and len(top) == 12, 'top-12 required')
    labels = [r.get('complaint_type') for r in top]
    counts = [r.get('requests') for r in top]
    require(all(isinstance(label, str) and label for label in labels) and
            len(set(labels)) == 12 and all(type(n) is int and n >= 0 for n in counts) and
            counts == sorted(counts, reverse=True), 'invalid complaint ranking')
    other = results.get('other_complaint_types_requests')
    require(type(other) is int and other >= 0 and sum(counts) + other == total,
            'complaint totals mismatch')
    return {'dataset_id': DATASET, 'month': month, 'observation': observation.isoformat(),
            'requests': total, 'distinct_ids': results['distinct_ids'],
            'days': len(days), 'top12_requests': sum(counts), 'other_requests': other,
            'raw_record_reconciled': False}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence_json')
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.evidence_json).read_text())), sort_keys=True))
