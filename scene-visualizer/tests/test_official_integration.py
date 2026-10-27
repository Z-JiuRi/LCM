import gzip
import json
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from lcm_scene.paths import city_directory


class OfficialIntegrationTests(unittest.TestCase):
    def test_three_resource_versions_preserve_layout_and_face_materials(self):
        for size in [1000,2000,4000]:
            path=ROOT/f'data/scenes/official-cities/city-{size//1000}km/assembled-city.scene.json.gz'
            if not path.exists():self.skipTest('Official resource integration not executed')
            old=json.loads(gzip.decompress((city_directory(size)/'assembled-city.scene.json.gz').read_bytes()))
            new=json.loads(gzip.decompress(path.read_bytes()))
            self.assertEqual(old['instances'],new['instances'])
            for key in ['roads','parks','parcels','green_path']:
                self.assertEqual(old[key],new[key])
            self.assertEqual(len(old['assets']),len(new['assets']))
            for previous,asset in zip(old['assets'],new['assets']):
                self.assertEqual(asset['source_object_index'],asset['official_object_index'])
                self.assertEqual(asset['geometry_provenance'],'official-archive-matched')
                self.assertEqual(len(asset['faces']),len(asset['face_material_keys']))
                self.assertLess(asset['official_match_error_m'],.002)
                for a,b in zip(asset['faces'],previous['faces']):np.testing.assert_allclose(a,b,rtol=0,atol=.002)
                for key in asset['face_material_keys']:self.assertIn(key,new['materials'])
            self.assertEqual(new['manifest']['resource_kind'],'official-integrated')
            self.assertTrue(all('conductivity' in m and 'permittivity' in m for m in new['materials'].values()))


if __name__=='__main__':unittest.main()
