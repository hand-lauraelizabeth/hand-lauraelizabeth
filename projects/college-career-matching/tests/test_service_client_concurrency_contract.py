#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
JS=(P/"prototype/service-client.js").read_text(encoding="utf-8")

class ServiceClientConcurrencyContractTests(unittest.TestCase):
 def test_match_propagates_abort_signal_to_fetch(self):
  self.assertIn("signal=null",JS)
  self.assertIn("body:body?JSON.stringify(body):null,signal",JS)
  self.assertIn("match(request,{signal=null}={})",JS)
  self.assertIn("body:request,signal",JS)

if __name__=="__main__":unittest.main()
