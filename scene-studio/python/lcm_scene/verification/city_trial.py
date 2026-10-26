"""Small real RT trial on the saved whole 1 km city, not dense coverage validation."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from shapely import affinity, constrained_delaunay_triangles, get_parts
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from ..paths import STUDIO_ROOT, city_directory


def triangulate(faces):
    vertices=[]
    triangles=[]
    stats=Counter()
    max_deviation=0.0
    for raw in faces:
        p=np.asarray(raw,dtype=float)
        if len(p)>3 and np.allclose(p[0],p[-1],atol=1e-8):
            p=p[:-1]
        if len(p)<3:
            stats['short_faces']+=1
            continue
        # Newell normal, preserving source winding (not proof of outward normals).
        normal=np.sum(np.cross(p,np.roll(p,-1,axis=0)),axis=0)
        norm=np.linalg.norm(normal)
        if norm<1e-9:
            stats['degenerate_faces']+=1
            continue
        normal/=norm
        deviation=float(np.max(np.abs((p-p[0])@normal)))
        max_deviation=max(max_deviation,deviation)
        if deviation>.02:
            raise ValueError(f'Nonplanar face deviation {deviation} m')
        if np.max(np.abs(p[:,2]))<.001:
            stats['ground_coplanar_bottom_faces_omitted']+=1
            continue
        drop=int(np.argmax(np.abs(normal)))
        axes=[i for i in range(3) if i!=drop]
        polygon=Polygon(p[:,axes])
        if not polygon.is_valid or polygon.area<1e-8:
            stats['invalid_projected_faces']+=1
            continue
        for triangle in get_parts(constrained_delaunay_triangles(polygon)):
            flat=np.asarray(triangle.exterior.coords)[:3]
            # CDT uses original boundary vertices; map back to exact source 3D
            # coordinates rather than reconstructing z and creating tiny seams.
            indices=[int(np.argmin(np.linalg.norm(p[:,axes]-q,axis=1))) for q in flat]
            assert all(np.linalg.norm(p[i,axes]-q)<1e-7 for i,q in zip(indices,flat))
            tri=p[indices].copy()
            if np.dot(np.cross(tri[1]-tri[0],tri[2]-tri[0]),normal)<0:
                tri=tri[[0,2,1]]
            offset=len(vertices)
            vertices.extend(tri.tolist())
            triangles.append([offset,offset+1,offset+2])
        stats['faces_triangulated']+=1
    return np.asarray(vertices),np.asarray(triangles,dtype=np.int32),dict(stats),max_deviation


def write_obj(path,vertices,triangles):
    # Share exact exported-coordinate indices; do not weld distinct buildings
    # by a loose nearest-neighbour tolerance.
    rounded=np.round(vertices,6)
    unique,inverse=np.unique(rounded,axis=0,return_inverse=True)
    vertices=unique
    triangles=inverse[triangles]
    with path.open('w') as file:
        for point in vertices:
            file.write('v '+' '.join(f'{v:.6f}' for v in point)+'\n')
        for indices in triangles:
            file.write('f '+' '.join(str(int(i)+1) for i in indices)+'\n')


def prepare(output):
    source=city_directory(1000)/'assembled-city.scene.json.gz'
    raw=source.read_bytes()
    data=json.loads(gzip.decompress(raw))
    assets={a['id']:a for a in data['assets']}
    local={}
    counts=Counter()
    deviation=0
    for key,asset in assets.items():
        v,f,s,d=triangulate(asset['faces'])
        assert len(f)>0,key
        local[key]=(v,f)
        counts.update(s)
        deviation=max(deviation,d)
    world=[]
    triangles=[]
    footprints=[]
    offset=0
    for instance in data['instances']:
        v,f=local[instance['asset']]
        theta=math.radians(instance['rotation_z_deg'])
        rotation=np.array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]])
        world.append(v@rotation.T+np.asarray(instance['position_m']))
        triangles.append(f+offset)
        offset+=len(v)
        asset=assets[instance['asset']]
        p=Polygon(asset['footprint']['outer'],asset['footprint']['holes'])
        p=affinity.rotate(p,instance['rotation_z_deg'],origin=(0,0))
        footprints.append(affinity.translate(p,*instance['position_m'][:2]))
    world=np.concatenate(world)
    triangles=np.concatenate(triangles)
    # Remove duplicated triangles in world coordinates, independent of winding.
    keys=set()
    kept=[]
    for indices in triangles:
        key=tuple(sorted(tuple(p) for p in np.round(world[indices],5)))
        if key not in keys:
            keys.add(key)
            kept.append(indices)
    counts['duplicate_world_triangles_removed']=len(triangles)-len(kept)
    triangles=np.asarray(kept)
    output.mkdir(parents=True,exist_ok=True)
    write_obj(output/'buildings.obj',world,triangles)
    write_obj(output/'ground.obj',np.array([[0,0,0],[1000,0,0],[1000,1000,0],[0,1000,0]]),np.array([[0,1,2],[0,2,3]]))
    obstacle=unary_union(footprints).buffer(2)
    inner=box(5,5,995,995)
    roads=[LineString(r['points']) for r in data['roads'] if r['kind']=='arterial']
    roads=sorted(roads,key=lambda r:r.length,reverse=True)
    rx=[]
    for line in roads:
        for fraction in np.linspace(.08,.92,12):
            p=line.interpolate(float(fraction),normalized=True)
            if inner.covers(p) and not obstacle.intersects(p) and all(p.distance(Point(q[:2]))>12 for q in rx):
                rx.append([p.x,p.y,1.5])
    rx=np.asarray(rx[:32])
    assert len(rx)==32,len(rx)
    # TX over an open street, with some close and distant samples, not a source BS.
    tx=np.array([*rx[5,:2],25.0])
    tx[:2]+=np.array([0.,3.])
    if obstacle.intersects(Point(tx[:2])):
        tx[:2]=rx[5,:2]
    metadata={'source_scene_sha256':hashlib.sha256(raw).hexdigest(),'extent_m':[0,0,1000,1000],
              'building_instances':len(data['instances']),'source_assets':len(assets),
              'exported_building_triangles':len(triangles),'mesh_processing_counts':dict(counts),
              'maximum_source_face_planarity_deviation_m':deviation,
              'normal_policy':'Preserve source face winding; not a watertight/outward-normal audit.',
              'positions_policy':'Synthetic TX on open arterial at 25m; 32 outdoor street RX at 1.5m, at least 2m footprint clearance.',
              'rx_pos_m':rx.tolist(),'tx_pos_m':tx.tolist()}
    (output/'geometry.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    return metadata,tx,rx


def run(output,budgets):
    started=time.perf_counter()
    metadata,tx,rx=prepare(output)
    print('GEOMETRY_READY',metadata['exported_building_triangles'],flush=True)
    import mitsuba as mi
    mi.set_variant('metal_ad_mono_polarized')
    import sionna.rt as rt
    from sionna.rt import Scene,SceneObject,ITURadioMaterial,PlanarArray,Transmitter,Receiver,PathSolver,subcarrier_frequencies
    scene=Scene()
    concrete=ITURadioMaterial(name='assumed_building_concrete',itu_type='concrete',thickness=.2)
    ground=ITURadioMaterial(name='assumed_ground_concrete',itu_type='concrete',thickness=.2)
    scene.add([SceneObject(name='city_buildings',fname=str(output/'buildings.obj'),radio_material=concrete),
               SceneObject(name='flat_ground',fname=str(output/'ground.obj'),radio_material=ground)])
    scene.frequency=3.5e9
    scene.tx_array=PlanarArray(num_rows=1,num_cols=8,horizontal_spacing=.5,vertical_spacing=.5,pattern='iso',polarization='V')
    scene.rx_array=PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
    scene.add(Transmitter('trial_bs',tx.tolist()))
    for i,p in enumerate(rx):
        scene.add(Receiver(f'trial_rx_{i:02d}',p.tolist()))
    frequency=subcarrier_frequencies(64,20e6/64)
    solver=PathSolver(deterministic=True)
    options=dict(max_depth=2,max_num_paths_per_src=200000,los=True,specular_reflection=True,
                 diffuse_reflection=False,refraction=False,diffraction=False,synthetic_array=True,seed=42)
    histories=[]
    previous=None
    saved={}
    for budget in budgets:
        begin=time.perf_counter()
        paths=solver(scene,samples_per_src=budget,**options)
        h=paths.cfr(frequencies=frequency,num_time_steps=1,normalize=False,normalize_delays=False,out_type='numpy')
        a,tau=paths.cir(num_time_steps=1,normalize_delays=False,out_type='numpy')
        assert h.shape==(len(rx),1,1,8,1,64),h.shape
        assert np.isfinite(h).all()
        energy=np.mean(np.abs(h)**2,axis=(1,2,3,4,5))
        valid=np.asarray(paths.valid)
        record={'samples_per_src':budget,'seconds':time.perf_counter()-begin,
                'rx_with_nonzero_csi':int(np.count_nonzero(energy>0)),
                'valid_paths_total':int(valid.sum()),'valid_shape':list(valid.shape),
                'csi_shape':list(h.shape),'mean_channel_gain_per_rx':energy.tolist()}
        if previous is not None:
            record['relative_csi_l2_change_vs_previous_budget']=float(np.linalg.norm(h-previous)/max(np.linalg.norm(h),1e-30))
            delta=np.linalg.norm((h-previous).reshape(len(rx),-1),axis=1)
            scale=np.linalg.norm(h.reshape(len(rx),-1),axis=1)
            record['per_rx_relative_csi_change']=[float(d/s) if s>0 else None for d,s in zip(delta,scale)]
        histories.append(record)
        previous=h.copy()
        saved=dict(rx_pos_m=rx,tx_pos_m=tx[None,:],frequency_offsets_hz=np.asarray(frequency),carrier_frequency_hz=np.array(3.5e9),csi=h,
                   cir_coefficients=a,path_delays_s=tau,path_valid=valid,
                   theta_t_rad=np.asarray(paths.theta_t),phi_t_rad=np.asarray(paths.phi_t),
                   theta_r_rad=np.asarray(paths.theta_r),phi_r_rad=np.asarray(paths.phi_r),
                   interactions=np.asarray(paths.interactions),mean_channel_gain=energy)
        np.savez_compressed(output/f'samples-{budget}.npz',**saved)
        print('RT_BUDGET_RESULT',json.dumps(record),flush=True)
    # LOS-only reference identifies sampled NLOS links without filling zero channels.
    begin=time.perf_counter()
    los_options=dict(options,max_depth=0,specular_reflection=False)
    los_paths=solver(scene,samples_per_src=budgets[-1],**los_options)
    h_los=los_paths.cfr(frequencies=frequency,num_time_steps=1,normalize=False,normalize_delays=False,out_type='numpy')
    los_gain=np.mean(np.abs(h_los)**2,axis=(1,2,3,4,5))
    h=saved['csi']
    H=h[:,0,0,:,0,:]
    codebook=np.exp(-2j*np.pi*np.arange(8)[:,None]*np.arange(8)[None,:]/8)/np.sqrt(8)
    beam=np.mean(np.abs(np.einsum('naf,ab->nbf',H,codebook))**2,axis=-1)
    active=saved['mean_channel_gain']>0
    best=np.where(active,np.argmax(beam,axis=1),-1)
    saved.update(csi_los_only=h_los,los_mean_channel_gain=los_gain,beam_gains=beam,best_beams=best,channel_valid=active)
    reconstructed=np.sum(a[...,0][...,None]*np.exp(-2j*np.pi*tau[:,None,:,None,:,None]*np.asarray(frequency)),axis=-2)[:,:,:,:,None,:]
    reconstruction_error=float(np.linalg.norm(reconstructed-h)/max(np.linalg.norm(h),1e-30))
    assert reconstruction_error<1e-4,reconstruction_error
    np.savez_compressed(output/'samples.npz',**saved)
    report={'date':'2026-10-26','status':'Real Sionna RT sparse trial on whole saved 1 km geometry; not a measured/validated city dataset.',
            'versions':{'sionna_rt':rt.__version__,'mitsuba':mi.__version__},'backend':mi.variant(),
            'geometry':metadata,'carrier_hz':3.5e9,'bandwidth_hz':20e6,'subcarriers':64,'tx_antennas':8,'rx_antennas':1,
            'array':'1x8 TX, half-wavelength spacing, isotropic V; synthetic_array approximation',
            'material_assumptions':'All building surfaces and flat ground use ITU concrete, thickness 0.2m, no source material claims.',
            'rt_options':options,'budget_runs':histories,'los_only_seconds':time.perf_counter()-begin,
            'los_rx_count':int(np.count_nonzero(los_gain>0)),
            'nlos_rx_with_found_reflections':int(np.count_nonzero((los_gain==0)&(saved['mean_channel_gain']>0))),
            'zero_csi_rx_count':int(np.count_nonzero(saved['mean_channel_gain']==0)),
            'csi_axes':['rx_position','rx_ant','tx','tx_ant','time_step','frequency'],
            'csi_shape':list(h.shape),'elapsed_seconds':time.perf_counter()-started,
            'frequency_offsets_hz':'64 baseband offsets [-10e6,9.6875e6], spacing 312500 Hz; add carrier for absolute frequency.',
            'array_orientation_rad':[0,0,0],
            'cir_to_csi_relative_reconstruction_error':reconstruction_error,
            'best_beam_policy':'-1 for zero-channel RX; channel_valid must be true for a usable beam label.',
            'limitations':['Sparse single-TX static trial, not full coverage map','No convergence certification from two budgets',
                           'No diffraction/refraction/diffuse reflection/vegetation/indoor users','Source previews not audited watertight meshes or source materials',
                           'Ground/road/park all represented by one flat assumed concrete surface; visual tree points excluded',
                           'No DeepMIMO format conversion or PHY link simulation in this trial','Zero channels indicate no paths found under configured solver, not proof of no physical propagation']}
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('TRIAL_COMPLETE',json.dumps({k:report[k] for k in ['csi_shape','los_rx_count','nlos_rx_with_found_reflections','zero_csi_rx_count','elapsed_seconds']}),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=STUDIO_ROOT/'generated/rt/city-1km-trial-v2')
    parser.add_argument('--budgets',type=int,nargs='+',default=[20000,100000,1000000])
    args=parser.parse_args()
    run(args.output.resolve(),args.budgets)


if __name__=='__main__':
    main()
