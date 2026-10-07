import unittest,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
from suny_step_live_snapshot import parse

class SunyStepLiveSnapshotTest(unittest.TestCase):
    def test_parse_visible_table(self):
        html='''<table><tr><th>ID</th><th>Initial Campus</th><th>Partner Campus</th><th>Type</th><th>Program</th><th>Destination</th><th>Source</th></tr>
        <tr><td>R284</td><td>Adirondack</td><td>Canton</td><td>Articulation Agreement</td><td>Business Administration A.S.</td><td>Technology Management B.B.A.</td><td>Business Administration A.S.</td></tr></table>'''
        rows=parse(html)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["Initial Campus"],"Adirondack")
        self.assertEqual(rows[0]["Partner Campus"],"Canton")
        self.assertEqual(rows[0]["Destination"],"Technology Management B.B.A.")

if __name__=="__main__":unittest.main()
