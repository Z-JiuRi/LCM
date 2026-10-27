#!/usr/bin/env python3
"""Re-export completed CSI by actual parcels, without ray tracing or copying raw paths."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import generate_city_csi as G
from parcel_groups import assign_parcels,parcels_from_manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True,help='Completed generation directory containing report.json')
    p.add_argument('--output',type=Path,required=True,help='New directory; raw sector data stays in source')
    args=p.parse_args(argv);source=args.source.resolve();output=args.output.resolve()
    if output.exists():p.error('Output exists; choose a new directory')
    report=json.loads((source/'report.json').read_text())
    if report.get('status')!='complete':p.error('Source generation is not complete')
    positions=np.load(source/'ue_positions.npy',allow_pickle=False)
    source_indices=np.load(source/'source_ue_indices.npy',allow_pickle=False)
    labels,catalog=assign_parcels(positions,parcels_from_manifest(report['geometry_manifest']))
    results=report['raw_sectors']
    for result in results:
        folder=Path(result['folder']).resolve()
        if not folder.is_relative_to(source) or not (folder/'csi.npy').is_file() or not (folder/'link_stats.npz').is_file():
            p.error('Invalid source sector path')
    G.require_disk_space(output,positions.shape[0]*report['config']['num_antennas']*report['config']['n_sc']*16,0)
    output.mkdir(parents=True,exist_ok=False)
    np.save(output/'ue_positions.npy',positions);np.save(output/'source_ue_indices.npy',source_indices)
    np.save(output/'ue_parcel_index.npy',labels);G.write_json(output/'parcel-catalog.json',catalog)
    new=dict(status='running',schema_version=3,grouping='actual_scene_parcels',source_run=str(source),
             source_report_sha256=G.sha256(source/'report.json'),config=report['config'],
             geometry_manifest=report['geometry_manifest'],parcel_catalog=catalog,
             note='CPU-only re-export; all source RT paths and per-sector CFR remain at source_run, not copied or modified.')
    G.write_json(output/'report.json',new)
    try:
        counts=G.export_feedback(output,results,positions,report['config'])
        new.update(status='complete',counts=counts)
    except BaseException as exc:
        new.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        G.write_json(output/'report.json',new);raise
    G.write_json(output/'report.json',new)
    print(json.dumps(dict(output=str(output),ue_count=len(positions),usable_count=counts['feedback_samples'],
                          groups=len(counts['parcel_groups']),grouping=counts['grouping']),ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
