import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Vec3, XY, Footprint, CatalogEntry, CityData, Instance, Environment, VegetationInstance, SourceMaterial, InspectObject, Layer, RTBatch, RTCoverage } from './types';

// Match the reference mechanisms without assigning a mixed path to only one bounce.
const rtColors: Record<number, number> = { 1: 0xe53935, 2: 0x1976ed, 4: 0x9755ca, 8: 0xf48b16 };
const rtNeutral = 0x526674;
const rtTX = 0xc32391;
const rtRX = 0x008b66;
const validRTPoint = (p: unknown): p is Vec3 => Array.isArray(p) && p.length === 3 && p.every(v => typeof v === 'number' && Number.isFinite(v));
const rtCoverageColor = (t: number) => new THREE.Color(`hsl(${(1 - t) * 240}, 88%, 50%)`);

/** Validate before drawing; never quietly skip malformed or weak paths. */
export function measureRTBatch(batch: RTBatch) {
    if (!Array.isArray(batch.rays) || !validRTPoint(batch.tx_position) || !Array.isArray(batch.rx_positions) || !batch.rx_positions.every(validRTPoint))
        throw new Error('RT 批次的 TX / RX 坐标或路径数组无效');
    let segments = 0, interactions = 0;
    for (const ray of batch.rays) {
        if (!Array.isArray(ray.points) || ray.points.length < 2 || !ray.points.every(validRTPoint) || !Array.isArray(ray.interactions) || ray.interactions.length !== ray.points.length - 2 || !ray.interactions.every(v => Number.isSafeInteger(v) && v >= 0))
            throw new Error('RT 路径坐标 / 交互点不匹配；该批次未绘制');
        segments += ray.points.length - 1;
        interactions += ray.interactions.length;
    }
    // Conservative display estimate: CPU + GPU attributes and marker bookkeeping.
    const displayBytes = (segments * 48 + interactions * 24 + (batch.rx_positions.length + 1) * 128) * 2;
    return { segments, interactions, displayBytes };
}

const outer = (p: Footprint) => Array.isArray(p) ? p : p.outer;
const holes = (p: Footprint) => Array.isArray(p) ? [] : p.holes ?? [];
const point = ([x, y, z]: Vec3) => new THREE.Vector3(x, z, -y);
/** Newell normal selects a stable projection for concave, arbitrary planar source faces. */
export function triangulateFaces(faces: Vec3[][]): THREE.BufferGeometry {
    const coords: number[] = [];
    for (const input of faces) {
        const face = input.length > 3 && input[0].every((v, i) => v === input[input.length - 1][i]) ? input.slice(0, -1) : input;
        if (face.length < 3)
            continue;
        const normal = new THREE.Vector3();
        for (let i = 0; i < face.length; i++) {
            const a = face[i], b = face[(i + 1) % face.length];
            normal.x += (a[1] - b[1]) * (a[2] + b[2]);
            normal.y += (a[2] - b[2]) * (a[0] + b[0]);
            normal.z += (a[0] - b[0]) * (a[1] + b[1]);
        }
        if (normal.lengthSq() < 1e-14)
            continue;
        const abs = [Math.abs(normal.x), Math.abs(normal.y), Math.abs(normal.z)], drop = abs.indexOf(Math.max(...abs)), axes = [0, 1, 2].filter(i => i !== drop);
        const triangles = THREE.ShapeUtils.triangulateShape(face.map(p => new THREE.Vector2(p[axes[0]], p[axes[1]])), []);
        for (const tri of triangles)
            for (const i of tri) {
                const p = point(face[i]);
                coords.push(p.x, p.y, p.z);
            }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(coords, 3));
    g.computeVertexNormals();
    g.computeBoundingBox();
    g.computeBoundingSphere();
    return g;
}
function planar(out: number[], outer: XY[], holes: XY[][], height: number) {
    const clean = (r: XY[]) => r.length > 3 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1] ? r.slice(0, -1) : r;
    const o = clean(outer), h = holes.map(clean);
    if (o.length < 3)
        return;
    const all = [...o, ...h.flat()];
    for (const t of THREE.ShapeUtils.triangulateShape(o.map(p => new THREE.Vector2(...p)), h.map(r => r.map(p => new THREE.Vector2(...p)))))
        for (const i of t)
            out.push(all[i][0], height, -all[i][1]);
}
function buffer(coords: number[]) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(coords, 3));
    g.computeVertexNormals();
    return g;
}
export class CityViewport {
    private scene = new THREE.Scene();
    private renderer: THREE.WebGLRenderer;
    private perspective = new THREE.PerspectiveCamera(42, 1, .1, 100000);
    private ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 100000);
    private camera: THREE.PerspectiveCamera | THREE.OrthographicCamera = this.perspective;
    private controls: OrbitControls;
    private root = new THREE.Group();
    private groups = {} as Record<Layer, THREE.Group>;
    private geometries = new Set<THREE.BufferGeometry>();
    private materials = new Set<THREE.Material>();
    private meshes: THREE.InstancedMesh[] = [];
    private vegetationMeshes: THREE.InstancedMesh[] = [];
    private bsSiteCount = 0;
    private sectorCount = 0;
    private uePointCount = 0;
    private uePositionsSample: Vec3[] = [];
    private terrainTriangles = 0;
    private picks: THREE.Object3D[] = [];
    private box = new THREE.Box3();
    private selection: THREE.Box3Helper | null = null;
    private selectedBounds: THREE.Box3 | null = null;
    private layerState: Record<Layer, boolean> = {
        buildings: true,
        roads: true,
        parks: true,
        parcels: false,
        boundaries: true,
        grid: true,
        labels: true,
        terrain: true,
        vegetation: true,
        source_vegetation: true,
        synthetic_vegetation: true,
        bs: true,
        sectors: true,
        ue: true
    };
    private heightColor = true;
    private observer: ResizeObserver;
    private raf = 0;
    private disposed = false;
    private interacting = false;
    private ray = new THREE.Raycaster();
    private down = [0, 0];
    private labelHost: HTMLDivElement;
    private labels: {
        at: THREE.Vector3;
        el: HTMLElement;
    }[] = [];
    private rtRoot = new THREE.Group();
    private rtCoverageRoot = new THREE.Group();
    private rtPathCount = 0;
    private rtSegmentCount = 0;
    private rtInteractionCount = 0;
    private rtBatchCount = 0;
    private rtBatchTotal = 0;
    private rtCoverageCount = 0;
    private rtCoverageRange: [number, number] | null = null;
    private rtCoverageFiniteCount = 0;
    private rtTXPositions = new Set<string>();
    private rtRXPositions = new Set<string>();
    private top = false;
    onSelect: (object: InspectObject | null) => void = () => {
    };
    constructor(private host: HTMLElement) {
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            preserveDrawingBuffer: true
        });
        this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
        this.renderer.setClearColor(0xeaf0f3);
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.15;
        host.prepend(this.renderer.domElement);
        this.renderer.domElement.tabIndex = 0;
        this.renderer.domElement.setAttribute('aria-label', '三维场景：左键旋转，滚轮缩放，中键或右键平移，单击选择建筑、植被或BS');
        this.labelHost = document.createElement('div');
        this.labelHost.className = 'city-labels';
        host.append(this.labelHost);
        this.rtRoot.name = 'RT paths';
        this.rtCoverageRoot.name = 'RT sampled power coverage';
        this.root.add(this.rtRoot, this.rtCoverageRoot);
        this.scene.add(this.root, new THREE.HemisphereLight(0xf6fbff, 0x879793, 2.5));
        const light = new THREE.DirectionalLight(0xfff6e8, 2.6);
        light.position.set(-300, 600, 200);
        this.scene.add(light);
        this.controls = this.makeControls();
        this.renderer.domElement.addEventListener('pointerdown', e => this.down = [e.clientX, e.clientY]);
        this.renderer.domElement.addEventListener('pointerup', e => {
            if (e.button !== 0 || Math.hypot(e.clientX - this.down[0], e.clientY - this.down[1]) > 5)
                return;
            const r = host.getBoundingClientRect();
            this.ray.setFromCamera(new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, 1 - (e.clientY - r.top) / r.height * 2), this.camera);
            const hit = this.ray.intersectObjects(this.picks, false).find(h => {
                for (let o: THREE.Object3D | null = h.object; o; o = o.parent)
                    if (!o.visible)
                        return false;
                return true;
            });
            if (hit) {
                const mesh = hit.object;
                const info = mesh instanceof THREE.InstancedMesh ? mesh.userData.items[hit.instanceId!] : mesh.userData.info;
                if (info) {
                    const bb = mesh instanceof THREE.InstancedMesh ? this.instanceBounds(mesh, hit.instanceId!) : new THREE.Box3().setFromObject(mesh);
                    this.select(bb);
                    this.onSelect(info);
                    return;
                }
            }
            this.select(null);
            this.onSelect(null);
        });
        this.observer = new ResizeObserver(() => this.resize());
        this.observer.observe(host);
        this.resize();
    }
    private makeControls() {
        const c = new OrbitControls(this.camera, this.renderer.domElement);
        c.enableDamping = true;
        c.dampingFactor = .1;
        c.maxPolarAngle = Math.PI / 2 - .005;
        c.minDistance = 1;
        c.maxDistance = 100000;
        c.mouseButtons = {
            LEFT: THREE.MOUSE.ROTATE,
            MIDDLE: THREE.MOUSE.PAN,
            RIGHT: THREE.MOUSE.PAN
        };
        c.addEventListener('change', this.invalidate);
        c.addEventListener('start', () => {
            this.interacting = true;
            this.invalidate();
        });
        c.addEventListener('end', () => {
            this.interacting = false;
            this.invalidate();
        });
        return c;
    }
    private material<T extends THREE.Material>(m: T): T {
        this.materials.add(m);
        return m;
    }
    private geometry<T extends THREE.BufferGeometry>(g: T): T {
        this.geometries.add(g);
        return g;
    }
    private reset() {
        this.select(null);
        for (const g of this.geometries)
            g.dispose();
        for (const m of this.materials)
            m.dispose();
        for (const m of [...this.meshes, ...this.vegetationMeshes])
            m.dispose();
        this.geometries.clear();
        this.materials.clear();
        this.meshes = [];
        this.vegetationMeshes = [];
        this.terrainTriangles = 0;
        this.bsSiteCount = 0;
        this.sectorCount = 0;
        this.uePointCount = 0;
        this.uePositionsSample = [];
        this.picks = [];
        this.rtPathCount = 0;
        this.rtSegmentCount = 0;
        this.rtInteractionCount = 0;
        this.rtBatchCount = 0;
        this.rtBatchTotal = 0;
        this.rtCoverageCount = 0;
        this.rtCoverageFiniteCount = 0;
        this.rtCoverageRange = null;
        this.rtTXPositions.clear();
        this.rtRXPositions.clear();
        this.root.clear();
        this.rtRoot = new THREE.Group();
        this.rtRoot.name = 'RT paths';
        this.rtCoverageRoot = new THREE.Group();
        this.rtCoverageRoot.name = 'RT sampled power coverage';
        this.root.add(this.rtRoot, this.rtCoverageRoot);
        this.labelHost.replaceChildren();
        this.labels = [];
        for (const layer of Object.keys(this.layerState) as Layer[]) {
            this.groups[layer] = new THREE.Group();
            this.root.add(this.groups[layer]);
        }
    }
    private addPlanar(coords: number[], layer: Layer, color: number) {
        if (!coords.length)
            return;
        const mesh = new THREE.Mesh(this.geometry(buffer(coords)), this.material(new THREE.MeshStandardMaterial({
            color,
            side: THREE.DoubleSide,
            roughness: 1
        })));
        this.groups[layer].add(mesh);
    }
    private lines(coords: number[], layer: Layer, color: number, opacity = .5) {
        if (!coords.length)
            return;
        this.groups[layer].add(new THREE.LineSegments(this.geometry(buffer(coords)), this.material(new THREE.LineBasicMaterial({
            color,
            transparent: true,
            opacity
        }))));
    }
    private ring(coords: number[], ring: XY[], z: number, matrix?: THREE.Matrix4) {
        for (let i = 0; i < ring.length; i++) {
            for (const p of [ring[i], ring[(i + 1) % ring.length]]) {
                const v = point([p[0], p[1], z]);
                if (matrix)
                    v.applyMatrix4(matrix);
                coords.push(v.x, v.y, v.z);
            }
        }
    }
    private label(text: string, at: Vec3) {
        if (this.labels.length >= 80)
            return;
        const el = document.createElement('span');
        el.textContent = text;
        this.labelHost.append(el);
        this.labels.push({
            el,
            at: point(at)
        });
    }
    private color(height: number) {
        return new THREE.Color(height < 12 ? 0xadb9bd : height < 25 ? 0x90a6ad : height < 60 ? 0x698891 : height < 120 ? 0x3f626e : 0x244b5b);
    }
    setCity(data: CityData, entry: CatalogEntry, uePositions?: Float32Array) {
        this.reset();
        const assets = new Map(data.assets.map(a => [String(a.id), a]));
        const byAsset = new Map<string, {
            instance: Instance;
            index: number;
        }[]>();
        data.instances.forEach((instance, index) => {
            const key = String(instance.asset);
            if (!assets.has(key))
                throw new Error(`建筑实例引用不存在的资产 ${key}`);
            const list = byAsset.get(key) ?? [];
            list.push({
                instance,
                index
            });
            byAsset.set(key, list);
        });
        const boundary: number[] = [];
        const material = this.material(new THREE.MeshStandardMaterial({
            color: 0xffffff,
            roughness: .86,
            side: THREE.DoubleSide
        }));
        for (const [id, items] of byAsset) {
            const asset = assets.get(id)!;
            const geometry = this.geometry(triangulateFaces(asset.faces));
            const mesh = new THREE.InstancedMesh(geometry, material, items.length);
            this.meshes.push(mesh);
            mesh.userData.items = [];
            mesh.userData.heights = [];
            items.forEach(({ instance, index }, i) => {
                const matrix = new THREE.Matrix4().compose(point(instance.position_m), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(instance.rotation_z_deg ?? 0)), new THREE.Vector3(1, 1, 1));
                mesh.setMatrixAt(i, matrix);
                mesh.setColorAt(i, this.heightColor ? this.color(asset.height_m) : new THREE.Color(0x9fb5c3));
                mesh.userData.heights.push(asset.height_m);
                mesh.userData.items.push({
                    title: `建筑 ${instance.id ?? index + 1}`,
                    kind: '建筑实例',
                    source: asset.source,
                    sourceObject: asset.source_object_index,
                    officialObjectId: asset.official_object_id,
                    officialObjectIndex: asset.official_object_index,
                    officialObjectName: asset.official_object_name,
                    geometryProvenance: asset.geometry_provenance,
                    materialRecords: [...new Set(asset.face_material_keys ?? [])].map(key => ({
                        key,
                        record: data.materials?.[key]
                    })),
                    height: asset.height_m,
                    position: instance.position_m,
                    rotation: instance.rotation_z_deg ?? 0,
                    parcel: instance.parcel,
                    role: instance.role
                } satisfies InspectObject);
                if (asset.footprint)
                    this.ring(boundary, outer(asset.footprint), .16, matrix);
            });
            mesh.instanceMatrix.needsUpdate = true;
            if (mesh.instanceColor)
                mesh.instanceColor.needsUpdate = true;
            mesh.computeBoundingBox();
            mesh.computeBoundingSphere();
            this.groups.buildings.add(mesh);
            this.picks.push(mesh);
        }
        const extent = data.ground?.extent_m ?? entry.extent_m, z = data.environment ? 0 : data.ground?.elevation_m ?? 0;
        if (data.environment) {
            this.grid(extent, z + .05);
            this.environment(data.environment, data.materials ?? {});
        }
        else {
            this.ground(extent, z);
            const road: number[] = [];
            for (const r of data.roads ?? [])
                for (let i = 1; i < r.points.length; i++) {
                    const a = r.points[i - 1], b = r.points[i], dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy);
                    if (!len)
                        continue;
                    const w = (r.width_m ?? 8) / 2, nx = -dy / len * w, ny = dx / len * w;
                    planar(road, [[a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny], [b[0] - nx, b[1] - ny], [a[0] - nx, a[1] - ny]], [], z + .08);
                }
            this.addPlanar(road, 'roads', 0xb7c1c8);
            const park: number[] = [];
            for (const p of data.parks ?? [])
                planar(park, p.outer, p.holes ?? [], z + .06);
            this.addPlanar(park, 'parks', 0xa3c5a2);
        }
        const parcel: number[] = [], parcelEdges: number[] = [];
        for (const p of data.parcels ?? []) {
            planar(parcel, outer(p.footprint), holes(p.footprint), z + .025);
            this.ring(parcelEdges, outer(p.footprint), z + .11);
            for (const hole of holes(p.footprint))
                this.ring(parcelEdges, hole, z + .11);
        }
        this.addPlanar(parcel, 'parcels', 0xc8b8a3);
        this.lines(parcelEdges, 'parcels', 0x9b835e, .65);
        this.lines(boundary, 'boundaries', 0x607d90, .5);
        if (data.radio_deployment)
            this.baseStations(data.radio_deployment);
        if (data.environment && uePositions)
            this.ueSamples(uePositions);
        for (const [east, north, text] of data.labels ?? [])
            this.label(text, [east, north, z + .5]);
        this.finish(extent);
    }
    private rtGeometry(coords: Float32Array) {
        const geometry = this.geometry(new THREE.BufferGeometry());
        geometry.setAttribute('position', new THREE.BufferAttribute(coords, 3));
        geometry.computeBoundingSphere();
        return geometry;
    }
    private rtPoints(coords: Float32Array, color: number, size: number, shape: 'square' | 'diamond' | 'ring', name: string, group = this.rtRoot) {
        if (!coords.length) return;
        const material = this.material(new THREE.PointsMaterial({ color, size, sizeAttenuation: false, transparent: true, depthTest: false, depthWrite: false, toneMapped: false }));
        const clip = shape === 'diamond' ? 'if (abs(gl_PointCoord.x - 0.5) + abs(gl_PointCoord.y - 0.5) > 0.5) discard;' : shape === 'ring' ? 'float r = length(gl_PointCoord - vec2(0.5)); if (r > 0.5 || r < 0.28) discard;' : '';
        material.onBeforeCompile = shader => {
            shader.fragmentShader = shader.fragmentShader.replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>\n${clip}`);
        };
        material.customProgramCacheKey = () => `rt-${shape}`;
        const points = new THREE.Points(this.rtGeometry(coords), material);
        points.name = name;
        points.renderOrder = 4;
        points.raycast = () => {};
        group.add(points);
    }
    /** Append all stored rays, batched by mechanism rather than one draw call per ray. */
    appendRTBatch(batch: RTBatch) {
        const measured = measureRTBatch(batch);
        const pathCounts = new Map<number, number>(), markerCounts = new Map<number, number>();
        const pathCode = (interactions: number[]) => interactions.length === 0 ? 0 : interactions.every(code => code === interactions[0]) ? interactions[0] : -1;
        for (const ray of batch.rays) {
            const code = pathCode(ray.interactions);
            pathCounts.set(code, (pathCounts.get(code) ?? 0) + (ray.points.length - 1) * 6);
            for (const bounce of ray.interactions) markerCounts.set(bounce, (markerCounts.get(bounce) ?? 0) + 3);
        }
        const allocate = (counts: Map<number, number>) => new Map([...counts].map(([code, length]) => [code, { coords: new Float32Array(length), offset: 0 }]));
        const paths = allocate(pathCounts), markers = allocate(markerCounts);
        const put = (target: { coords: Float32Array; offset: number }, p: Vec3) => {
            target.coords[target.offset++] = p[0];
            target.coords[target.offset++] = p[2];
            target.coords[target.offset++] = -p[1];
        };
        for (const ray of batch.rays) {
            const target = paths.get(pathCode(ray.interactions))!;
            for (let i = 1; i < ray.points.length; i++) {
                put(target, ray.points[i - 1]);
                put(target, ray.points[i]);
            }
            ray.interactions.forEach((code, i) => put(markers.get(code)!, ray.points[i + 1]));
        }
        for (const [code, { coords }] of paths) {
            // Mixed-mechanism paths stay neutral; their individual bounce colors
            // retain the actual sequence instead of pretending the path has one type.
            const material = this.material(new THREE.LineBasicMaterial({ color: rtColors[code] ?? rtNeutral, transparent: true, opacity: .86, depthWrite: false, toneMapped: false }));
            const line = new THREE.LineSegments(this.rtGeometry(coords), material);
            line.name = `RT paths mechanism ${code}`;
            line.renderOrder = 2;
            this.rtRoot.add(line);
        }
        for (const [code, { coords }] of markers)
            this.rtPoints(coords, rtColors[code] ?? rtNeutral, 6, 'square', `RT interaction ${code}`);
        const coordinates = (positions: Vec3[], seen: Set<string>) => {
            const fresh = positions.filter(p => {
                const key = p.join(',');
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
            const target = { coords: new Float32Array(fresh.length * 3), offset: 0 };
            fresh.forEach(p => put(target, p));
            return target.coords;
        };
        this.rtPoints(coordinates([batch.tx_position], this.rtTXPositions), rtTX, 16, 'diamond', 'RT TX markers');
        this.rtPoints(coordinates(batch.rx_positions, this.rtRXPositions), rtRX, 13, 'ring', 'RT RX sample markers');
        this.rtPathCount += batch.rays.length;
        this.rtSegmentCount += measured.segments;
        this.rtInteractionCount += measured.interactions;
        this.rtBatchCount++;
        this.invalidate();
    }
    setRTBatchTotal(total: number) {
        this.rtBatchTotal = total;
    }
    private clearRTGroup(group: THREE.Group) {
        group.traverse(object => {
            if (object instanceof THREE.LineSegments || object instanceof THREE.Points) {
                object.geometry.dispose();
                this.geometries.delete(object.geometry);
                const materials = Array.isArray(object.material) ? object.material : [object.material];
                for (const material of materials) {
                    material.dispose();
                    this.materials.delete(material);
                }
            }
        });
        group.clear();
    }
    clearRTPaths() {
        this.clearRTGroup(this.rtRoot);
        this.rtPathCount = this.rtSegmentCount = this.rtInteractionCount = this.rtBatchCount = this.rtBatchTotal = 0;
        this.rtTXPositions.clear();
        this.rtRXPositions.clear();
        this.invalidate();
    }
    clearRTCoverage() {
        this.clearRTGroup(this.rtCoverageRoot);
        this.rtCoverageCount = this.rtCoverageFiniteCount = 0;
        this.rtCoverageRange = null;
        this.invalidate();
    }
    clearRT() {
        this.clearRTPaths();
        this.clearRTCoverage();
    }
    setRTCoverage(coverage: RTCoverage) {
        this.clearRTCoverage();
        if (!Array.isArray(coverage.positions) || !Array.isArray(coverage.gain_db) || coverage.positions.length !== coverage.gain_db.length || !coverage.positions.every(validRTPoint))
            throw new Error('RT 覆盖采样位置与增益不匹配');
        let min = Infinity, max = -Infinity;
        for (const gain of coverage.gain_db) {
            if (gain === null) continue;
            if (typeof gain !== 'number' || !Number.isFinite(gain)) throw new Error('RT 采样增益无效');
            min = Math.min(min, gain);
            max = Math.max(max, gain);
            this.rtCoverageFiniteCount++;
        }
        this.rtCoverageCount = coverage.positions.length;
        if (this.rtCoverageFiniteCount) this.rtCoverageRange = [min, max];
        const coords = new Float32Array(coverage.positions.length * 3), colors = new Float32Array(coords.length);
        coverage.positions.forEach((p, i) => {
            coords.set([p[0], p[2], -p[1]], i * 3);
            const gain = coverage.gain_db[i];
            const color = gain === null ? new THREE.Color(0x7d8890) : rtCoverageColor(max === min ? .5 : (gain - min) / (max - min));
            colors.set([color.r, color.g, color.b], i * 3);
        });
        if (coords.length) {
            const geometry = this.rtGeometry(coords);
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            const points = new THREE.Points(geometry, this.material(new THREE.PointsMaterial({ size: 9, sizeAttenuation: false, vertexColors: true, transparent: true, depthTest: false, depthWrite: false, toneMapped: false })));
            points.name = 'RT sample-only serving path gain';
            points.renderOrder = 3;
            points.raycast = () => {};
            this.rtCoverageRoot.add(points);
        }
        this.invalidate();
    }
    focusRT() {
        const box = new THREE.Box3().setFromObject(this.rtRoot);
        box.union(new THREE.Box3().setFromObject(this.rtCoverageRoot));
        if (!box.isEmpty()) this.frame(box, this.top);
    }
    rtDiagnostics() {
        return {
            rtPathCount: this.rtPathCount, rtSegmentCount: this.rtSegmentCount,
            rtInteractionCount: this.rtInteractionCount,
            rtBatchCount: this.rtBatchCount, rtBatchTotal: this.rtBatchTotal,
            rtCoverageCount: this.rtCoverageCount, rtCoverageFiniteCount: this.rtCoverageFiniteCount,
            rtCoverageRange: this.rtCoverageRange ? [...this.rtCoverageRange] : null,
            rtTXCount: this.rtTXPositions.size, rtRXCount: this.rtRXPositions.size,
        };
    }
    private ueSamples(positions: Float32Array) {
        // Render-only overlay: retain every candidate, without creating scene RX/subscribers.
        const coords = new Float32Array(positions.length);
        this.uePointCount = positions.length / 3;
        for (let i = 0; i < positions.length; i += 3) {
            coords[i] = positions[i];
            coords[i + 1] = positions[i + 2];
            coords[i + 2] = -positions[i + 1];
        }
        this.uePositionsSample = Array.from({
            length: Math.min(3, this.uePointCount)
        }, (_, i) => [positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]] as Vec3);
        const geometry = this.geometry(new THREE.BufferGeometry());
        geometry.setAttribute('position', new THREE.BufferAttribute(coords, 3));
        geometry.computeBoundingSphere();
        const material = this.material(new THREE.PointsMaterial({
            color: 0x008ecb,
            size: 2,
            sizeAttenuation: false,
            depthTest: true,
            depthWrite: false,
            toneMapped: false
        }));
        material.onBeforeCompile = shader => {
            shader.fragmentShader = shader.fragmentShader.replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\nif (length(gl_PointCoord - vec2(0.5)) > 0.5) discard;');
        };
        material.customProgramCacheKey = () => 'ue-circle-v1';
        const points = new THREE.Points(geometry, material);
        points.name = 'UE candidate sampling grid';
        points.renderOrder = 1;
        points.userData.pickable = false;
        points.raycast = () => {
        };
        this.groups.ue.add(points);
        // Deliberately excluded from this.picks: a 500k-point raycast must never run.
    }
    private baseStations(radio: NonNullable<CityData['radio_deployment']>) {
        this.bsSiteCount = radio.sites.length;
        this.sectorCount = radio.sectors.length;
        const heads = new THREE.InstancedMesh(this.geometry(new THREE.SphereGeometry(5, 10, 8)), this.material(new THREE.MeshBasicMaterial({
            color: 0xe77e21
        })), radio.sites.length);
        heads.userData.items = [];
        heads.userData.isBS = true;
        const poles: number[] = [];
        radio.sites.forEach((site, i) => {
            const sectors = radio.sectors.filter(sector => sector.site_id === site.id);
            heads.setMatrixAt(i, new THREE.Matrix4().makeTranslation(site.position_m[0], site.position_m[2], -site.position_m[1]));
            heads.userData.items.push({
                title: site.id,
                kind: 'BS站点',
                source: '合成规划方案',
                sourceObject: site.id,
                height: site.position_m[2],
                position: site.position_m,
                rotation: 0,
                parcel: '—',
                role: String(sectors.length) + ' 扇区',
                placement: site.mount,
                radioPlanning: {
                    reason: site.planning_reason,
                    azimuths: sectors.map(sector => sector.azimuth_deg),
                    downtilts: sectors.map(sector => sector.downtilt_deg),
                },
            } satisfies InspectObject);
            for (const p of [point([site.position_m[0], site.position_m[1], 0]), point(site.position_m)]) {
                poles.push(p.x, p.y, p.z);
            }
        });
        heads.instanceMatrix.needsUpdate = true;
        heads.computeBoundingBox();
        heads.computeBoundingSphere();
        this.vegetationMeshes.push(heads);
        this.groups.bs.add(heads);
        this.picks.push(heads);
        this.lines(poles, 'bs', 0xb56a28, 1);
        for (const [k, color] of [0xefa13d, 0xd65d41, 0x965bc5].entries()) {
            const lines: number[] = [];
            for (const sector of radio.sectors.filter((_, i) => i % 3 === k)) {
                const a = THREE.MathUtils.degToRad(sector.azimuth_deg), [x, y, z] = sector.position_m;
                const tip = [x + 65 * Math.cos(a), y + 65 * Math.sin(a), z] as Vec3;
                const start = point([x, y, z]), end = point(tip);
                lines.push(start.x, start.y, start.z, end.x, end.y, end.z);
                for (const turn of [-.45, .45]) {
                    const tail = point([tip[0] - 10 * Math.cos(a + turn), tip[1] - 10 * Math.sin(a + turn), z]);
                    lines.push(end.x, end.y, end.z, tail.x, tail.y, tail.z);
                }
            }
            this.lines(lines, 'sectors', color, .9);
        }
    }
    private environment(env: Environment, records: Record<string, SourceMaterial>) {
        const { terrain } = env, batches = new Map<string, {
            role: string;
            key: string;
            coords: number[];
        }>();
        terrain.triangles.forEach((triangle, i) => {
            const role = terrain.triangle_roles[i] ?? 'other', key = terrain.triangle_material_keys[i];
            if (!key || !records[key])
                throw new Error(`地形三角 ${i} 的材料键未关联 scene.materials：${key}`);
            if (triangle.length !== 3)
                throw new Error(`地形三角 ${i} 必须包含三个顶点索引`);
            const id = JSON.stringify([role, key]), batch = batches.get(id) ?? {
                role,
                key,
                coords: []
            };
            for (const index of triangle) {
                const vertex = terrain.vertices[index];
                if (!vertex)
                    throw new Error(`地形三角 ${i} 引用不存在的顶点 ${index}`);
                const p = point(vertex);
                batch.coords.push(p.x, p.y, p.z);
            }
            batches.set(id, batch);
            this.terrainTriangles++;
        });
        for (const { role, key, coords } of batches.values()) {
            const layer: Layer = role === 'road' ? 'roads' : role === 'park' ? 'parks' : 'terrain', color = role === 'road' ? 0xb7c1c8 : role === 'park' ? 0xa3c5a2 : role === 'building-mask' ? 0xc6cfca : 0xe0e8e5;
            const mesh = new THREE.Mesh(this.geometry(buffer(coords)), this.material(new THREE.MeshStandardMaterial({
                color,
                side: THREE.DoubleSide,
                roughness: 1
            })));
            mesh.userData.role = role;
            mesh.userData.materialRecords = [{
                    key,
                    record: records[key]
                }];
            this.groups[layer].add(mesh);
        }
        const assets = new Map(env.vegetation_assets.map(a => [a.id, a])), byAsset = new Map<string, VegetationInstance[]>();
        for (const instance of env.vegetation_instances) {
            if (!assets.has(instance.asset))
                throw new Error(`植被实例引用不存在的资产 ${instance.asset}`);
            const items = byAsset.get(instance.asset) ?? [];
            items.push(instance);
            byAsset.set(instance.asset, items);
        }
        for (const [id, items] of byAsset) {
            const asset = assets.get(id)!;
            for (const key of asset.face_material_keys)
                if (!records[key])
                    throw new Error(`植被资产 ${id} 的材料键未关联 scene.materials：${key}`);
            const geometry = this.geometry(triangulateFaces(asset.faces));
            // Source assets are simplified source objects, not individual real trees.
            const synthetic = /synthetic/i.test(`${asset.source} ${asset.provenance}`), material = this.material(new THREE.MeshStandardMaterial({
                color: synthetic ? 0x408747 : 0x20583c,
                side: THREE.DoubleSide,
                roughness: 1,
                transparent: !synthetic,
                opacity: synthetic ? 1 : .62,
                depthWrite: synthetic
            })), mesh = new THREE.InstancedMesh(geometry, material, items.length);
            mesh.userData.items = [];
            items.forEach((instance, i) => {
                mesh.setMatrixAt(i, new THREE.Matrix4().compose(point(instance.position_m), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(instance.rotation_z_deg ?? 0)), new THREE.Vector3(1, 1, 1)));
                mesh.userData.items.push({
                    title: `${synthetic ? '合成树' : '源植被简化体'} ${instance.id}`,
                    kind: '植被实例',
                    source: asset.source,
                    sourceObject: asset.id,
                    officialObjectId: asset.official_object_id,
                    height: asset.height_m,
                    position: instance.position_m,
                    rotation: instance.rotation_z_deg ?? 0,
                    parcel: '—',
                    role: synthetic ? 'synthetic vegetation' : 'source vegetation',
                    placement: instance.placement,
                    provenance: asset.provenance,
                    rtStatus: asset.rt_status,
                    rtEnabled: instance.rt_enabled,
                    materialRecords: [...new Set(asset.face_material_keys)].map(key => ({
                        key,
                        record: records[key]
                    }))
                } satisfies InspectObject);
            });
            mesh.instanceMatrix.needsUpdate = true;
            mesh.computeBoundingBox();
            mesh.computeBoundingSphere();
            this.vegetationMeshes.push(mesh);
            this.groups[synthetic ? 'synthetic_vegetation' : 'source_vegetation'].add(mesh);
            this.picks.push(mesh);
        }
    }
    private ground(e: [
        number,
        number,
        number,
        number
    ], z: number) {
        const [a, b, c, d] = e;
        const coords: number[] = [];
        planar(coords, [[a, b], [c, b], [c, d], [a, d]], [], z - .04);
        const ground = new THREE.Mesh(this.geometry(buffer(coords)), this.material(new THREE.MeshStandardMaterial({
            color: 0xe0e8e5,
            side: THREE.DoubleSide,
            roughness: 1
        })));
        this.groups.terrain.add(ground);
        this.grid(e, z);
    }
    private grid(e: [
        number,
        number,
        number,
        number
    ], z: number) {
        const [a, b, c, d] = e;
        const grid = new THREE.GridHelper(Math.max(c - a, d - b), 40, 0xb6c9ce, 0xcbd8dd);
        grid.position.set((a + c) / 2, z - .025, -(b + d) / 2);
        this.geometry(grid.geometry);
        this.material(grid.material as THREE.Material);
        this.groups.grid.add(grid);
    }
    private finish(extent: [
        number,
        number,
        number,
        number
    ]) {
        this.box.setFromObject(this.groups.buildings);
        this.box.union(new THREE.Box3(point([extent[0], extent[3], 0]), point([extent[2], extent[1], 0])));
        this.applyLayers();
        this.fit(this.top);
    }
    setLayer(layer: Layer, value: boolean) {
        this.layerState[layer] = value;
        this.applyLayers();
    }
    private applyLayers() {
        for (const key of Object.keys(this.groups) as Layer[])
            this.groups[key].visible = this.layerState[key] && (!(key === 'source_vegetation' || key === 'synthetic_vegetation') || this.layerState.vegetation);
        this.labelHost.hidden = !this.layerState.labels;
        this.invalidate();
    }
    setHeightColor(enabled: boolean) {
        this.heightColor = enabled;
        for (const mesh of this.meshes) {
            mesh.userData.heights.forEach((h: number, i: number) => mesh.setColorAt(i, enabled ? this.color(h) : new THREE.Color(0x9fb5c3)));
            if (mesh.instanceColor)
                mesh.instanceColor.needsUpdate = true;
        }
        this.invalidate();
    }
    private instanceBounds(mesh: THREE.InstancedMesh, i: number) {
        const matrix = new THREE.Matrix4();
        mesh.getMatrixAt(i, matrix);
        return mesh.geometry.boundingBox!.clone().applyMatrix4(matrix).applyMatrix4(mesh.matrixWorld);
    }
    private select(box: THREE.Box3 | null) {
        if (this.selection) {
            this.scene.remove(this.selection);
            this.selection.geometry.dispose();
            (this.selection.material as THREE.Material).dispose();
            this.selection = null;
        }
        this.selectedBounds = box;
        if (box) {
            this.selection = new THREE.Box3Helper(box.clone().expandByScalar(.3), 0x0da88c);
            this.scene.add(this.selection);
        }
        this.invalidate();
    }
    focusSelection() {
        if (this.selectedBounds)
            this.frame(this.selectedBounds, this.top);
    }
    fit(top = this.top) {
        this.top = top;
        const target = this.controls.target.clone();
        this.controls.dispose();
        this.camera = top ? this.ortho : this.perspective;
        this.controls = this.makeControls();
        this.controls.target.copy(target);
        this.controls.enableRotate = !top;
        this.resize();
        if (!this.box.isEmpty())
            this.frame(this.box, top);
    }
    private frame(box: THREE.Box3, top: boolean) {
        const center = box.getCenter(new THREE.Vector3()), radius = Math.max(2, box.getBoundingSphere(new THREE.Sphere()).radius), aspect = this.host.clientWidth / Math.max(1, this.host.clientHeight);
        this.controls.target.copy(center);
        if (this.camera instanceof THREE.OrthographicCamera) {
            const half = radius * 1.12 / Math.min(1, aspect);
            this.camera.left = -half * aspect;
            this.camera.right = half * aspect;
            this.camera.top = half;
            this.camera.bottom = -half;
            this.camera.zoom = 1;
            this.camera.position.copy(center).add(new THREE.Vector3(0, radius * 3 + 100, .001));
        }
        else {
            const fov = THREE.MathUtils.degToRad(this.camera.fov / 2), distance = radius / Math.sin(Math.min(fov, Math.atan(Math.tan(fov) * aspect))) * 1.1;
            this.camera.position.copy(center).add(new THREE.Vector3(.8, 1, 1).normalize().multiplyScalar(distance));
        }
        this.camera.far = Math.max(10000, radius * 40);
        this.camera.updateProjectionMatrix();
        this.controls.update();
        this.invalidate();
    }
    private resize() {
        const w = this.host.clientWidth, h = this.host.clientHeight;
        if (!w || !h)
            return;
        this.renderer.setSize(w, h);
        this.perspective.aspect = w / h;
        this.perspective.updateProjectionMatrix();
        const half = this.ortho.top;
        this.ortho.left = -half * w / h;
        this.ortho.right = half * w / h;
        this.ortho.updateProjectionMatrix();
        this.invalidate();
    }
    diagnostics() {
        return {
            mode: this.top ? 'orthographic-top' : 'perspective',
            assetMeshes: this.meshes.length,
            instanceCount: this.meshes.reduce((n, m) => n + m.count, 0),
            sourceTriangles: this.meshes.reduce((n, m) => n + m.geometry.getAttribute('position').count / 3, 0),
            terrainTriangles: this.terrainTriangles,
            bsSiteCount: this.bsSiteCount,
            sectorCount: this.sectorCount,
            uePointCount: this.uePointCount,
            ueVisible: this.uePointCount > 0 && !!this.groups.ue?.visible,
            uePositionsSample: this.uePositionsSample.map(p => [...p]),
            ...this.rtDiagnostics(),
            vegetationCount: this.vegetationMeshes.filter(m => !m.userData.isBS).reduce((n, m) => n + m.count, 0),
            labelCount: this.labels.length,
            render: {
                ...this.renderer.info.render
            },
            memory: {
                ...this.renderer.info.memory
            },
            camera: this.camera.position.toArray(),
            target: this.controls.target.toArray()
        };
    }
    screenshot() {
        this.renderer.render(this.scene, this.camera);
        return this.renderer.domElement.toDataURL('image/png');
    }
    private invalidate = () => {
        if (!this.raf && !this.disposed)
            this.raf = requestAnimationFrame(this.render);
    };
    private render = () => {
        this.raf = 0;
        if (this.disposed)
            return;
        const changed = this.controls.update();
        this.renderer.render(this.scene, this.camera);
        for (const { at, el } of this.labels) {
            const p = at.clone().project(this.camera);
            el.style.transform = `translate(-50%,-100%) translate(${(p.x + 1) / 2 * this.host.clientWidth}px,${(1 - p.y) / 2 * this.host.clientHeight}px)`;
            el.style.visibility = p.z > -1 && p.z < 1 && Math.abs(p.x) < 1 && Math.abs(p.y) < 1 ? 'visible' : 'hidden';
        }
        if (changed || this.interacting)
            this.invalidate();
    };
    dispose() {
        this.disposed = true;
        cancelAnimationFrame(this.raf);
        this.observer.disconnect();
        this.controls.dispose();
        this.reset();
        this.renderer.dispose();
        this.renderer.domElement.remove();
        this.labelHost.remove();
    }
}
