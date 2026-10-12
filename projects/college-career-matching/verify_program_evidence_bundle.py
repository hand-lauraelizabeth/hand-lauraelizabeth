#!/usr/bin/env python3
"""Independently verify official-source IPEDS 2025 historical program bundle.

Usage: python verify_program_evidence_bundle.py /path/to/verified-source-bundle.zip
No network, no publishing, no current-program or licensing assertions.
"""
import argparse
import gzip
import hashlib
import json
import re
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(path):
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read('output/programs.manifest.v1.json'))
        assert manifest['data_kind'] == 'IPEDS_2024_25_HISTORICAL_FIRST_MAJOR_COMPLETIONS'
        for gate in ('current_program_offering_verified', 'credential_name_institution_verified',
                     'professional_license_eligibility_verified', 'admissions_and_career_matching_authorized'):
            assert manifest[gate] is False, gate
        for kind, source in (('completions', 'source/C2025_A.zip'),
                             ('cip2020', 'source/CIPCode2020.csv')):
            assert sha(z.read(source)) == manifest['sources'][kind]['sha256'], kind
        titles_entry = manifest['cip2020_titles']
        titles_bytes = z.read('output/' + titles_entry['file'])
        assert sha(titles_bytes) == titles_entry['sha256']
        assert sha(z.read('output/' + titles_entry['file'] + '.gz')) == titles_entry['gzip_sha256']
        titles = json.loads(titles_bytes)
        assert len(titles) == manifest['counts']['distinct_six_digit_cip2020_titles']
        ids = set()
        identities = set()
        n = zero = missing = 0
        gzip_total = raw_total = 0
        for shard in manifest['shards']:
            assert re.fullmatch(r'programs-\d{2}\.json', shard['file'])
            raw = z.read('output/' + shard['file'])
            compressed = z.read('output/' + shard['file'] + '.gz')
            assert len(raw) == shard['bytes'] and len(compressed) == shard['gzip_bytes']
            assert sha(raw) == shard['sha256'] and sha(compressed) == shard['gzip_sha256']
            assert gzip.decompress(compressed) == raw
            assert len(compressed) <= 768000
            raw_total += len(raw)
            gzip_total += len(compressed)
            data = json.loads(raw)
            assert data['schema_version'] == '1.0'
            assert len(data['institutions']) == shard['institutions']
            shard_n = 0
            for uid, rows in data['institutions']:
                assert re.fullmatch(r'\d{6}', uid) and uid not in ids
                ids.add(uid)
                for cip, award, count, status in rows:
                    key = (uid, cip, award)
                    assert key not in identities
                    identities.add(key)
                    assert cip in titles and award in manifest['award_levels']
                    if status == 'reported':
                        assert type(count) is int and count >= 0
                        zero += count == 0
                    else:
                        assert status == 'missing_or_suppressed' and count is None
                        missing += 1
                    shard_n += 1
                    n += 1
            assert shard_n == shard['program_award_records']
        counts = manifest['counts']
        assert len(ids) == counts['institutions_with_historical_program_completions']
        assert n == counts['joined_program_award_records']
        assert len(ids) + counts['national_institutions_without_joined_completions'] == counts['national_institutions']
        return dict(institutions=len(ids), national=counts['national_institutions'], records=n,
                    cip_titles=len(titles), zero_reported=zero, missing_or_suppressed=missing,
                    raw_shard_bytes=raw_total, gzip_shard_bytes=gzip_total,
                    shards=len(manifest['shards']), checksum_errors=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_bundle')
    print(json.dumps(verify(parser.parse_args().source_bundle), indent=2))