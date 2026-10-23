"""Synthetic source-binding and atomic-export regression; no actual service requests."""
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline

HEADERS = ['unique_key','created_date','closed_date','agency','complaint_type','borough','status']

def csv_file(path, key='SYNTHETIC_A'):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer=csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerow([key,'2026-09-10T12:00:00','','DOT','Pothole','Queens','Open'])

class SourceAndAtomicContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.source=self.folder/'source.csv'
        self.output=self.folder/'out.json'
        csv_file(self.source)

    def run_pipeline(self):
        return pipeline.ingest(self.source,self.output,as_of='2026-09-30',min_cell=1)

    def test_exact_snapshot_digest_and_bytes(self):
        original=self.source.read_bytes()
        result=self.run_pipeline()
        self.assertEqual(result['source_sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(result['source_bytes'],len(original))
        self.assertEqual(json.loads(self.output.read_text())['quality']['valid_records'],1)
        self.assertEqual(set(x.name for x in self.folder.iterdir()),{'source.csv','out.json'})

    def test_changed_source_rejected_and_previous_output_preserved(self):
        self.output.write_text('EXISTING_EXPORT')
        actual=csv.DictReader
        def mutate_on_reader(stream, *args, **kwargs):
            # Runs after snapshot hashing; emulate source changing mid-run.
            csv_file(self.source, key='SYNTHETIC_B')
            return actual(stream,*args,**kwargs)
        with patch.object(pipeline.csv,'DictReader',side_effect=mutate_on_reader):
            with self.assertRaisesRegex(ValueError,'Input CSV changed during processing'):
                self.run_pipeline()
        self.assertEqual(self.output.read_text(),'EXISTING_EXPORT')
        self.assertEqual(set(x.name for x in self.folder.iterdir()),{'source.csv','out.json'})

    def test_serialization_failure_is_atomic(self):
        self.output.write_text('EXISTING_EXPORT')
        def fail_mid_write(payload, stream, **kwargs):
            stream.write('{"partial":')
            raise OSError('synthetic serialization failure')
        with patch.object(pipeline.json,'dump',side_effect=fail_mid_write):
            with self.assertRaisesRegex(OSError,'synthetic serialization failure'):
                self.run_pipeline()
        self.assertEqual(self.output.read_text(),'EXISTING_EXPORT')
        self.assertEqual(set(x.name for x in self.folder.iterdir()),{'source.csv','out.json'})

    def test_replace_failure_is_atomic(self):
        self.output.write_text('EXISTING_EXPORT')
        with patch.object(pipeline.os,'replace',side_effect=OSError('synthetic replace failure')):
            with self.assertRaisesRegex(OSError,'synthetic replace failure'):
                self.run_pipeline()
        self.assertEqual(self.output.read_text(),'EXISTING_EXPORT')
        self.assertEqual(set(x.name for x in self.folder.iterdir()),{'source.csv','out.json'})

if __name__=='__main__': unittest.main()
