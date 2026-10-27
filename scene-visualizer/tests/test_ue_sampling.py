"""UE grid/display consistency; no RT imports or executions."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'scripts'))
from city_geometry import build_ue_grid


class UESamplingTests(unittest.TestCase):
    def test_vectorized_grid_matches_union_distance(self):
        scene=dict(assets=[dict(id='a',footprint={'outer':[[0,0],[3,0],[3,3],[0,3]]})],
                   instances=[dict(asset='a',position_m=[2.5,2.5,0],rotation_z_deg=0)],environment={})
        polygon=Polygon([[2.5,2.5],[5.5,2.5],[5.5,5.5],[2.5,5.5]])
        for clearance in (0.,1.,2.):
            positions,_=build_ue_grid(scene,1.,1.5,clearance,0.,(0,0,10,10))
            expected=[]
            for y in np.arange(.5,10,1):
                for x in np.arange(.5,10,1):
                    p=Point(x,y)
                    if not polygon.covers(p) and polygon.distance(p)>=clearance:expected.append([x,y,1.5])
            np.testing.assert_array_equal(positions,expected)

    def test_saved_candidates_and_browser_binary(self):
        catalog=json.loads((ROOT/'web/public/scenes/catalog.json').read_text())
        entries={entry['id']:entry for entry in catalog}
        for km,count in [(1,29726),(2,114688),(4,449988)]:
            with self.subTest(km=km):
                entry=entries[f'city-{km}km']['ue_sampling']
                positions=np.load(ROOT/f'data/scenes/ue-candidates/city-{km}km/ue_candidates.npy',allow_pickle=False)
                binary=(ROOT/'web/public'/entry['positions_url'].lstrip('/')).read_bytes()
                np.testing.assert_array_equal(np.frombuffer(binary,dtype='<f4').reshape(-1,3),positions)
                self.assertEqual(len(positions),count)
                self.assertEqual(hashlib.sha256(binary).hexdigest(),entry['positions_sha256'])
                source=ROOT/f'data/scenes/environment-cities/city-{km}km/assembled-city.scene.json.gz'
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),entry['source_scene_sha256'])
                self.assertTrue(np.all(positions[:,2]==1.5))
                np.testing.assert_array_equal(positions[:,:2]%5,2.5*np.ones((count,2)))
                self.assertTrue((positions[:,:2]>0).all() and (positions[:,:2]<km*1000).all())

if __name__=='__main__':unittest.main()
