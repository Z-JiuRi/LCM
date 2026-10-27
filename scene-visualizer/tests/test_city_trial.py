import json
import sys
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from lcm_scene.verification.city_trial import triangulate


class CityTrialTests(unittest.TestCase):
    def test_triangulation_preserves_vertices_and_removes_bottom(self):
        faces=[[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],
               [[0,0,2],[1,0,2],[1,1,2],[0,1,2]]]
        vertices,triangles,stats,deviation=triangulate(faces)
        self.assertEqual(len(triangles),2)
        self.assertTrue(np.all(vertices[:,2]==2))
        self.assertEqual(stats['ground_coplanar_bottom_faces_omitted'],1)
        self.assertEqual(deviation,0)

    def test_saved_trial_if_present(self):
        folder=ROOT/'generated/rt/city-1km-trial-final'
        if not (folder/'samples.npz').exists():
            self.skipTest('Sparse RT trial not executed on this machine')
        with np.load(folder/'samples.npz',allow_pickle=False) as data:
            h=data['csi']
            self.assertEqual(h.shape,(32,1,1,8,1,64))
            self.assertTrue(np.iscomplexobj(h))
            self.assertTrue(np.isfinite(h).all())
            active=data['channel_valid']
            self.assertTrue(np.all(data['best_beams'][~active]==-1))
            self.assertTrue(np.all(h[~active]==0))
            self.assertEqual(data['frequency_offsets_hz'][0],-1e7)
            self.assertEqual(data['carrier_frequency_hz'],3.5e9)
            np.testing.assert_allclose(data['mean_channel_gain'],np.mean(np.abs(h)**2,axis=(1,2,3,4,5)))
        report=json.loads((folder/'results.json').read_text())
        self.assertEqual(report['geometry']['building_instances'],665)
        self.assertLess(report['cir_to_csi_relative_reconstruction_error'],1e-4)


if __name__=='__main__':
    unittest.main()
