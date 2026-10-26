import gzip
import json
from pathlib import Path
import unittest
import numpy as np
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]


class EnvironmentTests(unittest.TestCase):
    def test_environment_partition_and_plant_clearance(self):
        for km in (1,2,4):
            folder=ROOT/f'data/scenes/environment-cities/city-{km}km'
            if not (folder/'assembled-city.scene.json.gz').exists():self.skipTest('Environment variant not built')
            env=json.loads(gzip.decompress((folder/'assembled-city.scene.json.gz').read_bytes()))
            base=json.loads(gzip.decompress((ROOT/f'data/scenes/official-cities/city-{km}km/assembled-city.scene.json.gz').read_bytes()))
            self.assertEqual(env['instances'],base['instances']);self.assertEqual(env['assets'],base['assets'])
            e=env['environment'];t=e['terrain'];v=np.asarray(t['vertices']);tri=np.asarray(t['triangles'])
            self.assertTrue(np.isfinite(v).all());self.assertTrue(np.all(v[:,2]==0))
            self.assertEqual(len(tri),len(t['triangle_material_keys']))
            self.assertEqual(len(tri),len(t['triangle_roles']))
            shapes=[Polygon(v[f,:2]) for f in tri]
            self.assertAlmostEqual(sum(p.area for p in shapes),(km*1000)**2,places=2)
            self.assertAlmostEqual(unary_union(shapes).area,(km*1000)**2,places=2)
            for key in t['triangle_material_keys']:self.assertIn(key,env['materials'])
            assets={a['id']:a for a in e['vegetation_assets']}
            for i in e['vegetation_instances']:
                self.assertIn(i['asset'],assets);self.assertFalse(i['rt_enabled'])
                self.assertEqual(i['position_m'][2],0)
            summary=e['summary'];self.assertEqual(summary['source_terrain_count'],36)
            self.assertTrue(summary['source_terrain_all_flat'])
            self.assertEqual(summary['source_vegetation_retained']+summary['source_vegetation_rejected'],19)
            self.assertGreater(summary['synthetic_tree_count'],0)
            report=json.loads((folder/'environment-report.json').read_text())
            self.assertEqual(report['qa']['plant_building_intrusions'],0)
            self.assertEqual(report['qa']['plant_road_intrusions'],0)



if __name__=='__main__':unittest.main()
