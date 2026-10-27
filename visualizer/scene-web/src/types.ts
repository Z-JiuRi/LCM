export type Vec3 = [number, number, number];
export type XY = [number, number];
export type Extent = [number, number, number, number];
export type Footprint = XY[] | { outer: XY[]; holes?: XY[][] };

export interface UESampling {
  count: number;
  spacing_m: number;
  ue_height_m: number;
  building_clearance_m: number;
  vegetation_clearance_m: number;
  positions_url: string;
}

export interface CatalogEntry {
  id: string;
  title: string;
  extent_m: Extent;
  instance_count: number;
  asset_count: number;
  source_count: number;
  data_url: string;
  status: string;
  ue_sampling?: UESampling;
}

export interface SourceMaterial {
  name?: string;
  id?: string | number;
  permittivity?: unknown;
  conductivity?: unknown;
  thickness?: unknown;
  thickness_m?: number;
  source_scene?: string;
  reference_frequency_hz?: number;
  provenance?: unknown;
}

export interface Asset {
  id: string | number;
  faces: Vec3[][];
  height_m: number;
  footprint: Footprint;
  source: unknown;
  source_object_index: number;
  official_object_id?: string | number;
  official_object_index?: number;
  official_object_name?: string;
  face_material_keys?: string[];
  geometry_provenance?: string;
}

export interface Instance {
  id?: string | number;
  asset: string | number;
  position_m: Vec3;
  rotation_z_deg: number;
  parcel: unknown;
  role: string;
}

export interface VegetationAsset {
  id: string;
  faces: Vec3[][];
  height_m: number;
  source: string;
  official_object_id?: number;
  face_material_keys: string[];
  provenance: string;
  rt_status: string;
}

export interface VegetationInstance {
  id: string;
  asset: string;
  position_m: Vec3;
  rotation_z_deg: number;
  placement: string;
  rt_enabled: false;
}

export interface Environment {
  terrain: {
    vertices: Vec3[];
    triangles: number[][];
    triangle_material_keys: string[];
    triangle_roles: string[];
  };
  vegetation_assets: VegetationAsset[];
  vegetation_instances: VegetationInstance[];
}

export interface RadioDeployment {
  sites: {
    id: string;
    position_m: Vec3;
    mount: string;
    planning_reason?: string;
  }[];
  sectors: {
    id: string;
    site_id: string;
    position_m: Vec3;
    azimuth_deg: number;
    downtilt_deg: number;
  }[];
}

export interface CityData {
  assets: Asset[];
  instances: Instance[];
  environment?: Environment;
  radio_deployment?: RadioDeployment;
  roads: { points: XY[]; width_m: number; kind: string }[];
  parks: { outer: XY[]; holes?: XY[][] }[];
  parcels: { id?: string | number; footprint: Footprint; role: string }[];
  ground: { extent_m: Extent; elevation_m: number };
  labels?: [number, number, string][];
  materials?: Record<string, SourceMaterial>;
  source_notice?: string;
}

export interface InspectObject {
  title: string;
  kind: string;
  source: unknown;
  sourceObject: unknown;
  height: number;
  position: Vec3;
  rotation: number;
  parcel: unknown;
  role: string;
  officialObjectId?: string | number;
  officialObjectIndex?: number;
  officialObjectName?: string;
  geometryProvenance?: string;
  placement?: string;
  provenance?: string;
  rtStatus?: string;
  rtEnabled?: false;
  materialRecords?: { key: string; record?: SourceMaterial }[];
  radioPlanning?: {
    reason?: string;
    azimuths: number[];
    downtilts: number[];
  };
}

export type Layer =
  | 'buildings'
  | 'roads'
  | 'parks'
  | 'parcels'
  | 'boundaries'
  | 'grid'
  | 'labels'
  | 'terrain'
  | 'vegetation'
  | 'source_vegetation'
  | 'synthetic_vegetation'
  | 'bs'
  | 'sectors'
  | 'ue';
