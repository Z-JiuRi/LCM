"""Build an explicit, traceable 1/2/4 km environment variant; no channel computation."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import numpy as np
from scipy.io import loadmat
from shapely import affinity,constrained_delaunay_triangles,get_parts
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from ..paths import REPO_ROOT,STUDIO_ROOT


def load(folder):
    objects=json.loads((folder/'objects.json').read_text())
    params=json.loads((folder/'params.json').read_text())
    file=list(folder.glob('vertices.*'))[0]
    if file.suffix=='.mat':vertices=loadmat(file)['vertices']
    else:
        with np.load(file,allow_pickle=False) as z:vertices=z['vertices']
    return objects,params,np.asarray(vertices,dtype=float),{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [folder/'objects.json',folder/'params.json',file]}


def serial(poly):
    return {'outer':np.asarray(poly.exterior.coords).round(6).tolist(),'holes':[np.asarray(r.coords).round(6).tolist() for r in poly.interiors]}


def parts(shape):
    return [p for p in get_parts(shape) if isinstance(p,Polygon) and p.area>1e-6]


def tree_faces(radius=3,height=9):
    # Synthetic regular polygon trunk and double cone crown, not recovered botany.
    faces=[]
    def ring(r,z):return [[r*math.cos(a),r*math.sin(a),z] for a in np.linspace(0,2*math.pi,12,endpoint=False)]
    bottom=ring(.25,0);top=ring(.25,height*.55)
    faces.extend([bottom[::-1],top])
    for i in range(12):faces.append([bottom[i],bottom[(i+1)%12],top[(i+1)%12],top[i]])
    crown=ring(radius,height*.62)
    for i in range(12):
        faces.append([[0,0,height*.32],crown[(i+1)%12],crown[i]])
        faces.append([crown[i],crown[(i+1)%12],[0,0,height]])
    return faces


def build(downloads,output,size=1000):
    baseline=STUDIO_ROOT/f'data/scenes/official-cities/city-{size//1000}km'
    raw=(baseline/'assembled-city.scene.json.gz').read_bytes()
    scene=json.loads(gzip.decompress(raw));original=deepcopy(scene)
    view=json.loads((baseline/'assembled-city.view.json').read_text())
    assets={a['id']:a for a in scene['assets']}
    buildings=[]
    for instance in scene['instances']:
        a=assets[instance['asset']];p=Polygon(a['footprint']['outer'],a['footprint']['holes'])
        buildings.append(affinity.translate(affinity.rotate(p,instance['rotation_z_deg'],origin=(0,0)),*instance['position_m'][:2]))
    building_mask=unary_union(buildings)
    boundary=box(0,0,size,size)
    road_mask=unary_union([LineString(r['points']).buffer(r['width_m']/2,cap_style=2) for r in scene['roads']]).intersection(boundary)
    park_mask=unary_union([Polygon(p['outer'],p['holes']) for p in scene['parks']]).difference(road_mask).intersection(boundary)
    # No source has relief. A single continuous z=0 surface is partitioned,
    # not 36 overlapping source ground planes stacked together.
    other=boundary.difference(road_mask).difference(park_mask)
    classifications=[('road',road_mask,'environment:asphalt'),('park',park_mask,'environment:soil'),('other',other,'environment:soil')]
    terrain_vertices=[];terrain_triangles=[];terrain_keys=[];terrain_roles=[];vertex_index={}
    for role,shape,key in classifications:
        for poly in parts(shape):
            for triangle in get_parts(constrained_delaunay_triangles(poly)):
                indices=[]
                q=np.asarray(triangle.exterior.coords)[:3]
                a=q[1]-q[0];b=q[2]-q[0]
                if a[0]*b[1]-a[1]*b[0]<0:q=q[[0,2,1]]
                for xy in q:
                    xyz=(round(float(xy[0]),8),round(float(xy[1]),8),0.0)
                    if xyz not in vertex_index:vertex_index[xyz]=len(terrain_vertices);terrain_vertices.append(list(xyz))
                    indices.append(vertex_index[xyz])
                terrain_triangles.append(indices);terrain_keys.append(key);terrain_roles.append(role)
    vegetation_assets=[];vegetation_instances=[];audit=[]
    source_candidate_rejections=[]
    boston=None
    for folder in sorted(downloads.iterdir()):
        if not folder.is_dir() or not (folder/'objects.json').exists():continue
        objects,params,v,hashes=load(folder)
        records=[]
        for obj in objects:
            if obj.get('label') not in ['terrain','vegetation']:continue
            points=v[np.concatenate(obj['face_vertex_idxs'])]
            records.append({'object_id':obj['id'],'label':obj['label'],'z_range_m':[float(points[:,2].min()),float(points[:,2].max())],
                            'extent_m':np.ptp(points,axis=0).tolist(),'face_material_ids':sorted(set(obj['face_material_idxs']))})
        audit.append({'source':folder.name,'files_sha256':hashes,'environment_objects':records})
        if folder.name=='boston5g_3p5':boston=(objects,params,v)
    assert all(r['z_range_m'][1]-r['z_range_m'][0]<1e-6 for a in audit for r in a['environment_objects'] if r['label']=='terrain')
    objects,params,v=boston
    group=next(g for g in scene['manifest']['preserved_groups'] if g['source']=='boston5g_3p5')
    source_center=np.asarray(group['source_center_m']);target_center=np.asarray(group['target_center_m']);angle=group['rotation_z_deg']
    rotation=np.array([[math.cos(math.radians(angle)),-math.sin(math.radians(angle))],[math.sin(math.radians(angle)),math.cos(math.radians(angle))]])
    occupied=[]
    for obj in objects:
        if obj.get('label')!='vegetation':continue
        faces=[v[ring] for ring in obj['face_vertex_idxs']]
        points=np.concatenate(faces);center=(points[:,:2].min(0)+points[:,:2].max(0))/2
        base=float(points[:,2].min());local=[(f-np.array([*center,base])).tolist() for f in faces]
        xy=target_center+rotation@(center-source_center)
        hull=Polygon(np.asarray(local[0])[:,:2]).convex_hull
        if hull.area<1e-6:hull=unary_union([Point(p[:2]) for f in local for p in f]).convex_hull
        footprint=affinity.translate(affinity.rotate(hull,angle,origin=(0,0)),*xy)
        reasons=[]
        if not boundary.covers(footprint):reasons.append('outside-city')
        if footprint.intersection(building_mask).area>.01:reasons.append('building-overlap')
        if footprint.intersection(road_mask).area>.01:reasons.append('road-overlap')
        if any(footprint.intersection(p).area>.01 for p in occupied):reasons.append('vegetation-overlap')
        if reasons:source_candidate_rejections.append({'id':obj['id'],'reasons':reasons});continue
        key=f'boston-vegetation-{obj["id"]}'
        matkeys=[]
        for idx in obj['face_material_idxs']:
            m=next((k,m) for k,m in params['materials'].items() if m['id']==idx)
            qualified=f'boston5g_3p5:{m[0]}'
            scene['materials'].setdefault(qualified,{**m[1],'source_scene':'boston5g_3p5','reference_frequency_hz':3.5e9,'provenance':'Official raw material binding; vegetation label is concrete in archive, NOT a validated foliage material.'})
            matkeys.append(qualified)
        vegetation_assets.append({'id':key,'faces':local,'height_m':float(np.ptp(points[:,2])),'footprint':serial(hull),
                                  'source':'boston5g_3p5','official_object_id':obj['id'],'face_material_keys':matkeys,
                                  'provenance':'Source vegetation-labelled simplified 25m volume; same Boston group rigid transform, not an individual realistic tree.',
                                  'rt_status':'Disabled: archive concrete binding is not a validated foliage electromagnetic model.'})
        vegetation_instances.append({'id':key+'-placed','asset':key,'position_m':[*xy,0.0],'rotation_z_deg':angle,'placement':'preserved-source-group','rt_enabled':False})
        occupied.append(footprint)
    # Explicit materials assumptions for redesigned ground. Reuse source numeric
    # references but not silently promote them to ground-truth frequency models.
    _,reference,_v,_hash=load(downloads/'city_21_taito_city_3p5')
    asphalt=reference['materials']['material_1'];soil=reference['materials']['material_2']
    scene['materials']['environment:asphalt']={**asphalt,'source_scene':'city_21_taito_city_3p5','reference_frequency_hz':1e9,
        'provenance':'Design assignment to synthetic roads; original name Asphalt_1GHz, use at 3.5GHz requires validation.'}
    scene['materials']['environment:soil']={**soil,'source_scene':'city_21_taito_city_3p5','reference_frequency_hz':3.5e9,
        'provenance':'Design assignment to parks/other ground using source ITU Wet earth numbers, not measured new-city ground.'}
    scene['materials']['environment:foliage-unassigned']={'name':'Foliage model pending','provenance':'No permittivity/conductivity invented. Visual synthetic tree only; RT disabled.'}
    seed=261026103+(size//1000-1)
    rng=random.Random(seed)
    available=park_mask.difference(building_mask.buffer(4)).buffer(-4)
    paths=LineString(scene['green_path']).buffer(2)
    available=available.difference(paths)
    for n,(radius,height) in enumerate([(2.5,7),(3.2,10),(4.,12)]):
        ring=[(radius*math.cos(a),radius*math.sin(a)) for a in np.linspace(0,2*math.pi,12,endpoint=False)]
        vegetation_assets.append({'id':f'synthetic-tree-{n}','faces':tree_faces(radius,height),'height_m':height,'footprint':serial(Polygon(ring)),
            'source':'synthetic-design','face_material_keys':['environment:foliage-unassigned'],'provenance':'Synthetic trunk/crown mesh; new designed park planting, not official source vegetation.',
            'rt_status':'Disabled pending foliage propagation model selection.'})
    # Spaced planting lattice with deterministic jitter, collision-tested crown footprint.
    source_occupied=list(occupied)
    for x in np.arange(8,size,18):
        for y in np.arange(8,size,18):
            xy=[float(x+rng.uniform(-3,3)),float(y+rng.uniform(-3,3))]
            n=rng.randrange(3);radius=[2.5,3.2,4][n];footprint=Point(xy).buffer(radius)
            if not available.covers(footprint) or any(footprint.intersects(p.buffer(1)) for p in source_occupied):continue
            vegetation_instances.append({'id':f'plant-{len(vegetation_instances)}','asset':f'synthetic-tree-{n}',
                'position_m':[*xy,0.0],'rotation_z_deg':rng.uniform(0,360),'placement':'synthetic-park-planting','rt_enabled':False})
            occupied.append(footprint)
    counts=Counter(i['placement'] for i in vegetation_instances)
    summary={'city_size_m':size,'source_terrain_count':sum(r['label']=='terrain' for a in audit for r in a['environment_objects']),
             'source_terrain_all_flat':True,'elevation_range_m':[0,0],
             'source_vegetation_candidates':19,'source_vegetation_retained':counts['preserved-source-group'],
             'source_vegetation_rejected':len(source_candidate_rejections),'synthetic_tree_count':counts['synthetic-park-planting'],
             'terrain_triangles':len(terrain_triangles),'terrain_role_area_m2':{role:shape.area for role,shape,key in classifications},
             'buildings_xy_z_unchanged':scene['instances']==original['instances'],'vegetation_rt_enabled':False,
             'limitations':['No elevation relief exists in downloaded terrain; do not invent source hills',
                            'Boston vegetation objects are simplified 25m volumes with concrete source binding',
                            'Synthetic trees are visual/design geometry; foliage RT model not assigned',
                            'Ground material placement is synthetic design; asphalt source is labelled at 1GHz',
                            'No new channel calculation; original RT trial not attached']}
    # Area disjointness and full coverage checks, above terrain triangles all z0.
    coverage=unary_union([shape for _,shape,_ in classifications])
    assert coverage.symmetric_difference(boundary).area<1e-5
    assert sum(shape.area for _,shape,_ in classifications)-coverage.area<1e-5
    assert all(not p.intersects(building_mask) and p.intersection(road_mask).area<.01 for p in occupied)
    scene['environment']={'terrain':{'vertices':terrain_vertices,'triangles':terrain_triangles,'triangle_material_keys':terrain_keys,'triangle_roles':terrain_roles},
                          'vegetation_assets':vegetation_assets,'vegetation_instances':vegetation_instances,'summary':summary,
                          'source_resource_audit':audit,'source_vegetation_rejections':source_candidate_rejections}
    scene['ground']['material_status']='Partitioned continuous z=0 terrain with explicit design ground materials; no duplicate coplanar road/park RT surfaces.'
    scene['manifest'].update(resource_kind='environment-enhanced',status='Official buildings + audited flat terrain + source vegetation subset + synthetic planting; no foliage RT or new channels.',
                             environment_seed=seed,baseline_sha256=hashlib.sha256(raw).hexdigest(),environment_summary=summary)
    output.mkdir(parents=True,exist_ok=True)
    (output/'assembled-city.scene.json.gz').write_bytes(gzip.compress(json.dumps(scene,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    (output/'assembled-city-manifest.json').write_text(json.dumps(scene['manifest'],ensure_ascii=False,indent=2)+'\n')
    view['manifest']=scene['manifest']
    (output/'assembled-city.view.json').write_text(json.dumps(view,ensure_ascii=False,separators=(',',':')))
    (output/'environment-report.json').write_text(json.dumps({'summary':summary,'source_resource_audit':audit,'source_vegetation_rejections':source_candidate_rejections,
        'qa':{'ground_uncovered_area_m2':coverage.symmetric_difference(boundary).area,'ground_partition_overlap_m2':sum(shape.area for _,shape,_ in classifications)-coverage.area,
              'plant_building_intrusions':0,'plant_road_intrusions':0}},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads',type=Path,default=REPO_ROOT/'data')
    parser.add_argument('--size',type=int,choices=[1000,2000,4000],default=1000)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=args.output or STUDIO_ROOT/f'data/scenes/environment-cities/city-{args.size//1000}km'
    build(args.downloads,output,args.size)


if __name__=='__main__':main()
