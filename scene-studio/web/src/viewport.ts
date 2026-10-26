import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { bounds, type SceneData, type Selection, type Vec3 } from './model';

const pos = ([x,y,z]: Vec3) => new THREE.Vector3(x,z,-y);
type Layer = 'buildings' | 'receivers' | 'trajectory' | 'grid' | 'labels' | 'connection';
export class Viewport {
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(42, 1, 0.1, 20000);
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private objects = new THREE.Group();
  private grid = new THREE.Group();
  private receiverGroup = new THREE.Group();
  private buildingGroup = new THREE.Group();
  private pathGroup = new THREE.Group();
  private mobile = new THREE.Group();
  private connection = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineDashedMaterial({color:0x3da497,dashSize:1,gapSize:0.65,transparent:true,opacity:0.5}));
  private selectionBox: THREE.Box3Helper | null = null;
  private pickable: THREE.Object3D[] = [];
  private labelItems: {el: HTMLDivElement; at: THREE.Vector3}[] = [];
  private labels: HTMLDivElement;
  private raycaster = new THREE.Raycaster();
  private pointer = new THREE.Vector2();
  private down = [0,0];
  private selected: Selection = null;
  private data!: SceneData;
  private layers: Record<Layer,boolean> = {buildings:true,receivers:true,trajectory:true,grid:true,labels:true,connection:false};
  private animation = 0;
  private observer: ResizeObserver;
  onSelect: (selection: Selection) => void = () => {};

  constructor(private host: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.setClearColor(0xedf2f6, 1);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.2;
    this.renderer.domElement.setAttribute('aria-label','三维街区视图，可用鼠标旋转、缩放和平移');
    this.renderer.domElement.tabIndex = 0;
    host.append(this.renderer.domElement);
    this.labels = document.createElement('div'); this.labels.className='map-labels'; host.append(this.labels);
    this.scene.add(new THREE.HemisphereLight(0xf5faff,0xa2b5b0,3));
    const sun = new THREE.DirectionalLight(0xfff9ed,3.1); sun.position.set(-35,85,30);sun.castShadow=true;
    sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-120;sun.shadow.camera.right=120;sun.shadow.camera.top=120;sun.shadow.camera.bottom=-120;sun.shadow.camera.far=300;sun.shadow.bias=-0.0002;sun.shadow.normalBias=0.08;
    this.scene.add(sun);
    this.scene.add(this.objects,this.grid,this.mobile,this.pathGroup,this.connection);
    this.controls = new OrbitControls(this.camera,this.renderer.domElement);
    this.controls.enableDamping=true;this.controls.dampingFactor=0.09;this.controls.minDistance=3;this.controls.maxDistance=5000;this.controls.maxPolarAngle=Math.PI/2-0.025;
    this.controls.mouseButtons = {LEFT:THREE.MOUSE.ROTATE,MIDDLE:THREE.MOUSE.DOLLY,RIGHT:THREE.MOUSE.PAN};
    this.renderer.domElement.addEventListener('pointerdown',e=>this.down=[e.clientX,e.clientY]);
    this.renderer.domElement.addEventListener('pointerup', e => {
      if(e.button!==0 || Math.hypot(e.clientX-this.down[0],e.clientY-this.down[1])>5)return;
      const rect=this.renderer.domElement.getBoundingClientRect();
      this.pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);
      this.raycaster.setFromCamera(this.pointer,this.camera);
      const hit=this.raycaster.intersectObjects(this.pickable,true).find(h=>{
        for(let o:THREE.Object3D|null=h.object;o;o=o.parent) if(!o.visible)return false;
        return true;
      });
      let target=hit?.object;
      while(target && !target.userData.selection)target=target.parent??undefined;
      this.onSelect(target?.userData.selection??null);
    });
    this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(host);this.resize();this.render();
  }
  private resize() { const {width,height}=this.host.getBoundingClientRect();if(!width||!height)return;this.camera.aspect=width/height;this.camera.updateProjectionMatrix();this.renderer.setSize(width,height); }
  private clear(group: THREE.Group) {
    for(const child of [...group.children]) {
      child.traverse(o=>{if(o instanceof THREE.Mesh || o instanceof THREE.Line || o instanceof THREE.LineSegments){o.geometry.dispose();const mats=Array.isArray(o.material)?o.material:[o.material];mats.forEach(m=>m.dispose());}});group.remove(child);
    }
  }
  private label(text: string, at: THREE.Vector3, type='') {const el=document.createElement('div');el.className=`map-label ${type}`;el.textContent=text;this.labels.append(el);this.labelItems.push({el,at});}
  private box(size: Vec3, position: Vec3, color: THREE.ColorRepresentation) {
    const geo=new THREE.BoxGeometry(size[0],size[2],size[1]);
    const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color,roughness:0.78,metalness:0.06}));mesh.position.copy(pos(position));mesh.castShadow=true;mesh.receiveShadow=true;return mesh;
  }
  setScene(data: SceneData, fit=false) {
    this.data=data;this.clear(this.objects);this.clear(this.grid);this.clear(this.mobile);this.clear(this.pathGroup);this.labels.replaceChildren();this.labelItems=[];this.pickable=[];
    this.buildingGroup=new THREE.Group();this.receiverGroup=new THREE.Group();this.objects.add(this.buildingGroup,this.receiverGroup);
    for(const tile of data.tiles) {
      const floor=this.box([tile.size[0],tile.size[1],0.4],[...tile.center,-0.22],tile.color);floor.userData.selection={kind:'tile',id:tile.id};this.objects.add(floor);this.pickable.push(floor);
      const road=new THREE.Mesh(new THREE.PlaneGeometry(tile.size[0],14),new THREE.MeshStandardMaterial({color:0xcdd9e1,roughness:1}));road.rotation.x=-Math.PI/2;road.position.copy(pos([...tile.center,0.005]));road.receiveShadow=true;this.objects.add(road);
      // Road paint is visual decoration; it is not a radio-material assignment.
      for(let x=-tile.size[0]/2+2;x<tile.size[0]/2;x+=5) {
        const stripe=new THREE.Mesh(new THREE.PlaneGeometry(2.4,0.16),new THREE.MeshBasicMaterial({color:0xf8fafc}));stripe.rotation.x=-Math.PI/2;stripe.position.copy(pos([tile.center[0]+x,tile.center[1],0.03]));this.objects.add(stripe);
      }
      const points=[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]].map(([x,y])=>pos([tile.center[0]+x*tile.size[0]/2,tile.center[1]+y*tile.size[1]/2,0.08]));
      const edge=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineDashedMaterial({color:0x849ba7,dashSize:0.8,gapSize:0.65,transparent:true,opacity:0.65}));edge.computeLineDistances();this.objects.add(edge);
      this.label(tile.name,pos([tile.center[0],tile.center[1]-tile.size[1]/2-2.5,0]),'tile-label');
    }
    for(const b of data.buildings) {
      const group=new THREE.Group();group.userData.selection={kind:'building',id:b.id};
      const mesh=this.box(b.size,b.position,0xb6c7d7);group.add(mesh);
      const edge=new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry),new THREE.LineBasicMaterial({color:0x7b98ad,transparent:true,opacity:0.38}));edge.position.copy(mesh.position);group.add(edge);
      const roof=this.box([b.size[0]*0.94,b.size[1]*0.94,0.16],[b.position[0],b.position[1],b.position[2]+b.size[2]/2+0.1],0xdde6ed);group.add(roof);
      // Light facade bands improve depth perception without changing the stored building mesh.
      for(let z=-b.size[2]/2+2.1;z<b.size[2]/2-0.5;z+=3) {
        const g=new THREE.EdgesGeometry(new THREE.BoxGeometry(b.size[0]+0.025,0.42,b.size[1]+0.025));
        const line=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0xe9f3fc,transparent:true,opacity:0.6}));line.position.copy(pos([b.position[0],b.position[1],b.position[2]+z]));group.add(line);
      }
      this.buildingGroup.add(group);this.pickable.push(group);
      this.label(b.name,pos([b.position[0],b.position[1],b.position[2]+b.size[2]/2+1.4]),'building-label');
    }
    for(const tx of data.transmitters) {
      const group=new THREE.Group();group.userData.selection={kind:'transmitter',id:tx.id};
      const mast=new THREE.Mesh(new THREE.CylinderGeometry(0.16,0.3,tx.position[2],8),new THREE.MeshStandardMaterial({color:0x3e6473}));mast.position.copy(pos([tx.position[0],tx.position[1],tx.position[2]/2]));group.add(mast);
      const antenna=this.box([0.55,1.15,1.9],tx.position,0x176e68);group.add(antenna);
      const cap=new THREE.Mesh(new THREE.SphereGeometry(0.35,16,12),new THREE.MeshStandardMaterial({color:0xf59e46,emissive:0xf59e46,emissiveIntensity:0.3}));cap.position.copy(pos([tx.position[0],tx.position[1],tx.position[2]+1.2]));group.add(cap);
      this.objects.add(group);this.pickable.push(group);this.label(tx.name,pos([tx.position[0],tx.position[1],tx.position[2]+3]),'tx-label');
    }
    for(const rx of data.receivers) {
      const node=new THREE.Mesh(new THREE.SphereGeometry(0.48,16,12),new THREE.MeshStandardMaterial({color:0x228bc1,roughness:0.3,emissive:0x147db1,emissiveIntensity:0.12}));node.position.copy(pos(rx.position));node.userData.selection={kind:'receiver',id:rx.id};this.receiverGroup.add(node);this.pickable.push(node);
      const stem=new THREE.Line(new THREE.BufferGeometry().setFromPoints([pos([rx.position[0],rx.position[1],0.05]),pos(rx.position)]),new THREE.LineBasicMaterial({color:0x3596c7,transparent:true,opacity:0.55}));this.receiverGroup.add(stem);
    }
    const marker=new THREE.Mesh(new THREE.SphereGeometry(0.65,20,16),new THREE.MeshStandardMaterial({color:0x17a38c,emissive:0x178877,emissiveIntensity:0.35}));this.mobile.add(marker);
    const ring=new THREE.Mesh(new THREE.RingGeometry(0.95,1.13,40),new THREE.MeshBasicMaterial({color:0x16a38a,side:THREE.DoubleSide,transparent:true,opacity:0.8}));ring.rotation.x=-Math.PI/2;ring.position.y=-1.4;this.mobile.add(ring);
    const bb=bounds(data),extent=Math.max(bb.maxX-bb.minX,bb.maxY-bb.minY)+50;
    const groundGrid=new THREE.GridHelper(extent,Math.ceil(extent/5),0xc5d1dc,0xdce5ec);groundGrid.position.set((bb.minX+bb.maxX)/2,-0.46,-(bb.minY+bb.maxY)/2);(groundGrid.material as THREE.Material).transparent=true;(groundGrid.material as THREE.Material).opacity=0.65;this.grid.add(groundGrid);
    this.setSelection(this.selected);this.applyLayers();if(fit)this.fit();
  }
  setPath(points: Vec3[], planned: boolean) {
    this.clear(this.pathGroup);
    if(points.length>1) {
      const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(pos)),new THREE.LineDashedMaterial({color:planned?0xa58243:0x139f88,dashSize:0.8,gapSize:0.38}));line.computeLineDistances();this.pathGroup.add(line);
      for(const p of [points[0],points[points.length-1]]) {const point=new THREE.Mesh(new THREE.SphereGeometry(0.28,12,8),new THREE.MeshBasicMaterial({color:planned?0xa58243:0x16a38a}));point.position.copy(pos(p));this.pathGroup.add(point);}
    }
    this.pathGroup.visible=this.layers.trajectory;
  }
  setPosition(p: Vec3) {
    this.mobile.position.copy(pos(p));
    const tx=this.data.transmitters[0];
    this.connection.geometry.dispose();this.connection.geometry=new THREE.BufferGeometry().setFromPoints(tx?[pos(tx.position),pos(p)]:[]);this.connection.computeLineDistances();
  }
  setSelection(selection: Selection) {
    this.selected=selection;
    if(this.selectionBox) {this.scene.remove(this.selectionBox);this.selectionBox.geometry.dispose();(this.selectionBox.material as THREE.Material).dispose();this.selectionBox=null;}
    if(!selection)return;
    const target=this.pickable.find(o=>o.userData.selection?.id===selection.id);if(!target)return;
    const box=new THREE.Box3().setFromObject(target).expandByScalar(0.18);
    this.selectionBox=new THREE.Box3Helper(box,0x16a38a);this.scene.add(this.selectionBox);
    this.applyLayers();
  }
  setLayer(layer: Layer,visible: boolean) {this.layers[layer]=visible;this.applyLayers();}
  private applyLayers() {
    this.buildingGroup.visible=this.layers.buildings;this.receiverGroup.visible=this.layers.receivers;this.pathGroup.visible=this.layers.trajectory;this.mobile.visible=this.layers.trajectory;this.grid.visible=this.layers.grid;this.labels.style.display=this.layers.labels?'':'none';this.connection.visible=this.layers.connection;
    this.labelItems.forEach(({el})=>{if(el.classList.contains('building-label'))el.hidden=!this.layers.buildings;});
    if(this.selectionBox) this.selectionBox.visible=this.selected?.kind==='building'?this.layers.buildings:this.selected?.kind==='receiver'?this.layers.receivers:true;
  }
  fit(top=false) {
    const box=new THREE.Box3().setFromObject(this.objects),sphere=box.getBoundingSphere(new THREE.Sphere()),center=sphere.center;
    const verticalHalf=THREE.MathUtils.degToRad(this.camera.fov/2),horizontalHalf=Math.atan(Math.tan(verticalHalf)*this.camera.aspect);
    const distance=Math.max(5,sphere.radius/Math.sin(Math.min(verticalHalf,horizontalHalf))*1.05);
    this.controls.maxDistance=Math.max(5000,distance*3);this.camera.far=Math.max(20000,distance*10);this.camera.updateProjectionMatrix();
    this.controls.target.copy(center);
    this.camera.position.copy(center).add((top?new THREE.Vector3(0,1,0.0001):new THREE.Vector3(0.78,0.93,1.05)).normalize().multiplyScalar(distance));this.controls.update();
  }
  focusPosition(p: Vec3) {const center=pos(p);this.controls.target.copy(center);this.camera.position.copy(center).add(new THREE.Vector3(12,14,17));this.controls.update();}
  zoom(factor:number) {this.camera.position.sub(this.controls.target).multiplyScalar(factor).add(this.controls.target);this.controls.update();}
  screenshot() {this.renderer.render(this.scene,this.camera);return this.renderer.domElement.toDataURL('image/png');}
  private render=()=>{
    this.animation=requestAnimationFrame(this.render);this.controls.update();this.renderer.render(this.scene,this.camera);
    const width=this.host.clientWidth,height=this.host.clientHeight;
    const origin=this.controls.target.clone().project(this.camera),north=this.controls.target.clone().add(new THREE.Vector3(0,0,-10)).project(this.camera);
    const northArrow=this.host.querySelector<HTMLElement>('.axis-center');
    if(northArrow)northArrow.style.transform=`rotate(${Math.atan2(-(north.y-origin.y)*height,(north.x-origin.x)*width)*180/Math.PI+45}deg)`;
    for(const {el,at} of this.labelItems) {const v=at.clone().project(this.camera);el.style.transform=`translate(-50%, -100%) translate(${(v.x+1)/2*width}px,${(-v.y+1)/2*height}px)`;el.style.visibility=v.z<1&&Math.abs(v.x)<1&&Math.abs(v.y)<1?'visible':'hidden';}
  };
  dispose() {cancelAnimationFrame(this.animation);this.observer.disconnect();this.controls.dispose();this.clear(this.objects);this.clear(this.grid);this.clear(this.mobile);this.clear(this.pathGroup);this.connection.geometry.dispose();(this.connection.material as THREE.Material).dispose();this.renderer.dispose();}
}
