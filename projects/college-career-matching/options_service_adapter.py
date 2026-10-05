#!/usr/bin/env python3
"""Service wrapper for current-data interface options and constraint capabilities."""
from __future__ import annotations
from interface_options_builder import build as build_options
from constraint_field_registry import public_registry
def options(snapshot,data_version):
 o=build_options(snapshot,data_version)
 return {"schema_version":"1.0","data_version":data_version,"options":o,"constraint_capabilities":public_registry(),"semantic_rules":{"options_source":"active product snapshot","unknown_evidence":"unknown is not false or zero","browser_role":"render choices; do not invent constraint fields or operators"}}
