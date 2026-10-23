"""Private, fail-closed NYC 311 release preflight. Never authorizes publication.

Use only synthetic or independently cleared marginal evidence. The output
contains redacted risk codes, never record-level data, marginal values or labels.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path
from release_disclosure_audit import audit_single, audit_pair
from marginal_reconstruction_audit import audit_marginals
from integer_feasibility_audit import audit_integer_feasibility

EVIDENCE_FIELDS = {'coefficients', 'totals', 'suppressed', 'sensitive_groups'}


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


def _read_strict_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=_reject_duplicate_keys,
                      parse_constant=_reject_nonfinite)


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
    parser.add_argument('--report', required=True)
    a = parser.parse_args(argv)
    sources = [p for p in (a.candidate_json, a.previous_json,
                           a.marginal_evidence_json) if p is not None]
    if any(_aliases_source(a.report, source) for source in sources):
        print('HOLD: report destination aliases a source; source preserved')
        return 2
    try:
        candidate = _read_strict_json(a.candidate_json)
        previous = _read_strict_json(a.previous_json) if a.previous_json else None
        evidence = (_read_strict_json(a.marginal_evidence_json)
                    if a.marginal_evidence_json else None)
        result = audit_release(candidate, previous=previous, evidence=evidence)
    except (OSError, UnicodeError, ValueError, TypeError):
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
