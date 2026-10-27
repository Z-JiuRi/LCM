import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.verification'

"""Small scene-composition verification; not a city-scale performance benchmark."""
from pathlib import Path
import json, time
import numpy as np
from ..paths import TEST_SCENE_ROOT

def main():
    import mitsuba as mi
    mi.set_variant("metal_ad_mono_polarized")
    import sionna.rt as rt
    from sionna.rt import Scene, SceneObject, ITURadioMaterial, PlanarArray, Transmitter, Receiver, PathSolver, subcarrier_frequencies

    ROOT=TEST_SCENE_ROOT
    ROOT.mkdir(parents=True, exist_ok=True)
    started=time.perf_counter()

    def mesh_file(name, vertices, faces):
        f=ROOT/(name+'.obj')
        f.write_text('\n'.join(['v '+' '.join(map(str,v)) for v in vertices]+['f '+' '.join(str(i+1) for i in face) for face in faces])+'\n')
        return str(f)

    def box(name, bounds, material):
        x0,x1,y0,y1,z0,z1=bounds
        v=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
        quads=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        faces=[t for a,b,c,d in quads for t in [(a,b,c),(a,c,d)]]
        return SceneObject(name=name,fname=mesh_file(name,v,faces),radio_material=material)

    def tile(prefix):
        scene=Scene()
        mat=ITURadioMaterial(name=prefix+'_concrete',itu_type='concrete',thickness=0.2)
        ground=SceneObject(name=prefix+'_ground',fname=mesh_file(prefix+'_ground',[(-40,-25,0),(0,-25,0),(0,25,0),(-40,25,0)],[(0,1,2),(0,2,3)]),radio_material=mat)
        north=box(prefix+'_north',[-30,-15,8,20,0,12],mat)
        south=box(prefix+'_south',[-28,-12,-20,-8,0,9],mat)
        scene.add([ground,north,south])
        return scene

    scene_a=tile('a')
    scene_b=tile('b')
    moving=list(scene_b.objects.values())
    scene_b.remove(moving)
    for matname in list(scene_b.radio_materials):
        scene_b.remove(matname)
    for obj in moving:
        obj.position=obj.position+mi.Point3f(40,0,0)
    scene_a.add(moving)
    scene=scene_a
    assert len(scene.objects)==6 and len(scene_b.objects)==0
    scene.frequency=3.5e9
    scene.tx_array=PlanarArray(num_rows=1,num_cols=8,horizontal_spacing=0.5,vertical_spacing=0.5,pattern='iso',polarization='V')
    scene.rx_array=PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
    scene.add(Transmitter('bs',[-35,0,6]))
    frequencies=subcarrier_frequencies(32,20e6/32)
    solver=PathSolver(deterministic=True)
    kwargs=dict(max_depth=2,samples_per_src=20000,max_num_paths_per_src=20000,los=True,specular_reflection=True,diffuse_reflection=False,refraction=False,diffraction=False,synthetic_array=True,seed=42)

    def cfr():
        paths=solver(scene,**kwargs)
        h=paths.cfr(frequencies=frequencies,num_time_steps=1,normalize=False,normalize_delays=False,out_type='numpy')
        assert np.isfinite(h).all()
        return paths,h

    # Static samples on both sides of the join x=0; deliberately small for verification.
    static_pos=np.array([[x,y,1.5] for x in [-30,-10,10,30] for y in [-2,2]],dtype=float)
    for i,p in enumerate(static_pos):scene.add(Receiver(f'static_{i}',p.tolist()))
    paths,h_static=cfr()
    assert h_static.shape==(8,1,1,8,1,32),h_static.shape
    assert np.all(np.sum(np.abs(h_static)**2,axis=(1,2,3,4,5))>0)
    print('STATIC_PASS',h_static.shape, 'tau_shape',paths.tau.shape,flush=True)
    for i in range(len(static_pos)):scene.remove(f'static_{i}')

    # Recompute geometry-dependent paths at every point on a short UE trajectory crossing x=0.
    ue=Receiver('mobile',[-1,0,1.5]);scene.add(ue)
    xs=np.linspace(-1,1,9)
    hs=[]
    for x in xs:
        ue.position=[float(x),0,1.5]
        paths,h=cfr();hs.append(h)
    h_trajectory=np.concatenate(hs,axis=0)
    assert np.all(np.sum(np.abs(h_trajectory)**2,axis=(1,2,3,4,5))>0)
    print('TRAJECTORY_PASS',h_trajectory.shape,flush=True)

    # Revisit exact same physical position; deterministic computation must reproduce its CFR.
    ue.position=[0,0,1.5]
    _,h_again=cfr()
    revisit_error=float(np.max(np.abs(h_again-hs[4])))
    assert np.allclose(h_again,hs[4],rtol=1e-5,atol=1e-10)

    # DFT codebook; calculate wideband average power for every beam at each trajectory point.
    H=h_trajectory[:,0,0,:,0,:]
    codebook=np.exp(-2j*np.pi*np.arange(8)[:,None]*np.arange(8)[None,:]/8)/np.sqrt(8)
    powers=np.mean(np.abs(np.einsum('naf,ab->nbf',H,codebook))**2,axis=-1)
    assert powers.shape==(9,8) and np.isfinite(powers).all() and np.all(powers.max(axis=1)>0)
    print('BEAMS_PASS',powers.shape,flush=True)

    # Moving blocker: verify geometry update actually removes a previously present direct path.
    mat=scene.radio_materials['a_concrete']
    blocker=box('movable_blocker',[-1,1,12,16,0,4],mat);scene.add(blocker)
    ue.position=[10,0,1.5]
    los_kwargs=dict(kwargs);los_kwargs.update(max_depth=0,specular_reflection=False)
    def los_energy():
        p=solver(scene,**los_kwargs)
        h=p.cfr(frequencies=frequencies,num_time_steps=1,normalize=False,normalize_delays=False,out_type='numpy')
        return float(np.sum(np.abs(h)**2))
    clear_energy=los_energy()
    blocker.position=blocker.position+mi.Point3f(0,-14,0)
    blocked_energy=los_energy()
    assert clear_energy>0 and blocked_energy==0,(clear_energy,blocked_energy)
    print('BLOCKER_PASS',clear_energy,blocked_energy,flush=True)
    np.savez_compressed(ROOT/'samples.npz',static_positions=static_pos,static_csi=h_static,trajectory_x=xs,trajectory_csi=h_trajectory,beam_powers=powers,best_beams=np.argmax(powers,axis=1))
    report={'sionna_rt':rt.__version__,'mitsuba':mi.__version__,'backend':mi.variant(),'geometry':'Two independently created 40x50 m tiles, 2 buildings per tile, joined at x=0; no duplicate ground overlap','source_objects_moved':len(moving),'combined_objects_before_blocker':6,'static_positions':len(static_pos),'static_csi_shape':list(h_static.shape),'trajectory_positions':len(xs),'trajectory_x_m':xs.tolist(),'trajectory_csi_shape':list(h_trajectory.shape),'beam_powers_shape':list(powers.shape),'revisit_max_absolute_error':revisit_error,'los_energy_before_blocker':clear_energy,'los_energy_after_blocker':blocked_energy,'elapsed_seconds':time.perf_counter()-started,'scope':'Small functional test only. No Boston5G import, full-city memory/runtime benchmark, dense phase-continuity study, diffraction validation, or DeepMIMO export tested.'}
    (ROOT/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()
