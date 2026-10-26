"""Match official DeepMIMO objects to frozen preview assets without moving instances."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from scipy.spatial import cKDTree
from shapely.geometry import Polygon
from shapely.ops import unary_union
from ..paths import REPO_ROOT,STUDIO_ROOT,city_directory
from .validate_city_variants import validate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source(folder):
    objs=json.loads((folder/'objects.json').read_text())
    params=json.loads((folder/'params.json').read_text())
    vertex_paths=list(folder.glob('vertices.*'))
    assert len(vertex_paths)==1,folder
    path=vertex_paths[0]
    if path.suffix=='.mat':
        vertices=loadmat(path)['vertices']
    else:
        with np.load(path,allow_pickle=False) as z:vertices=z['vertices']
    vertices=np.asarray(vertices,dtype=np.float64)
    assert vertices.ndim==2 and vertices.shape[1]==3 and np.isfinite(vertices).all()
    candidates=[]
    for index,obj in enumerate(objs):
        if obj.get('label')!='buildings':continue
        faces=[]
        for ring in obj['face_vertex_idxs']:
            indices=np.asarray(ring,dtype=int)
            assert (indices>=0).all() and (indices<len(vertices)).all()
            faces.append(vertices[indices])
        points=np.unique(np.concatenate(faces),axis=0)
        materials=obj.get('face_material_idxs',[])
        assert len(materials)==len(faces),obj['name']
        candidates.append({'index':index,'object':obj,'faces':faces,'points':points,'center':points.mean(0),'tree':cKDTree(points)})
    return candidates,params,{name:digest(folder/name) for name in ['objects.json','params.json',path.name]}


def match(asset,candidates,tolerance=.002):
    points=np.unique(np.concatenate(asset['faces'])+np.asarray(asset['source_origin_m']),axis=0)
    tree=cKDTree(points)
    matches=[]
    for c in candidates:
        if np.linalg.norm(points.mean(0)-c['center'])>tolerance*2:continue
        error=max(c['tree'].query(points)[0].max(),tree.query(c['points'])[0].max())
        if error<=tolerance:matches.append((float(error),c))
    if not matches:raise ValueError(f'No official object matches asset {asset["id"]} / {asset["source"]}')
    # Prefer the previous index ONLY after independent geometric validation.
    # API indices alone are never accepted as proof of object identity.
    matches.sort(key=lambda x:(x[1]['index']!=asset['source_object_index'],x[0],x[1]['index']))
    # Multiple objects may be exact geometry duplicates; require identical
    # face/material structure before choosing a canonical representative.
    chosen=matches[0][1]
    if len(matches)>1:
        reference=chosen['object']['face_material_idxs']
        if any(c['object']['face_material_idxs']!=reference or len(c['faces'])!=len(chosen['faces']) or any(a.shape!=b.shape or not np.allclose(a,b,rtol=0,atol=tolerance) for a,b in zip(c['faces'],chosen['faces'])) for _,c in matches):
            raise ValueError(f'Ambiguous geometry/material mapping asset {asset["id"]}')
    return chosen,matches[0][0],[c['object']['id'] for _,c in matches]


def integrate(size,downloads,output_root,sources):
    folder=city_directory(size)
    source=folder/'assembled-city.scene.json.gz'
    original=json.loads(gzip.decompress(source.read_bytes()))
    scene=deepcopy(original)
    mapping=[]
    materials={}
    metadata={}
    max_delta=0
    for asset in scene['assets']:
        name=asset['source']
        candidates,params,hashes=sources[name]
        obj,error,duplicates=match(asset,candidates)
        official=obj['object']
        old_faces=asset['faces']
        local=[(face-np.asarray(asset['source_origin_m'])).tolist() for face in obj['faces']]
        assert len(local)==len(old_faces) and all(np.asarray(a).shape==np.asarray(b).shape and np.allclose(a,b,rtol=0,atol=.002) for a,b in zip(local,old_faces)), ('Ordered face topology mismatch',asset['id'])
        # Old footprint stays authoritative for parcel placement; verify official
        # horizontal surfaces have the same projected shape within rounding.
        projected=[Polygon(np.asarray(f)[:,:2]) for f in local if Polygon(np.asarray(f)[:,:2]).is_valid and Polygon(np.asarray(f)[:,:2]).area>.1]
        shape=unary_union(projected)
        old_shape=Polygon(asset['footprint']['outer'],asset['footprint']['holes'])
        area_delta=shape.symmetric_difference(old_shape).area
        assert area_delta<.2,(asset['id'],area_delta)
        max_delta=max(max_delta,area_delta)
        keys=[]
        source_materials=params.get('materials',{})
        for material_id in official['face_material_idxs']:
            choices=[(k,v) for k,v in source_materials.items() if v.get('id')==material_id]
            assert len(choices)==1,(name,material_id)
            key,record=choices[0]
            qualified=f'{name}:{key}'
            materials[qualified]={**record,'source_scene':name,'reference_frequency_hz':params.get('rt_params',{}).get('frequency'),
                                  'provenance':'Downloaded official params.json; raw source semantics retained, no Sionna translation validated.'}
            keys.append(qualified)
        asset.update(faces=local,official_object_id=official['id'],official_object_index=obj['index'],
                     official_object_name=official['name'],face_material_keys=keys,
                     geometry_provenance='official-archive-matched',official_match_error_m=error,
                     official_geometry_duplicate_ids=duplicates)
        metadata[name]={'version':params.get('version'),'file_sha256':hashes,'source_folder':str((downloads/name).resolve()),
                        'reference_frequency_hz':params.get('rt_params',{}).get('frequency'),
                        'source_rt_params':params.get('rt_params',{}),'source_scene_metadata':params.get('scene',{}),
                        'excluded':'Original terrain, vegetation, TX/RX sets and original channel arrays are not imported into merged layout.'}
        mapping.append({'asset_id':asset['id'],'source':name,'preview_object_index':asset['source_object_index'],
                        'official_object_id':official['id'],'official_object_index':obj['index'],
                        'vertex_hausdorff_error_m':error,'footprint_symmetric_difference_m2':area_delta,
                        'equivalent_geometry_object_ids':duplicates})
    assert scene['instances']==original['instances']
    for key in ['roads','parks','parcels','ground','green_path']:
        assert scene[key]==original[key]
    scene['materials']=materials
    scene['source_metadata']=metadata
    scene['ground']['material_status']='Synthetic ground; source terrain/material not transplanted. Requires explicit new-city material assignment.'
    manifest=scene['manifest']
    manifest.update(status='Official archive geometry matched into synthetic city layout; source face materials retained, no new RT/channel validation.',
                    resource_kind='official-integrated',integration_date=datetime.now(timezone.utc).isoformat(),
                    preview_snapshot_sha256=digest(source),official_matched_asset_count=len(mapping),official_material_count=len(materials),
                    official_match_max_vertex_error_m=max(m['vertex_hausdorff_error_m'] for m in mapping),
                    official_match_tolerance_m=.002,
                    channel_status='Not recomputed. Earlier 1km trial used preview/assumed materials and is not attached to this resource version.')
    # Ground status is the only intentional extra synthetic-ground field.
    target=output_root/f'city-{size//1000}km'
    target.mkdir(parents=True,exist_ok=True)
    payload=gzip.compress(json.dumps(scene,ensure_ascii=False,separators=(',',':')).encode(),mtime=0)
    (target/'assembled-city.scene.json.gz').write_bytes(payload)
    (target/'assembled-city-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    view=json.loads((folder/'assembled-city.view.json').read_text())
    view['manifest']=manifest
    (target/'assembled-city.view.json').write_text(json.dumps(view,ensure_ascii=False,separators=(',',':')))
    qa=validate(target)
    report={'city_size_m':size,'matched_assets':len(mapping),'instances':len(scene['instances']),
            'source_count':len(metadata),'material_count':len(materials),'max_footprint_area_difference_m2':max_delta,
            'layout_instances_unchanged':True,'synthetic_layout_unchanged':True,'mapping':mapping,
            'validation':qa,'scope':'Geometry matching and source face-material association; not source license approval, RT material conversion or new channel calculation.'}
    (target/'integration-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('INTEGRATED',size,len(mapping),'assets',len(scene['instances']),'instances',len(materials),'materials',flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads',type=Path,default=REPO_ROOT/'data')
    parser.add_argument('--output',type=Path,default=STUDIO_ROOT/'data/scenes/official-cities')
    args=parser.parse_args()
    names=set()
    for size in [1000,2000,4000]:
        names.update(json.loads((city_directory(size)/'assembled-city-manifest.json').read_text())['source_usage'])
    plan_path=args.downloads/'download-plan.json'
    plan=json.loads(plan_path.read_text())
    sources={}
    for name in sorted(names):
        row=plan['scenes'][name]
        for filename,expected in row.get('sha256',{}).items():
            assert digest(args.downloads/name/filename)==expected,(name,filename)
        candidates,params,hashes=load_source(args.downloads/name)
        sources[name]=(candidates,params,hashes)
    reports=[integrate(size,args.downloads,args.output,sources) for size in [1000,2000,4000]]
    summary={'source_count':len(names),'downloaded_bytes':sum((args.downloads/name/file).stat().st_size for name in names for file in sources[name][2]),
             'cities':[{k:v for k,v in report.items() if k!='mapping'} for report in reports]}
    (args.output/'integration-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
