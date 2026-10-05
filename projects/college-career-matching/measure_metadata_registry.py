#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
PATH=Path(__file__).parent/'config'/'measure_metadata_registry.v1.json'
def load_registry(path=PATH):
 r=json.loads(Path(path).read_text(encoding='utf-8'));states=set(r.get('evidence_states',[]))
 if not states or not r.get('measures'):raise ValueError('measure registry is incomplete')
 return r
def evidence_state(measure,row,registry=None):
 r=registry or load_registry();states=set(r['evidence_states'])
 if measure not in r['measures']:raise ValueError(f'unregistered measure: {measure}')
 raw=row.get(f'{measure}__state')
 if raw is not None and str(raw).strip():
  s=str(raw).strip().lower()
  if s not in states:raise ValueError(f'invalid evidence state for {measure}: {s}')
  return s
 v=row.get(measure)
 return 'missing' if v is None or str(v).strip()=='' else 'observed'
def public_measure(measure,registry=None):
 r=registry or load_registry();return {'measure_id':measure,**r['measures'][measure]}
