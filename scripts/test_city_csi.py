"""Lightweight deterministic tests: synthetic paths/data only, no Sionna/RT."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import generate_city_csi as G


class ChannelTests(unittest.TestCase):
    def config(self):
        return dict(samples_per_src=100000,max_depth=3,max_num_paths_per_src=200000,
                    diffuse_reflection=False,diffraction=False,edge_diffraction=False,refraction=False,
                    seed=42,tx_power_dbm=44.,bandwidth_hz=20e6,n_fft=1024,n_sc=64,
                    convention='deepmimo',num_antennas=32,significant_db=25.,
                    split_mode='random',block_m=100.)

    def test_frequencies(self):
        bins,f=G.frequency_plan()
        np.testing.assert_array_equal(bins,np.arange(0,1024,16))
        self.assertEqual(f[0],0);self.assertEqual(f[-1],19687500)
        np.testing.assert_allclose(np.diff(f),312500)
        _,c=G.frequency_plan(convention='centered')
        self.assertEqual(c[0],-10000000);self.assertEqual(c[-1],9687500)
        with self.assertRaises(ValueError):G.frequency_plan(n_sc=63)

    def test_cfr_and_inverse_preprocessing(self):
        rng=np.random.default_rng(42)
        a=(rng.normal(size=(3,1,32,4))+1j*rng.normal(size=(3,1,32,4))).astype(np.complex64)
        tau=np.array([[1,2,3,4],[2,3,4,5],[3,4,5,6]])*1e-7
        valid=np.ones((3,4),bool);valid[0,-1]=False
        _,f=G.frequency_plan()
        h,clipped=G.synthesize_cfr(a,tau,valid,f)
        expected=np.zeros_like(h,dtype=np.complex128)
        for u in range(3):
            for p in range(4):
                if valid[u,p]:expected[u]+=a[u,:,:,p,None]*np.exp(-2j*np.pi*tau[u,p]*f)/np.sqrt(1024)
        np.testing.assert_allclose(h,expected,rtol=1e-5,atol=1e-7)
        gain,ref,count=G.path_statistics(a,tau,valid)
        normalized,rms=G.align_and_normalize(h[:,0],ref,f)
        np.testing.assert_allclose(np.mean(abs(normalized)**2,axis=(1,2)),1,atol=2e-7)
        inverse=normalized*rms[:,None,None]*np.exp(-2j*np.pi*ref[:,None,None]*f)
        np.testing.assert_allclose(inverse,h[:,0],rtol=1e-5,atol=1e-7)
        self.assertTrue((gain>0).all());np.testing.assert_array_equal(count,[3,4,4])
        self.assertFalse(clipped.any())

    def test_path_mask_and_no_paths(self):
        a=np.zeros((2,1,32,0),np.complex64);tau=np.zeros((2,0));valid=np.zeros((2,0),bool)
        gain,ref,count=G.path_statistics(a,tau,valid)
        self.assertTrue(np.isnan(ref).all());self.assertFalse(gain.any());self.assertFalse(count.any())
        _,f=G.frequency_plan();h,_=G.synthesize_cfr(a,tau,valid,f)
        self.assertEqual(h.shape,(2,1,32,64));self.assertFalse(h.any())
        a=np.ones((1,1,32,2),np.complex64)
        tau=np.array([[0.,1024/20e6]]);valid=np.ones((1,2),bool)
        h,drop=G.synthesize_cfr(a,tau,valid,f)
        np.testing.assert_allclose(h,1/32);np.testing.assert_array_equal(drop,[1])
        valid[:]=False
        h,_=G.synthesize_cfr(a,tau,valid,f);self.assertFalse(h.any())
        with self.assertRaises(ValueError):G.align_and_normalize(h[:,0],np.zeros(1),f)

    def test_significant_reference_not_necessarily_earliest(self):
        a=np.ones((1,1,32,3),np.complex64);a[:,:,:,0]=.001
        tau=np.array([[1e-9,2e-9,3e-9]]);valid=np.ones((1,3),bool)
        _,ref,_=G.path_statistics(a,tau,valid)
        self.assertEqual(ref[0],2e-9)

    def test_fixed_solver_budget_and_physics_flags(self):
        config=self.config();opts=G.solver_options(config,2)
        self.assertEqual(opts['samples_per_src'],100000)
        self.assertNotIn('samples_per_link',opts)
        config['diffraction']=True;config['diffuse_reflection']=True
        opts=G.solver_options(config,2)
        self.assertTrue(opts['diffraction']);self.assertTrue(opts['diffuse_reflection'])
        self.assertEqual(opts['seed'],44)

    def test_spatial_split_keeps_blocks_together(self):
        xy=np.array([[x*100+v,y*100+v,1.5] for y in range(10) for x in range(10) for v in [10,20]])
        split=G.split_indices(xy)
        np.testing.assert_array_equal(split[::2],split[1::2])
        np.testing.assert_array_equal(split,G.split_indices(xy))
        self.assertEqual(np.sum(split==0),160);self.assertEqual(np.sum(split==1),20)

    def test_serving_association_and_output_dimensions(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d);config=self.config();config['n_sc']=4;config['n_fft']=8
            positions=np.array([[10+i*10,20,1.5] for i in range(10)])
            results=[];raws=[]
            for j in range(2):
                folder=output/f's{j}';folder.mkdir()
                H=np.ones((10,1,32,4),np.complex64)*(j+1)*(1+1j)
                # Selection deliberately disagrees with CFR magnitude.
                power=np.array([3 if i%2==j else 1 for i in range(10)],float)
                power[-1]=0;H[-1]=0
                refs=np.ones(10)*1e-7*(j+1);refs[-1]=np.nan
                np.save(folder/'csi.npy',H);raws.append(H)
                np.savez(folder/'link_stats.npz',path_gain_linear=power,tau_ref_s=refs,
                         path_counts=np.ones(10,np.int32),delay_window_clipped=np.zeros(10,np.int32),no_path_found=np.zeros(10,bool))
                results.append(dict(folder=str(folder),sector={'id':f'S{j}'}))
            summary=G.export_feedback(output,results,positions,config)
            self.assertEqual(summary['feedback_samples'],9);self.assertEqual(summary['no_path_found_all_sectors'],0)
            self.assertEqual(summary['zero_power_despite_valid_paths'],1)
            self.assertEqual(summary['valid_path_ues'],10)
            with np.load(output/'association.npz') as z:
                np.testing.assert_array_equal(z['serving_sector_index'],[0,1,0,1,0,1,0,1,0,-1])
                self.assertFalse(z['no_path_found_all_sectors'].any())
                self.assertTrue(z['zero_power_despite_valid_paths'][-1])
                for name in ['train','val','test']:
                    data=np.load(output/f'{name}.npy')
                    self.assertEqual(data.dtype,np.float32);self.assertEqual(data.shape[1:],(2,32,4))
                    with np.load(output/f'{name}_aux.npz') as aux:
                        reconstructed=(data[:,0]+1j*data[:,1])*aux['rms'][:,None,None]
                        reconstructed*=np.exp(-2j*np.pi*aux['tau_ref_s'][:,None,None]*z['frequencies_hz'])
                        expected=np.array([raws[s][u,0] for u,s in zip(aux['ue_indices'],aux['serving_sector_index'])]).reshape(-1,32,4)
                        np.testing.assert_allclose(reconstructed,expected,rtol=1e-5,atol=1e-7)
                        self.assertEqual(len(aux['ue_positions_m']),len(data))
            self.assertEqual(sum(v['count'] for v in summary['splits'].values()),9)

    def test_dry_run_never_imports_rt_or_creates_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);geometry=root/'geo';geometry.mkdir()
            (geometry/'one.obj').write_text('v 0 0 0\n')
            G.write_json(geometry/'geometry-manifest.json',dict(groups=[{'obj':'one.obj'}],materials=[]))
            np.save(geometry/'ue_candidates.npy',np.array([[10,20,1.5],[30,40,1.5]]))
            dep=root/'dep.json';G.write_json(dep,dict(sectors=[dict(id='S',position_m=[20,30,25],azimuth_deg=0,downtilt_deg=10)]))
            target=root/'output'
            with patch.object(G,'_worker',side_effect=AssertionError('RT must not run')),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(G.main(['--geometry',str(geometry),'--deployment',str(dep),'--output',str(target),'--dry-run']),0)
            self.assertFalse(target.exists())

    def test_mocked_worker_batches_and_complete_export(self):
        """Exercise real worker/main control flow with fake APIs, never import RT."""
        import sys
        from types import ModuleType, SimpleNamespace
        scene=SimpleNamespace(receivers={})
        def add(items):
            if isinstance(items,list):
                for item in items:scene.receivers[item.name]=item.position
        scene.add=add;scene.remove=lambda name:scene.receivers.pop(name)
        calls=[]
        class FakeSolver:
            def __init__(self,deterministic):self.deterministic=deterministic
            def __call__(self,scene,**options):
                calls.append((len(scene.receivers),options.copy()))
                n=len(scene.receivers)
                # paths.a is a (real_part, imag_part) tuple of ndarrays.
                # synthetic_array=True layout: [U, RX_ant, TX, TX_ant, P]
                # We use 1 RX_ant, 1 TX, 32 TX_ant, 2 paths.
                a_re=np.zeros((n,1,1,32,2),np.float32);a_im=np.zeros_like(a_re)
                tau=np.full((n,1,2),-1.,np.float32)   # [U,TX,P], invalid = -1
                valid=np.zeros((n,1,2),bool)           # [U,TX,P]
                for row,pos in enumerate(scene.receivers.values()):
                    if pos[0]<30:
                        # one valid path with passband coefficient 1+1j
                        a_re[row,0,0,:,0]=1.; a_im[row,0,0,:,0]=1.
                        tau[row,0,0]=1e-7; valid[row,0,0]=True
                angle=np.zeros((n,1,2));interactions=np.zeros((1,n,1,2),np.uint32)
                return SimpleNamespace(
                    a=(a_re,a_im), tau=tau, valid=valid,
                    theta_t=angle,phi_t=angle,theta_r=angle,phi_r=angle,
                    interactions=interactions,vertices=np.zeros((1,n,1,2,3)))
        mi=ModuleType('mitsuba');mi.set_variant=lambda variant:None;mi.__version__='fake'
        rt=ModuleType('sionna.rt');rt.__version__='fake';rt.PathSolver=FakeSolver
        rt.Receiver=lambda name,position:SimpleNamespace(name=name,position=position)
        rt.Transmitter=lambda *args,**kwargs:SimpleNamespace(name='tx')
        parent=ModuleType('sionna');parent.rt=rt
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);geo=root/'geo';geo.mkdir()
            (geo/'one.obj').write_text('v 0 0 0\n')
            G.write_json(geo/'geometry-manifest.json',dict(groups=[{'obj':'one.obj'}],materials=[]))
            np.save(geo/'ue_candidates.npy',np.array([[10.,20.,1.5],[20.,20.,1.5],[30.,20.,1.5]]))
            dep=root/'dep.json';G.write_json(dep,dict(sectors=[dict(id='S',position_m=[0,0,25],azimuth_deg=0,downtilt_deg=10)]))
            target=root/'out'
            argv=['--geometry',str(geo),'--deployment',str(dep),'--output',str(target),
                  '--workers','1','--chunk','2','--split-mode','random','--samples-per-src','1234']
            with patch.dict(sys.modules,{'mitsuba':mi,'sionna':parent,'sionna.rt':rt}),\
                 patch.object(G,'build_scene',return_value=scene),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(G.main(argv),0)
            self.assertEqual([n for n,_ in calls],[2,1])
            self.assertTrue(all(opt['samples_per_src']==1234 for _,opt in calls))
            self.assertFalse(scene.receivers)
            report=json.loads((target/'report.json').read_text())
            self.assertEqual(report['status'],'complete');self.assertEqual(report['counts']['feedback_samples'],2)
            self.assertEqual(report['counts']['no_path_found_all_sectors'],1)
            self.assertEqual(np.load(target/'raw/sector-000/csi.npy').shape,(3,1,32,64))
            for filename,batch in [('paths-0000000-0000002.npz',2),('paths-0000002-0000003.npz',1)]:
                with np.load(target/'raw/sector-000'/filename,allow_pickle=False) as z:
                    self.assertEqual(z['passband_coefficients'].shape,(batch,1,32,2))
                    self.assertEqual(z['path_valid'].shape,(batch,2))
                    self.assertIn('interactions',z.files);self.assertIn('vertices_m',z.files)
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):G.main(argv)


class GeometryTests(unittest.TestCase):
    def scene(self):
        cube=[[[0,0,1],[2,0,1],[2,2,1],[0,2,1]],
              [[0,0,1],[0,0,3],[2,0,3],[2,0,1]]]
        material=dict(permittivity=5.31,conductivity=.08987,thickness=.3,
                      scattering_model='directive',scattering_coefficient=.2,
                      cross_polarization_coefficient=.4,alpha_r=4)
        return dict(assets=[dict(id=0,faces=cube,face_material_keys=['A','B'],
                    footprint={'outer':[[0,0],[2,0],[2,2],[0,2]]})],
                    instances=[dict(asset=0,rotation_z_deg=0,position_m=[1,1,0])],
                    materials={'A':material,'B':dict(material,scattering_model='none')},
                    ground={'extent_m':[0,0,10,10]},environment={})

    def test_mixed_materials_and_exact_vertices(self):
        import city_geometry as C
        with tempfile.TemporaryDirectory() as d:
            groups=C.export_buildings(self.scene(),Path(d))
            self.assertEqual({g['material_key'] for g in groups},{'A','B'})
            self.assertEqual(sum(g['triangles'] for g in groups),4)
            for g in groups:
                vertices=[]
                for line in (Path(d)/g['obj']).read_text().splitlines():
                    if line.startswith('v '):vertices.append(list(map(float,line[2:].split())))
                self.assertTrue(all(v[2]>=1 for v in vertices))

    def test_concave_triangulation_and_invalid_faces(self):
        import city_geometry as C
        face=np.array([[0,0,1],[3,0,1],[3,3,1],[2,1,1],[0,3,1]],float)
        triangles=C._triangulate_face(face)
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        self.assertTrue(Polygon(face[:,:2]).equals(unary_union([Polygon(t[:,:2]) for t in triangles])))
        self.assertTrue(all(tuple(v) in set(map(tuple,face)) for t in triangles for v in t))
        with self.assertRaises(ValueError):C._triangulate_face([[0,0,0],[1,0,0],[1,1,.1],[0,1,0]])

    def test_zero_clearance_excludes_interiors(self):
        import city_geometry as C
        scene=self.scene()
        pos,stats=C.build_ue_grid(scene,1,1.5,0,0,(0,0,10,10))
        from shapely.geometry import Point
        obstacle=C.building_footprints(scene)[0]
        self.assertFalse(any(obstacle.covers(Point(p[:2])) for p in pos))
        with self.assertRaises(ValueError):C.build_ue_grid(scene,0,1.5,0,0,(0,0,10,10))

    def test_material_mapping_and_no_hidden_fallback(self):
        import city_geometry as C
        material=C.resolve_materials(self.scene(),['A','B'])
        a,b=material
        self.assertEqual(a.scattering_pattern,'directive');self.assertEqual(a.scattering_kwargs,{'alpha_r':4})
        self.assertEqual(b.scattering_coefficient,0);self.assertEqual(b.source_record['scattering_coefficient'],.2)
        self.assertTrue(b.scattering_assumptions)
        scene=self.scene();del scene['materials']['A']['conductivity']
        with self.assertRaises(ValueError):C.resolve_materials(scene,['A'])
        with self.assertRaises(ValueError):C.resolve_materials(scene,['missing'])

    def test_synthetic_geometry_cli_manifest_and_no_overwrite(self):
        import city_geometry as C
        import gzip
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input.gz';source.write_bytes(gzip.compress(json.dumps(self.scene()).encode()))
            out=Path(d)/'output';manifest=C.prepare(source,out)
            self.assertEqual(manifest['scene_sha256'],G.sha256(source))
            self.assertEqual(manifest['ue_candidates_sha256'],G.sha256(out/'ue_candidates.npy'))
            for group in manifest['groups']:self.assertEqual(group['sha256'],G.sha256(out/group['obj']))
            with self.assertRaises(FileExistsError):C.prepare(source,out)


if __name__=='__main__':unittest.main(verbosity=2)
