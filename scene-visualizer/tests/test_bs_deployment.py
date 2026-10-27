import gzip
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from lcm_scene.city.deploy_bs import footprint
from lcm_scene.city.demand_bs import plan_sites, TIMES


class BSDeploymentTests(unittest.TestCase):
    def test_layout_and_demand_consistency(self):
        for km in [1,2,4]:
            folder=ROOT/f'data/scenes/deployed-cities/city-{km}km'
            self.assertTrue(folder.exists(),f'Missing {km}km output; run deploy-bs first')
            scene=json.loads(gzip.decompress((folder/'assembled-city.scene.json.gz').read_bytes()))
            base=json.loads(gzip.decompress((ROOT/f'data/scenes/environment-cities/city-{km}km/assembled-city.scene.json.gz').read_bytes()))
            for k in ['assets','instances','environment','roads','parks','parcels','materials','ground']:
                self.assertEqual(scene[k],base[k])
            r=scene['radio_deployment']; summary=r['summary']; d=r['demand_model']
            self.assertEqual(summary['strategy'],'land-use-demand-500m'); self.assertEqual(summary['nominal_isd_m'],500)
            count=len(r['sites']);self.assertEqual(len(r['sectors']),count*3)
            self.assertEqual(count,summary['site_count']); self.assertEqual(count*3,summary['sector_count'])
            ids={s['id'] for s in r['sites']};self.assertEqual(len(ids),count)
            assets={a['id']:a for a in scene['assets']}
            buildings=unary_union([footprint(assets[i['asset']],i) for i in scene['instances']])
            plants={a['id']:a for a in scene['environment']['vegetation_assets']}
            vegetation=unary_union([footprint(plants[i['asset']],i) for i in scene['environment']['vegetation_instances']])
            roads=unary_union([LineString(x['points']).buffer(x['width_m']/2,cap_style=2) for x in scene['roads']])
            for s in r['sites']:
                p=Point(s['position_m'][:2]); self.assertEqual(s['position_m'][2],25)
                self.assertGreaterEqual(buildings.distance(p),4-1e-5)
                self.assertGreaterEqual(vegetation.distance(p),3-1e-5)
                self.assertGreaterEqual(roads.distance(p),1-1e-5)
                self.assertEqual(len(s['sector_ids']),3);self.assertTrue(s['planning_reason'])
                self.assertTrue(8<=p.x<=km*1000-8 and 8<=p.y<=km*1000-8)
                sectors=[x for x in r['sectors'] if x['site_id']==s['id']]
                self.assertEqual({x['id'] for x in sectors},set(s['sector_ids']))
                angles=sorted(x['azimuth_deg'] for x in sectors)
                np.testing.assert_allclose([(angles[(k+1)%3]-angles[k])%360 for k in range(3)],120,atol=2e-6)
                for x in sectors:self.assertEqual(x['position_m'],s['position_m'])
            xy=np.array([s['position_m'][:2] for s in r['sites']]); nn=cKDTree(xy).query(xy,k=2)[0][:,1]
            self.assertGreaterEqual(nn.min(),150-1e-6)
            self.assertFalse(summary['coverage_validated']);self.assertFalse(summary['capacity_validated'])
            self.assertFalse(d['ue_positions_generated']);self.assertEqual(d['cell_count'],(km*20)**2)
            report=json.loads((folder/'ue-demand.json').read_text());self.assertEqual(report,d)
            cells=d['cells'];coordinates=np.array([c['position_m'] for c in cells])
            distances,owner=cKDTree(xy).query(coordinates)
            np.testing.assert_allclose(distances,[c['planning_distance_m'] for c in cells])
            for i,c in enumerate(cells):self.assertEqual(c['planning_site_id'],r['sites'][int(owner[i])]['id'])
            loads=[]
            for time in TIMES:
                for key in ['present_population','operator_ues','active_ues','demand_mbps','outdoor_network_active_ues','outdoor_network_demand_mbps','pending_indoor_active_ues','pending_indoor_demand_mbps']:
                    total=sum(c['scenarios'][time][key] for c in cells)
                    self.assertAlmostEqual(total,summary['demand_summary'][time][key],places=6)
                for c in cells:
                    t=c['scenarios'][time]
                    self.assertAlmostEqual(t['operator_ues'],t['present_population']*.3)
                    self.assertLessEqual(t['active_ues'],t['operator_ues'])
                    self.assertAlmostEqual(t['demand_mbps'],t['active_ues']*2)
                    self.assertAlmostEqual(t['demand_mbps'],t['outdoor_network_demand_mbps']+t['pending_indoor_demand_mbps'])
                    self.assertAlmostEqual(t['outdoor_network_demand_mbps'],t['outdoor_network_active_ues']*2)
                load=np.bincount(owner,weights=[c['scenarios'][time]['outdoor_network_demand_mbps'] for c in cells],minlength=count)
                loads.append(load)
                np.testing.assert_allclose(load,[s['planning_demand_by_time_mbps'][time] for s in r['sites']])
            proxy=summary['planning_proxy']
            self.assertAlmostEqual(proxy['spatial_max_distance_m'],float(distances.max()))
            self.assertAlmostEqual(proxy['max_assigned_demand_mbps'],float(np.max(loads)))
            expected=bool(distances.max()<=350+1e-7 and np.max(loads)<=600+1e-7)
            self.assertEqual(expected,proxy['constraints_satisfied'])
            self.assertTrue(proxy['constraints_satisfied'],f'{km}km outdoor planning proxy unresolved')
            self.assertFalse(summary['full_city_demand_served'])
            self.assertLessEqual(summary['max_relocation_m'],200+1e-6)
            self.assertEqual(len(d['building_estimates']),len(scene['instances']))
            for scale,mult in [('low',.5),('medium',1),('high',1.5)]:
                self.assertAlmostEqual(summary['fixed_layout_sensitivity'][scale]['max_assigned_demand_mbps'],np.max(loads)*mult)

    def test_demand_changes_site_selection_deterministically(self):
        xy=np.array([[x,y] for y in np.arange(25,1000,50) for x in np.arange(25,1000,50)])
        candidates=np.array([[x,y] for y in np.arange(12,992,25) for x in np.arange(12,992,25)])
        light=np.ones((len(xy),3))*.2
        hotspot=light.copy();hotspot[(xy[:,0]>400)&(xy[:,0]<700)&(xy[:,1]>400)&(xy[:,1]<700)]=40
        a=plan_sites(xy,light,candidates,1000)
        b=plan_sites(xy,hotspot,candidates,1000)
        again=plan_sites(xy,hotspot,candidates,1000)
        self.assertFalse(np.array_equal(a[0],b[0]));np.testing.assert_array_equal(b[0],again[0])
        self.assertTrue(a[-1]['constraints_satisfied']);self.assertTrue(b[-1]['constraints_satisfied'])
        # Heuristic relocation/deletion is not globally optimal: increased
        # demand need not monotonically increase count. Check responsiveness
        # and constrained loads, not an unsupported station-count property.
        self.assertLessEqual(b[5].max(),600+1e-7)
        self.assertLessEqual(b[3].max(),350+1e-7)


if __name__=='__main__':unittest.main()
