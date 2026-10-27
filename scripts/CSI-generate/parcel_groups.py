"""Deterministic actual-map parcel membership, never random train/val/test splits."""
from __future__ import annotations
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from shapely import points
from shapely.geometry import Polygon
from shapely.strtree import STRtree


def parcel_records(scene):
    records=[]
    for i,parcel in enumerate(scene.get('parcels',[])):
        footprint=deepcopy(parcel['footprint'])
        if isinstance(footprint,list):footprint={'outer':footprint,'holes':[]}
        polygon=Polygon(footprint['outer'],footprint.get('holes',[]))
        if polygon.is_empty or not polygon.is_valid or polygon.area<=0:
            raise ValueError(f'Invalid source parcel polygon at index {i}')
        records.append(dict(index=i,id=parcel.get('id',f'parcel-{i:04d}'),role=parcel.get('role','unknown'),
                            footprint=footprint))
    return records


def parcels_from_manifest(manifest):
    if 'parcels' in manifest:return manifest['parcels']
    # Backwards-compatible re-export of already-computed RT, without retracing.
    source=Path(manifest.get('source_scene',''))
    if not source.is_file():raise ValueError('No parcel geometry in manifest; regenerate geometry or provide its original source scene')
    raw=source.read_bytes()
    expected=manifest.get('scene_sha256')
    if not expected or hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('Original scene hash mismatch; refusing uncertain parcel assignment')
    return parcel_records(json.loads(gzip.decompress(raw)))


def assign_parcels(positions,records):
    """Source array order defines stable IDs. Boundary/overlap ties choose first.

    Roads/parks not inside a real parcel remain in an explicit outside group;
    never drop those UEs or invent nearest-parcel membership.
    """
    positions=np.asarray(positions)
    if positions.ndim!=2 or positions.shape[1]!=3 or not np.isfinite(positions).all():
        raise ValueError('Invalid UE positions')
    polygons=[Polygon(p['footprint']['outer'],p['footprint'].get('holes',[])) for p in records]
    if any(p.is_empty or not p.is_valid or p.area<=0 for p in polygons):raise ValueError('Invalid parcel geometry')
    outside=len(records);labels=np.full(len(positions),outside,dtype=np.int32)
    matches=np.zeros(len(positions),np.int32)
    if polygons:
        tree=STRtree(polygons)
        for start in range(0,len(positions),20000):
            queries=points(positions[start:start+20000,:2])
            point_idx,polygon_idx=tree.query(queries,predicate='covered_by')
            np.minimum.at(labels,start+point_idx,polygon_idx)
            np.add.at(matches,start+point_idx,1)
    catalog=[dict(p,group_index=i,directory=f'parcel-{i:04d}',kind='parcel') for i,p in enumerate(records)]
    catalog.append(dict(group_index=outside,index=None,id='outside-parcels',role='roads/parks/unassigned',
                        directory='outside-parcels',kind='outside',footprint=None))
    for item in catalog:item['ue_count']=int(np.count_nonzero(labels==item['group_index']))
    return labels,dict(schema_version=1,grouping='actual_scene_parcels',groups=catalog,
        ue_count=len(positions),multiple_membership_ues=int(np.count_nonzero(matches>1)),
        boundary_policy='Polygon covers includes boundary; multiple matches use lowest source parcel index.',
        outside_policy='Keep every UE outside actual parcel polygons in outside-parcels; no nearest assignment.',
        split_policy='No train/val/test partition. All UEs of a parcel stay together, including unusable links.')
