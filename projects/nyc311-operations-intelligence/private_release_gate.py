"""Private, fail-closed NYC 311 release preflight. Never authorizes publication.

Use only synthetic or independently cleared marginal evidence. The output
contains redacted risk codes, never record-level data, marginal values or labels.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import math
from decimal import Decimal
import os
import tempfile
from pathlib import Path
from release_disclosure_audit import audit_single, audit_pair
from marginal_reconstruction_audit import audit_marginals
from integer_feasibility_audit import audit_integer_feasibility
from source_unique_key_audit import audit_unique_keys

EVIDENCE_FIELDS = {'coefficients', 'totals', 'suppressed', 'sensitive_groups'}
# Aggregate snapshots and cleared marginal evidence should remain compact. Bound
# reads before UTF-8 decoding or JSON parsing to prevent memory exhaustion.
MAX_INPUT_BYTES = 16 * 1024 * 1024
# Bound untrusted CSV snapshots independently of the candidate's self-reported
# source_bytes. A larger authentic export requires an explicit reviewed change.
MAX_SOURCE_BYTES = 1024 * 1024 * 1024


def _codes(result):
    if (type(result) is not dict or result.get('status') != 'HOLD' or
            result.get('manual_review_required') is not True or
            type(result.get('codes')) is not list or
            any(type(code) is not str or not code.isascii() or not code or
                len(code) > 100 or
                not all(c.isupper() or c.isdigit() or c == '_' for c in code)
                for code in result['codes'])):
        return ['INVALID_AUDIT_RESPONSE']
    return sorted(set(result['codes']))


def audit_release(candidate, *, previous=None, evidence=None):
    """Invoke temporal, linear and integer screens; return unconditional HOLD."""
    codes = {'INDEPENDENT_PRIVACY_AND_SOURCE_REVIEW_REQUIRED'}
    try:
        result = audit_pair(previous, candidate) if previous is not None else audit_single(candidate)
        codes.update(_codes(result))
        if result.get('structural_valid') is False:
            codes.add('INVALID_AGGREGATE_CONTRACT')
    except Exception:
        codes.add('AGGREGATE_AUDIT_FAILED_CLOSED')
    if evidence is None:
        codes.update(('MARGINAL_EVIDENCE_NOT_SUPPLIED', 'INTEGER_EVIDENCE_NOT_SUPPLIED'))
    elif (type(evidence) is not dict or set(evidence) - EVIDENCE_FIELDS or
          not {'coefficients', 'totals', 'suppressed'} <= set(evidence)):
        codes.add('INVALID_MARGINAL_EVIDENCE_CONTRACT')
    else:
        args = (evidence['coefficients'], evidence['totals'], evidence['suppressed'])
        kwargs = {'sensitive_groups': evidence.get('sensitive_groups')}
        for screen, failure in ((audit_marginals, 'MARGINAL_AUDIT_FAILED_CLOSED'),
                                (audit_integer_feasibility, 'INTEGER_AUDIT_FAILED_CLOSED')):
            try:
                codes.update(_codes(screen(*args, **kwargs)))
            except Exception:
                codes.add(failure)
    return {'status': 'HOLD', 'manual_review_required': True,
            'release_authorized': False, 'codes': sorted(codes)}


def _reject_duplicate_keys(pairs):
    """Reject ambiguous JSON objects, including duplicates in nested evidence."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _reject_nonfinite(_value):
    """Python's permissive JSON decoder otherwise accepts NaN/Infinity."""
    raise ValueError('nonfinite JSON number')


def _parse_finite_float(token):
    """Reject valid-JSON exponents that overflow Python floats to infinity."""
    number = float(token)
    if not math.isfinite(number):
        raise ValueError('out-of-range JSON number')
    # A nonzero JSON quantity rounded to 0.0 would silently erase evidence.
    # Decimal is consulted only at the zero boundary, so legitimate 0e-9999
    # remains valid while nonzero subnormal underflow fails closed.
    if number == 0.0 and not Decimal(token).is_zero():
        raise ValueError('underflowing JSON number')
    return number


def _read_strict_json(path):
    # Read at most one byte beyond the limit; never allocate based on file size.
    # Byte counting (rather than character counting) also covers UTF-8 input.
    with Path(path).open('rb') as stream:
        payload = stream.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError('oversized JSON input')
    return json.loads(payload.decode('utf-8'),
                      object_pairs_hook=_reject_duplicate_keys,
                      parse_constant=_reject_nonfinite,
                      parse_float=_parse_finite_float)


def _source_binding_codes(candidate, csv_path, *, snapshot_path=None):
    """Compare bytes with the candidate's claim; never attest official origin."""
    if csv_path is None:
        return ['SOURCE_CSV_NOT_SUPPLIED']
    if (type(candidate) is not dict or
            type(candidate.get('source_bytes')) is not int or
            candidate['source_bytes'] < 1 or
            type(candidate.get('source_sha256')) is not str or
            len(candidate['source_sha256']) != 64 or
            any(c not in '0123456789abcdef' for c in candidate['source_sha256'])):
        return ['SOURCE_CSV_BINDING_FAILED']
    if candidate['source_bytes'] > MAX_SOURCE_BYTES:
        return ['SOURCE_CSV_SIZE_LIMIT_EXCEEDED']
    digest = hashlib.sha256()
    size = 0
    try:
        # Snapshot the exact bytes being hashed. Auditing the original path
        # later would permit a changed file to be validated against an old hash.
        with ExitStack() as stack:
            source = stack.enter_context(Path(csv_path).open('rb'))
            snapshot = (stack.enter_context(Path(snapshot_path).open('xb'))
                        if snapshot_path is not None else None)
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                # Never copy or hash beyond the cap, even when a candidate
                # understates its size or the source grows while being read.
                if size > MAX_SOURCE_BYTES:
                    return ['SOURCE_CSV_SIZE_LIMIT_EXCEEDED']
                digest.update(chunk)
                if snapshot is not None:
                    snapshot.write(chunk)
    except (OSError, ValueError):
        return ['SOURCE_CSV_READ_FAILED_CLOSED']
    if size != candidate['source_bytes'] or digest.hexdigest() != candidate['source_sha256']:
        return ['SOURCE_CSV_BINDING_FAILED']
    # Equality to a self-reported digest is NOT authentication of the origin,
    # time window, unique_key grain or official export parameters.
    return ['SOURCE_CSV_BYTES_MATCH_CANDIDATE_CLAIM',
            'SOURCE_ORIGIN_NOT_AUTHENTICATED']


def _aliases_source(report, source):
    """Prevent an output report from replacing any input, even via aliases."""
    output, original = Path(report), Path(source)
    if output.resolve() == original.resolve():
        return True
    try:
        return output.samefile(original)
    except (OSError, ValueError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate_json')
    parser.add_argument('--previous-json')
    parser.add_argument('--marginal-evidence-json', help='synthetic or cleared evidence only')
    parser.add_argument('--source-csv', help='private source CSV to stream-hash; origin still unverified')
    parser.add_argument('--created-month', help='expected source-local YYYY-MM; floating timestamp, no timezone inference')
    parser.add_argument('--report', required=True)
    a = parser.parse_args(argv)
    sources = [p for p in (a.candidate_json, a.previous_json,
                           a.marginal_evidence_json, a.source_csv) if p is not None]
    if any(_aliases_source(a.report, source) for source in sources):
        print('HOLD: report destination aliases a source; source preserved')
        return 2
    try:
        candidate = _read_strict_json(a.candidate_json)
        previous = _read_strict_json(a.previous_json) if a.previous_json else None
        evidence = (_read_strict_json(a.marginal_evidence_json)
                    if a.marginal_evidence_json else None)
        result = audit_release(candidate, previous=previous, evidence=evidence)
        # Hash and audit one private, automatically removed byte snapshot.
        # This closes the gap between hashing the input and reopening it for
        # unique_key/month checks; it does NOT authenticate publisher origin.
        with tempfile.TemporaryDirectory(prefix='nyc311_source_snapshot_') as snapshot_dir:
            snapshot = Path(snapshot_dir) / 'source.csv'
            binding = _source_binding_codes(candidate, a.source_csv,
                                            snapshot_path=snapshot)
            codes = set(result['codes']) | set(binding)
            if 'SOURCE_CSV_BYTES_MATCH_CANDIDATE_CLAIM' in binding:
                if a.created_month is None:
                    codes.add('SOURCE_CREATED_DATE_MONTH_NOT_BOUND')
                expected_rows = candidate.get('source_rows') if type(candidate) is dict else None
                codes.update(audit_unique_keys(snapshot, expected_rows=expected_rows,
                                               expected_month=a.created_month))
            result['codes'] = sorted(codes)
    except (OSError, UnicodeError, ValueError, TypeError,
            RecursionError, ArithmeticError):
        result = {'status': 'HOLD', 'manual_review_required': True,
                  'release_authorized': False, 'codes': ['INPUT_READ_OR_PARSE_FAILED_CLOSED']}
    target = Path(a.report)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='.nyc311_gate_', suffix='.tmp', delete=False) as out:
            temporary = Path(out.name)
            json.dump(result, out, indent=2, sort_keys=True)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print('HOLD: independent source, disclosure and accessibility review required')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
