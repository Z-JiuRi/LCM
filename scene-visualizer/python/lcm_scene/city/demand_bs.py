"""Synthetic land-use demand planning; distances/budgets are NOT RF predictions."""
from collections import Counter
import math
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely.prepared import prep
from .deploy_bs import footprint

TIMES = ('weekday_day', 'weekday_evening', 'weekend')
# (residential floor share, residential presence, employment presence).
# All entries below are project scenario assumptions, NOT measured land uses.
PROFILES = {
    'lowrise': (.90, [.40,.95,.80], [.90,.10,.15]),
    'fine': (.75, [.45,.90,.80], [.95,.20,.35]),
    'midrise': (.80, [.40,.95,.80], [.95,.15,.20]),
    'towers': (.65, [.40,.95,.80], [.95,.15,.20]),
    'mixed': (.45, [.50,.90,.80], [.95,.45,.65]),
    'core': (.15, [.45,.90,.75], [.95,.25,.35]),
    'secondary': (.20, [.45,.90,.75], [.95,.25,.40]),
    'campus': (.25, [.45,.90,.70], [.90,.30,.20]),
    'employment': (.05, [.40,.90,.75], [.95,.10,.15]),
}
ASSUMPTIONS = {
    'status': 'Synthetic planning assumptions, not measured population or verified building functions',
    'grid_size_m': 50, 'floor_height_m': 3.3, 'usable_floor_fraction': .70,
    'residential_usable_m2_per_person': 35, 'employment_usable_m2_per_person': 20,
    'operator_share': .30, 'connected_devices_per_person': 1.0,
    'building_activity_fraction': [.12,.15,.14], 'outdoor_activity_fraction': [.18,.22,.20],
    'active_ue_demand_mbps': 2.0,
    'park_present_people_per_km2': [600,1200,2200],
    'road_present_people_per_km2': [200,300,250],
    'other_open_present_people_per_km2': [80,100,120],
    'indoor_building_demand_included': True,
    'building_traffic_fraction_assigned_to_outdoor_network': .35,
    'indoor_service_solution_validated': False,
    'service_split_note': '35% of building traffic assigned to outdoor BS planning as an explicit scenario assumption; remaining 65% requires a separate indoor/WiFi solution and is NOT claimed served. All park/road/open demand assigned to outdoor network.',
    'population_method': 'Each building footprint * max(1,floor(height/3.3)) * 0.70; split residential/employment floor shares; disjoint floor areas, then time presence factors. Visitors represented only by outdoor area densities, not a second indoor population.',
    'uncertainty_multipliers': {'low': .5, 'medium': 1., 'high': 1.5},
    'role_profiles': {r: {'residential_floor_share': p[0], 'resident_presence': p[1], 'employment_presence': p[2]} for r,p in PROFILES.items()},
}


def demand_grid(scene, size, building_shapes):
    """Aggregate expected counts, not physical RX positions, into nonoverlapping cells."""
    step = ASSUMPTIONS['grid_size_m']; n = math.ceil(size/step)
    cells = []
    for y in range(n):
        for x in range(n):
            cells.append({'id': f'D-{x}-{y}', 'position_m': [(x+.5)*step,(y+.5)*step],
                          'area_m2': step*step, 'role_present': {}, 'building_count': 0,
                          'present': np.zeros(3), 'active': np.zeros(3), 'outdoor_active': np.zeros(3)})
    def add(index, role, present, activity, outdoor_fraction=1.):
        cell=cells[index]; present=np.asarray(present,float)
        cell['present'] += present
        active = present * ASSUMPTIONS['operator_share'] * np.asarray(activity)
        cell['active'] += active
        cell['outdoor_active'] += active * outdoor_fraction
        cell['role_present'].setdefault(role,np.zeros(3))
        cell['role_present'][role] += present
    assets={a['id']:a for a in scene['assets']}
    regions=[]
    for i,(instance,shape) in enumerate(zip(scene['instances'],building_shapes)):
        asset=assets[instance['asset']]; role=instance['role']
        if role not in PROFILES: raise ValueError(f'Unmapped role: {role}')
        share,res,work=PROFILES[role]
        floors=max(1,math.floor(asset['height_m']/ASSUMPTIONS['floor_height_m']))
        usable=shape.area*floors*ASSUMPTIONS['usable_floor_fraction']
        residents=usable*share/ASSUMPTIONS['residential_usable_m2_per_person']
        jobs=usable*(1-share)/ASSUMPTIONS['employment_usable_m2_per_person']
        population=residents*np.asarray(res)+jobs*np.asarray(work)
        # Distribute by footprint-cell intersection rather than treating centroids
        # as outdoor UE locations. Tall buildings keep their role/height demand.
        minx,miny,maxx,maxy=shape.bounds
        pieces=[]
        for y in range(max(0,int(miny//step)),min(n,int(maxy//step)+1)):
            for x in range(max(0,int(minx//step)),min(n,int(maxx//step)+1)):
                area=shape.intersection(box(x*step,y*step,(x+1)*step,(y+1)*step)).area
                if area>1e-8: pieces.append((y*n+x,area))
        total=sum(a for _,a in pieces)
        if total<=0: raise ValueError(f'Building outside demand grid: {i}')
        for index,area in pieces:
            add(index,role,population*area/total,ASSUMPTIONS['building_activity_fraction'],
                ASSUMPTIONS['building_traffic_fraction_assigned_to_outdoor_network'])
            cells[index]['building_count']+=1
        regions.append({'instance_index':i,'parcel':instance.get('parcel'),'role':role,
                        'estimated_floors':floors,'usable_floor_area_m2':usable,
                        'resident_capacity':residents,'employment_capacity':jobs,
                        'present_population':dict(zip(TIMES,population.tolist()))})
    boundary=box(0,0,size,size)
    buildings=unary_union(building_shapes)
    roads=unary_union([LineString(r['points']).buffer(r['width_m']/2,cap_style=2) for r in scene['roads']]).intersection(boundary).difference(buildings)
    parks=unary_union([Polygon(p['outer'],p.get('holes',[])) for p in scene['parks']]).intersection(boundary).difference(buildings).difference(roads)
    masks=[('park',parks),('road',roads),('open',boundary.difference(buildings).difference(roads).difference(parks))]
    for index,cell in enumerate(cells):
        x,y=cell['position_m']; tile=box(x-step/2,y-step/2,x+step/2,y+step/2)
        for role,mask in masks:
            area=mask.intersection(tile).area
            density=ASSUMPTIONS[f'{"other_open" if role=="open" else role}_present_people_per_km2']
            add(index,role,np.asarray(density)*area/1e6,ASSUMPTIONS['outdoor_activity_fraction'])
    summary={}
    for t,name in enumerate(TIMES):
        pop=sum(c['present'][t] for c in cells); active=sum(c['active'][t] for c in cells)
        outdoor=sum(c['outdoor_active'][t] for c in cells)
        summary[name]={'present_population':pop,'operator_ues':pop*ASSUMPTIONS['operator_share'],
                       'active_ues':active,'demand_mbps':active*ASSUMPTIONS['active_ue_demand_mbps'],
                       'outdoor_network_active_ues':outdoor,'outdoor_network_demand_mbps':outdoor*ASSUMPTIONS['active_ue_demand_mbps'],
                       'pending_indoor_active_ues':active-outdoor,'pending_indoor_demand_mbps':(active-outdoor)*ASSUMPTIONS['active_ue_demand_mbps']}
    for c in cells:
        c['dominant_role']=max(c['role_present'],key=lambda r: max(c['role_present'][r]))
        c['scenarios']={name:{'present_population':float(c['present'][t]),'operator_ues':float(c['present'][t]*ASSUMPTIONS['operator_share']),
                      'active_ues':float(c['active'][t]),'demand_mbps':float(c['active'][t]*ASSUMPTIONS['active_ue_demand_mbps']),
                      'outdoor_network_active_ues':float(c['outdoor_active'][t]),
                      'outdoor_network_demand_mbps':float(c['outdoor_active'][t]*ASSUMPTIONS['active_ue_demand_mbps']),
                      'pending_indoor_active_ues':float(c['active'][t]-c['outdoor_active'][t]),
                      'pending_indoor_demand_mbps':float((c['active'][t]-c['outdoor_active'][t])*ASSUMPTIONS['active_ue_demand_mbps'])} for t,name in enumerate(TIMES)}
        del c['present'],c['active'],c['outdoor_active']
        c['role_present']={r:dict(zip(TIMES,p.tolist())) for r,p in c['role_present'].items()}
    return {'assumptions':ASSUMPTIONS,'cell_count':len(cells),'cells':cells,'building_estimates':regions,
            'summary':summary,'ue_positions_generated':False,
            'spatial_semantics':'Cell centers are demand aggregation/nearest-site planning probes, may lie indoors; NOT physical RX positions or simultaneous scheduled UEs.'}, roads


def plan_sites(xy, traffic, candidates, size, isd=500, budget=600):
    """500m soft prior, demand-weighted relocation, spatial/load repairs, deletion.

    Nearest-site assignment and an assumed aggregate site budget are only a
    planning proxy. No path loss, indoor penetration, sectors or interference.
    """
    radius=isd*.70; minimum=isd*.30
    ctree=cKDTree(candidates); sites=[]; reasons=[]; nominal=[]
    def feasible(q,exclude=None):
        return all(i==exclude or np.linalg.norm(q-p)>=minimum-1e-7 for i,p in enumerate(sites))
    # Triangular initialization is explicitly NOT a fixed output spacing.
    row=0
    for y in np.arange(isd/2,size,isd*math.sqrt(3)/2):
        for x in np.arange(isd/2+(row%2)*isd/2,size,isd):
            target=np.array([x,y]); _,idx=ctree.query(target,k=min(120,len(candidates)))
            q=next((candidates[j] for j in np.atleast_1d(idx) if feasible(candidates[j])),None)
            if q is not None: sites.append(q.copy());reasons.append('基础覆盖：500m参考尺度初始化，经需求加权调整');nominal.append(target)
        row+=1
    weights=traffic.max(axis=1)+max(float(traffic.mean()),.01)*.15
    # Demand-aware relocation, with a soft regularizer to the initialization.
    for _ in range(3):
        _,owner=cKDTree(sites).query(xy)
        for i,p in enumerate(sites):
            mask=owner==i
            if not mask.any(): continue
            center=np.average(xy[mask],axis=0,weights=weights[mask])*.8+nominal[i]*.2
            _,ids=ctree.query(center,k=min(80,len(candidates)))
            q=next((candidates[j] for j in np.atleast_1d(ids) if np.linalg.norm(candidates[j]-nominal[i])<=isd*.35 and feasible(candidates[j],i)),None)
            if q is not None: sites[i]=q.copy()
    def evaluate(points):
        distance,owner=cKDTree(points).query(xy)
        loads=np.array([np.bincount(owner,weights=traffic[:,t],minlength=len(points)) for t in range(3)]).T
        return distance,owner,loads
    def refine():
        """Coordinate search can rebalance a hotspot without adding another site."""
        moved=False
        for _ in range(2):
            changed=False
            for i in range(len(sites)):
                others=sites[:i]+sites[i+1:]
                if not others: continue
                other_dist,other_owner=cKDTree(others).query(xy)
                other_loads=np.array([np.bincount(other_owner,weights=traffic[:,t],minlength=len(others)) for t in range(3)]).T
                def score(q):
                    d=np.linalg.norm(xy-q,axis=1); steal=d<other_dist
                    l=other_loads.copy()
                    for t in range(3):l[:,t]-=np.bincount(other_owner[steal],weights=traffic[steal,t],minlength=len(others))
                    l=np.vstack([l,traffic[steal].sum(axis=0)])
                    near=np.minimum(d,other_dist)
                    return (float(np.maximum(near-radius,0).sum()/radius + np.maximum(l-budget,0).sum()/budget),
                            float(np.average(near,weights=weights)))
                best=sites[i]; best_score=score(best)
                _,pool=ctree.query(best,k=min(100,len(candidates)))
                for j in np.atleast_1d(pool):
                    q=candidates[j]
                    if not feasible(q,i) or np.linalg.norm(q-nominal[i])>isd*.4:continue
                    candidate_score=score(q)
                    if candidate_score<best_score:best=q;best_score=candidate_score
                if np.linalg.norm(best-sites[i])>1e-6:sites[i]=best.copy();changed=True;moved=True
            if not changed:break
        return moved
    refine()
    repairs=[]
    for iteration in range(500):
        distance,owner,loads=evaluate(sites)
        if distance.max()<=radius+1e-7 and loads.max()<=budget+1e-7: break
        spatial=distance.max()>radius+1e-7
        if spatial:
            target=xy[np.argmax(distance)]
            reason='空间补点：需求网格到最近站超过规划距离阈值（非RF覆盖盲区判定）'
            pool=ctree.query(target,k=min(160,len(candidates)))[1]
        else:
            overloaded=int(np.argmax(loads.max(axis=1))); mask=owner==overloaded
            center=np.average(xy[mask],axis=0,weights=weights[mask])
            pool=ctree.query(center,k=min(180,len(candidates)))[1]
            reason='需求补点：分时需求超过假设单站预算（非实测容量不足）'
        best=None; best_score=None
        old_over=float(np.maximum(loads-budget,0).sum())
        old_excess=float(np.maximum(distance-radius,0).sum())
        def search(indices):
            best=None; best_score=None
            for j in np.atleast_1d(indices):
                q=candidates[j]
                if not feasible(q):continue
                d=np.linalg.norm(xy-q,axis=1); steal=d<distance
                if not steal.any():continue
                newloads=loads.copy()
                for t in range(3):newloads[:,t]-=np.bincount(owner[steal],weights=traffic[steal,t],minlength=len(sites))
                newloads=np.vstack([newloads,traffic[steal].sum(axis=0)])
                near=np.minimum(d,distance)
                excess=float(np.maximum(near-radius,0).sum())
                over=float(np.maximum(newloads-budget,0).sum())
                score=(excess if spatial else over, over if spatial else excess, float(np.average(near,weights=weights)))
                if best_score is None or score<best_score:best_score=score;best=q
            return best,best_score
        best,best_score=search(pool)
        if best is None or best_score[0]>=(old_excess if spatial else old_over)-1e-6:
            # A local failure is not evidence the city is infeasible. Scan the
            # entire feasible candidate set before reporting a heuristic stall.
            best,best_score=search(range(len(candidates)))
        if best is None or (spatial and best_score[0]>=old_excess-1e-6) or (not spatial and best_score[0]>=old_over-1e-6):
            if refine():
                d,_,l=evaluate(sites)
                if np.maximum(d-radius,0).sum()<old_excess-1e-6 or np.maximum(l-budget,0).sum()<old_over-1e-6:
                    continue
            repairs.append({'status':'unresolved','reason':reason,'target_m':target.tolist() if spatial else center.tolist()});break
        sites.append(best.copy());nominal.append(best.copy());reasons.append(reason)
    # Remove redundant/light sites only when all time slices and spatial probes
    # remain within the planning thresholds. Re-check after every deletion.
    removed=0
    changed=True
    while changed and len(sites)>1:
        changed=False
        _,_,loads=evaluate(sites)
        for i in np.argsort(loads.max(axis=1)):
            trial=sites[:i]+sites[i+1:]
            d,_,l=evaluate(trial)
            if d.max()<=radius+1e-7 and l.max()<=budget+1e-7:
                sites.pop(i);nominal.pop(i);reasons.pop(i);removed+=1;changed=True;break
    distance,owner,loads=evaluate(sites)
    return np.asarray(sites),nominal,reasons,distance,owner,loads,{
        'distance_target_m':radius,'site_budget_mbps':budget,'minimum_neighbor_floor_m':minimum,
        'spatial_max_distance_m':float(distance.max()),'spatial_p95_distance_m':float(np.percentile(distance,95)),
        'max_assigned_demand_mbps':float(loads.max()),'constraints_satisfied':bool(distance.max()<=radius+1e-7 and loads.max()<=budget+1e-7),
        'unresolved':repairs,'redundant_sites_removed':removed,
        'meaning':'Euclidean distance to 50m cell centers and assumed site budget under nearest-site association. NOT RF coverage/capacity. Only assumed outdoor-network share is constrained; pending indoor demand NOT served or validated.',
        'constraint_scope':'outdoor-network assumed traffic only, not full city demand'}


def build_plan(scene,size,isd=500):
    if not math.isfinite(isd) or isd!=500:raise ValueError('This land-use scenario requires the 500m soft reference')
    if size not in [1000,2000,4000]:raise ValueError('Supported city sizes are 1000, 2000, 4000m')
    assets={a['id']:a for a in scene['assets']}
    shapes=[footprint(assets[i['asset']],i) for i in scene['instances']]
    buildings=unary_union(shapes)
    plants={a['id']:a for a in scene['environment']['vegetation_assets']}
    vegetation=unary_union([footprint(plants[i['asset']],i) for i in scene['environment']['vegetation_instances']])
    demand,roads=demand_grid(scene,size,shapes)
    allowed=box(8,8,size-8,size-8).difference(unary_union([buildings.buffer(4),vegetation.buffer(3),roads.buffer(1)]))
    ready=prep(allowed)
    # Fine-grained candidates, staggered to avoid regular final lattice. Add
    # geometry-derived representative points so narrow clear pockets are kept.
    candidates=[]
    for row,y in enumerate(np.arange(12,size-8,25)):
        for x in np.arange(12+(row%2)*12.5,size-8,25):
            if ready.covers(Point(x,y)):candidates.append([x,y])
    for p in getattr(allowed,'geoms',[allowed]):
        q=p.representative_point()
        if ready.covers(q):candidates.append([q.x,q.y])
    candidates=np.unique(np.round(candidates,6),axis=0)
    if len(candidates)==0:raise ValueError('No feasible ground site candidates')
    xy=np.array([c['position_m'] for c in demand['cells']])
    traffic=np.array([[c['scenarios'][t]['outdoor_network_demand_mbps'] for t in TIMES] for c in demand['cells']])
    points,nominal,reasons,distance,owner,loads,proxy=plan_sites(xy,traffic,candidates,size,isd)
    sites=[];sectors=[]
    for i,q in enumerate(points):
        sid=f'BS-{size//1000}K-{i+1:03d}';mask=owner==i;ids=[f'{sid}-S{k+1}' for k in range(3)]
        roles=Counter()
        for j in np.where(mask)[0]:
            for role,present in demand['cells'][j]['role_present'].items():roles[role]+=max(present.values())
        direction=(xy[mask]-q)*traffic[mask].max(axis=1)[:,None]
        delta=direction.sum(axis=0)
        az=float(math.degrees(math.atan2(delta[1],delta[0]))%120) if np.linalg.norm(delta)>1e-8 else 0.
        assignments={t:float(loads[i,k]) for k,t in enumerate(TIMES)}
        site={'id':sid,'position_m':[float(q[0]),float(q[1]),25.], 'ground_elevation_m':0.,'mount':'ground-pole',
              'nominal_position_m':[*map(float,nominal[i]),25.], 'relocation_m':float(np.linalg.norm(q-nominal[i])),
              'clearance_m':float(min(buildings.distance(Point(q)),vegetation.distance(Point(q)))),
              'road_clearance_m':float(roads.distance(Point(q))), 'sector_ids':ids,
              'planning_reason':reasons[i],'served_region_roles':[r for r,_ in roles.most_common()],
              'planning_peak_active_ues':float(loads[i].max()/ASSUMPTIONS['active_ue_demand_mbps']),
              'planning_peak_demand_mbps':float(loads[i].max()),'planning_demand_by_time_mbps':assignments,
              'planning_radius_m':float(distance[mask].max()) if mask.any() else 0.,
              'provenance':'New synthetic city demand-aware site plan; no source BS copied; not operator deployment.'}
        sites.append(site)
        for k in range(3):
            sectors.append({'id':ids[k],'site_id':sid,'position_m':site['position_m'],'azimuth_deg':round((az+120*k)%360,6),
                            'azimuth_convention':'Counterclockwise from east in local XY; not bearing from north.',
                            'downtilt_deg':10,'antenna_model':'planned-sector-not-yet-RT','carrier_frequency_hz':3.5e9,
                            'status':'Orientation metadata rotated toward aggregate demand; no radiation pattern, power, per-sector load or RT mapping.'})
    for j,c in enumerate(demand['cells']):c.update(planning_site_id=sites[int(owner[j])]['id'],planning_distance_m=float(distance[j]))
    nn=cKDTree(points).query(points,k=2)[0][:,1] if len(points)>1 else np.array([0.])
    sensitivity={}
    for name,multiplier in ASSUMPTIONS['uncertainty_multipliers'].items():
        sensitivity[name]={'demand_multiplier':multiplier,'max_assigned_demand_mbps':float(loads.max()*multiplier),
                           'sites_above_assumed_budget':int(np.sum((loads*multiplier).max(axis=1)>proxy['site_budget_mbps'])),
                           'note':'Fixed-layout demand sensitivity, not a separate optimized deployment or RF validation.'}
    full_traffic=np.array([[c['scenarios'][t]['demand_mbps'] for t in TIMES] for c in demand['cells']])
    full_load=np.array([np.bincount(owner,weights=full_traffic[:,t],minlength=len(sites)) for t in range(3)]).T
    sensitivity['all_building_traffic_to_outdoor']={'max_assigned_demand_mbps':float(full_load.max()),
        'sites_above_assumed_budget':int(np.sum(full_load.max(axis=1)>proxy['site_budget_mbps'])),
        'note':'Same layout with 100% building traffic assigned to outdoor BS; no indoor offload assumed; not a separate optimized plan.'}
    summary={'city_size_m':size,'strategy':'land-use-demand-500m','nominal_isd_m':isd,
             'site_count':len(sites),'sector_count':len(sectors),'installation_height_agl_m':25,
             'nearest_neighbor_m':{'min':float(nn.min()),'median':float(np.median(nn)),'max':float(nn.max())},
             'max_relocation_m':max(s['relocation_m'] for s in sites),'candidate_count':len(candidates),
             'coverage_validated':False,'capacity_validated':False,'full_city_demand_served':False,
             'planning_status':'outdoor-proxy-satisfied-indoor-pending' if proxy['constraints_satisfied'] else 'partial-outdoor-proxy-unresolved-indoor-pending',
             'demand_summary':demand['summary'],
             'planning_proxy':proxy,'fixed_layout_sensitivity':sensitivity,
             'limitations':['All UE/population/traffic values are synthetic expectations, not measured counts; land uses are assigned roles.',
                '500m is a soft initialization scale, not mandatory spacing or a standard requirement.',
                'No UE/RX positions, trajectories, scheduling, power, antenna pattern, SINR, throughput or new RT computed.',
                '600Mbps/site is an assumed planning budget, NOT a predicted radio capacity.',
                'Euclidean nearest-site association ignores blockage/indoor penetration/interference; indoor provision remains unresolved.',
                '25m poles need not be above nearby roofs; physical permissions/power/backhaul unvalidated.',
                'No external neighbor sites or boundary interference; high demand may exceed the fixed-layout budget.']}
    return {'sites':sites,'sectors':sectors,'summary':summary,'demand_model':demand}
