"""Private applicant input validation; never predicts admission outcomes."""
from __future__ import annotations

GPA_SCALES = ('4.0', 'other')
TEST_POLICIES = ('required', 'optional', 'blind', 'unknown')
ENROLLMENT_DEFINITIONS = ('undergraduate', 'total')

def validate_gpa_scale(scale):
    if scale not in GPA_SCALES:
        raise ValueError('Unsupported GPA scale')
    return scale
