import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {SECTORS, universe, related} from './model.mjs';
import {mountWorld} from './World.jsx';
import {PortalChoice} from './portal-choice.mjs';

// The bridge is the only dependency on the original, non-module application.
const bridge = {
  request: (...args) => api(...args),
  metadata: () => v5meta,
  escape: value => esc(value),
  home: () => openPage('start'),
  work: id => v5Work(id),
  invoice: id => v5Invoice(id)
};
const safe = bridge.escape;
const money = value => new Intl.NumberFormat('nl-NL',{style:'currency',currency:'EUR'}).format(Number(value || 0));
const button = (action,label) => `<button type="button" data-spatial="${action}">${label}</button>`;

export class SpatialDataSource {
  constructor(request, metadata) {this.request=request;this.metadata=metadata;}
  async all(kind, signal) {
    if(!this.metadata().permissions[kind]?.read) return [];
    if(kind==='workorders') return this.request('v5/workorders');
    const rows=[];
    for(let offset=0;;offset+=100) {
      if(signal.aborted) throw new DOMException('Aborted','AbortError');
      const result=await this.request(`v5/entities/${kind}?limit=100&offset=${offset}`);
      rows.push(...result.items);
      if(offset+100>=result.total) return rows;
    }
  }
  async load(signal) {
    const kinds=['customers','workorders','invoices','objects'];
    const results=await Promise.all(kinds.map(k=>this.all(k,signal)));
    return Object.fromEntries(kinds.map((k,i)=>[k,results[i]]));
  }
}

// Camera-projected HTML stays a real DOM surface: forms, keyboard, drag and drop.
export class SpatialHtmlLayer {
  constructor(host,camera,renderer) {this.host=host;this.camera=camera;this.renderer=renderer;this.labels=document.createElement('div');this.labels.className='spatial-labels';host.append(this.labels);this.items=[];}
  setNodes(nodes) {
    this.labels.replaceChildren();
    const counts={};
    this.items=nodes.filter(node=>{counts[node.kind]=(counts[node.kind]||0)+1;return counts[node.kind]<=30;}).map(node=>{const el=document.createElement('span');el.className='spatial-node-label';el.textContent=node.label;el.dataset.urgent=node.urgent;this.labels.append(el);return {el,node};});
  }
  point(position) {
    const p=new THREE.Vector3(...position).project(this.camera);
    return {x:(p.x+1)*this.host.clientWidth/2,y:(1-p.y)*this.host.clientHeight/2,visible:p.z>-1&&p.z<1&&Math.abs(p.x)<1.1&&Math.abs(p.y)<1.1};
  }
  update(selected) {
    for(const {el,node} of this.items) {const p=this.point(node.position);el.hidden=!p.visible;el.style.transform=`translate(${p.x-45}px,${p.y+20}px)`;}
    const panel=this.host.querySelector('.spatial-panel');
    if(!panel) return;
    if(this.host.clientWidth<650) {panel.style.transform='';panel.style.left='12px';panel.style.top='auto';panel.style.bottom='12px';return;}
    const p=selected?this.point(selected.position):{x:this.host.clientWidth/2,y:200};
    const x=Math.max(16,Math.min(this.host.clientWidth-panel.offsetWidth-16,p.x+55));
    const y=Math.max(85,Math.min(this.host.clientHeight-panel.offsetHeight-20,p.y-panel.offsetHeight/3));
    panel.style.left=`${x}px`;panel.style.top=`${y}px`;panel.style.bottom='auto';
  }
  dispose() {this.labels.remove();}
}

export class SpatialCanvas {
  constructor(host,{source,actions=bridge}={}) {
    this.host=host;this.source=source;this.actions=actions;this.abort=new AbortController();this.disposed=false;this.nodes=[];this.meshes=[];this.selected=null;this.detailSerial=0;this.busy=false;
    this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.data={customers:[],workorders:[],invoices:[],objects:[]};
    this.renderChrome();
    this.listen(host,'click',e=>this.onClick(e));
    this.listen(host,'submit',e=>this.onSubmit(e));
    this.listen(host,'input',e=>{if(e.target.matches('[data-spatial-search]'))this.search(e.target.value);});
    this.listen(host,'keydown',e=>{if(e.key==='Escape') {e.stopPropagation();this.overview();}});
    this.listen(host,'dragstart',e=>{const task=e.target.closest('[data-task]');if(task)e.dataTransfer.setData('application/roefs-task',task.dataset.task);});
    this.listen(host,'dragover',e=>{if(e.target.closest('[data-done]'))e.preventDefault();});
    this.listen(host,'drop',e=>{const column=e.target.closest('[data-done]');if(!column)return;e.preventDefault();const id=Number(e.dataTransfer.getData('application/roefs-task'));if(id)this.changeTask(id,column.dataset.done==='true');});
    this.listen(document,'visibilitychange',()=>{this.lastTime=0;});
    try{this.initScene();}catch(error){this.fallback=true;this.host.querySelector('[data-instructions]').textContent='3D is hier niet beschikbaar. Gebruik de zoeklijst om gegevens te openen en te bewerken.';this.host.querySelector('[data-spatial=help]').textContent='Uitleg';}
    this.refresh();
  }
  listen(target,event,callback) {target.addEventListener(event,callback,{signal:this.abort.signal});}
  renderChrome() {
    this.host.innerHTML=`<div class="spatial-top"><div class="spatial-brand"><img src="/assets/amocean-mark.png?v=2" alt="Amocean"><div><b>ROEFS ONE</b><small>RUIMTELIJKE WERKPLEK</small></div></div><div class="spatial-controls"><span class="spatial-live" data-live>Gegevens laden</span>${button('refresh','Vernieuwen')}${button('overview','Overzicht')}${button('exit','Sluiten')}</div></div><section class="spatial-overview"><span class="spatial-kicker">BEDRIJF IN BEWEGING</span><h1>Jouw bedrijf. In één ruimte.</h1><p>Kies een knooppunt om aan het werk te gaan.</p><div class="spatial-sectors" data-counts></div></section><div class="spatial-bottom"><section class="spatial-search spatial-glass" aria-label="Zoek en open bedrijfsgegevens"><input type="search" placeholder="Zoek klant, opdracht, factuur" aria-label="Zoek ruimtelijke gegevens" data-spatial-search><div class="spatial-results" data-results></div></section><div class="spatial-help"><div class="spatial-legend">${Object.values(SECTORS).map(s=>`<span style="--tone:${s.color}">${s.label}</span>`).join('')}<span style="--tone:#ff936f">Aandacht nodig</span></div><div data-instructions>Sleep om te draaien · scroll om te zoomen<br>Twee vingers om te verplaatsen · klik om te openen</div><div class="spatial-zoom">${button('zoom-in','+ Vergroten')}${button('zoom-out','− Verkleinen')}${button('help','?')}</div></div></div><div class="spatial-message spatial-glass" data-loading role="status">Bedrijfsgegevens laden…</div>`;
  }
  initScene() {
    this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));
    this.renderer.setClearColor('#080d16');this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    const canvas=this.renderer.domElement;canvas.className='spatial-canvas';canvas.setAttribute('aria-label','Ruimtelijke bedrijfsgegevens. Gebruik ook de doorzoekbare knoppenlijst.');canvas.tabIndex=0;this.host.prepend(canvas);
    this.scene=new THREE.Scene();this.scene.fog=new THREE.FogExp2('#080d16',.004);
    this.camera=new THREE.PerspectiveCamera(46,1,.1,2500);this.camera.position.set(44,48,64);
    this.controls=new OrbitControls(this.camera,canvas);this.controls.enableDamping=!this.reduced;this.controls.dampingFactor=.08;this.controls.maxPolarAngle=Math.PI*.47;this.controls.minDistance=5;this.controls.maxDistance=900;
    this.scene.add(new THREE.AmbientLight('#c4d8ee',1.8));const light=new THREE.DirectionalLight('#d4e8ff',3);light.position.set(10,30,20);this.scene.add(light);
    this.grid=new THREE.GridHelper(500,100,'#203947','#11212e');this.grid.position.y=-.3;this.scene.add(this.grid);
    this.group=new THREE.Group();this.scene.add(this.group);
    this.geometry=new THREE.CylinderGeometry(.85,1.05,1,6);this.materials={};
    for(const [key,s] of Object.entries(SECTORS))this.materials[key]=new THREE.MeshStandardMaterial({color:s.color,emissive:s.color,emissiveIntensity:.25,roughness:.3,metalness:.55});
    this.materials.urgent=new THREE.MeshStandardMaterial({color:'#ff936f',emissive:'#ff5929',emissiveIntensity:.85});
    this.selection=new THREE.Mesh(new THREE.TorusGeometry(1.25,.045,8,48),new THREE.MeshBasicMaterial({color:'#ffffff'}));this.selection.rotation.x=-Math.PI/2;this.selection.visible=false;this.scene.add(this.selection);
    this.lines=new THREE.Group();this.scene.add(this.lines);this.html=new SpatialHtmlLayer(this.host,this.camera,this.renderer);
    this.raycaster=new THREE.Raycaster();this.pointer=new THREE.Vector2();
    const pointers=new Set();
    this.listen(canvas,'pointerdown',e=>{pointers.add(e.pointerId);this.down=pointers.size===1?{x:e.clientX,y:e.clientY,moved:false}:null;this.flight=null;});
    this.listen(canvas,'pointerup',e=>{pointers.delete(e.pointerId);const down=this.down;this.down=null;if(pointers.size||!down||down.moved||Math.hypot(e.clientX-down.x,e.clientY-down.y)>6)return;const hit=this.hit(e);if(hit)this.select(hit);});
    this.listen(canvas,'pointercancel',e=>{pointers.delete(e.pointerId);this.down=null;});
    this.listen(canvas,'pointermove',e=>{if(this.down&&Math.hypot(e.clientX-this.down.x,e.clientY-this.down.y)>6)this.down.moved=true;canvas.style.cursor=this.hit(e)?'pointer':'grab';});
    this.listen(canvas,'wheel',()=>{this.flight=null;});
    this.listen(canvas,'webglcontextlost',e=>{e.preventDefault();this.say('3D-weergave onderbroken. De gegevens blijven bereikbaar via de zoeklijst.');});
    this.listen(canvas,'webglcontextrestored',()=>this.refresh());
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(this.host);this.resize();
    this.animate(0);
  }
  resize() {if(!this.renderer)return;const {clientWidth:w,clientHeight:h}=this.host;this.renderer.setSize(w,h);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();if(!this.selected)this.frameAll();}
  hit(e) {const r=this.renderer.domElement.getBoundingClientRect();this.pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.raycaster.setFromCamera(this.pointer,this.camera);return this.raycaster.intersectObjects(this.meshes,false)[0]?.object.userData.node;}
  fly(target,distance) {
    if(!this.camera)return;
    this.flight={from:this.camera.position.clone(),targetFrom:this.controls.target.clone(),to:target.clone().add(new THREE.Vector3(.45,.75,1).normalize().multiplyScalar(distance)),target:target.clone(),start:performance.now()};
    if(this.reduced){this.camera.position.copy(this.flight.to);this.controls.target.copy(target);this.flight=null;this.controls.update();}
  }
  frameAll() {
    if(!this.camera)return;
    const box=new THREE.Box3();for(const n of this.nodes)box.expandByPoint(new THREE.Vector3(...n.position));
    if(box.isEmpty())box.setFromCenterAndSize(new THREE.Vector3(),new THREE.Vector3(35,5,20));
    const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
    const distance=Math.max(32,Math.max(size.x/this.camera.aspect,size.z)*.75/Math.tan(THREE.MathUtils.degToRad(23)));
    this.fly(center,Math.min(850,distance+12));
  }
  animate(time) {
    if(this.disposed)return;
    this.frame=requestAnimationFrame(t=>this.animate(t));
    if(document.hidden)return;
    if(this.flight){const f=this.flight,t=Math.min(1,(time-f.start)/(this.reduced?1:950)),s=t*t*(3-2*t);this.camera.position.lerpVectors(f.from,f.to,s);this.controls.target.lerpVectors(f.targetFrom,f.target,s);if(t===1)this.flight=null;}
    this.controls.update();
    if(this.selection.visible&&!this.reduced)this.selection.rotation.z=time*.00015;
    this.html.update(this.selected);this.renderer.render(this.scene,this.camera);
  }
  async refresh() {
    if(this.loading)return;this.loading=true;
    this.host.querySelector('[data-live]').textContent='Gegevens laden';
    try {
      const data=await this.source.load(this.abort.signal);if(this.disposed)return;
      this.data=data;this.nodes=universe(data);this.buildNodes();this.search(this.host.querySelector('[data-spatial-search]').value);
      this.host.querySelector('[data-counts]').innerHTML=Object.entries(SECTORS).map(([k,s])=>`<div class="spatial-sector"><strong style="color:${s.color}">${data[k].length}</strong><span>${s.label}</span></div>`).join('');
      this.host.querySelector('[data-live]').textContent='Opgeslagen gegevens';this.host.querySelector('[data-loading]')?.remove();
      if(this.selected){const node=this.nodes.find(n=>n.key===this.selected.key);if(node)await this.select(node,false);else this.overview();}else this.frameAll();
    }catch(error){if(!this.disposed){this.host.querySelector('[data-loading]')?.remove();this.say('Laden mislukt: '+error.message);}}
    finally{this.loading=false;}
  }
  buildNodes() {
    if(!this.group)return;
    this.group.clear();this.meshes=this.nodes.map(node=>{const mesh=new THREE.Mesh(this.geometry,this.materials[node.urgent?'urgent':node.kind]);mesh.position.set(...node.position);mesh.scale.y=node.kind==='invoices'?node.position[1]*1.2:1.8;mesh.userData.node=node;this.group.add(mesh);return mesh;});
    this.html.setNodes(this.nodes);
  }
  search(query='') {
    const found=this.nodes.filter(n=>(n.label+' '+n.record.id).toLocaleLowerCase('nl').includes(query.toLocaleLowerCase('nl')));
    this.host.querySelector('[data-results]').innerHTML=found.slice(0,30).map(n=>`<button type="button" data-node="${safe(n.key)}">${safe(n.label)}<small>${SECTORS[n.kind].label} · #${n.record.id}</small></button>`).join('')+(found.length>30?'<small>Verfijn je zoekopdracht voor meer resultaten.</small>':!found.length?'<small>Geen gegevens gevonden binnen je toegangsrechten.</small>':'');
  }
  async select(node,move=true) {
    const serial=++this.detailSerial;this.selected=node;
    if(move)this.fly(new THREE.Vector3(...node.position),this.host.clientWidth<650?21:18);
    this.host.querySelector('.spatial-panel')?.remove();this.drawLinks(node);
    const panel=document.createElement('section');panel.className='spatial-panel spatial-glass';panel.setAttribute('aria-label','Gegevens bewerken');
    panel.innerHTML=`<header><span class="spatial-kicker">${SECTORS[node.kind].label.toUpperCase()} / #${node.record.id}</span>${button('close-panel','Sluiten ×')}</header><h2>${safe(node.label)}</h2><div data-detail><p>Gegevens openen…</p></div><p role="status" data-feedback></p><p role="alert" data-error></p>`;this.host.append(panel);this.html?.update(node);
    if(!this.html){panel.style.left=this.host.clientWidth<650?'12px':'auto';panel.style.right='12px';panel.style.top='85px';}
    try {
      const r=node.record,write=this.actions.metadata().permissions[node.kind]?.write;
      let body='';
      if(node.kind==='customers') {
        body=`<p>${safe(r.billing_address||r.city||'Geen adres vastgelegd')}</p><form data-customer-form>${[['name','Klantnaam'],['contact','Contactpersoon'],['email','E-mail'],['phone','Telefoon']].map(([k,label])=>`<label>${label}<input name="${k}" value="${safe(r[k])}" type="${k==='email'?'email':'text'}" maxlength="2000" ${k==='name'?'required':''} ${write?'':'readonly'}></label>`).join('')}${write?'<button type="submit">Wijzigingen opslaan</button>':'<p>Je hebt leestoegang.</p>'}</form>`;
      }else if(node.kind==='workorders') {
        const detail=await this.actions.request('v5/workorders/'+r.id);if(this.disposed||serial!==this.detailSerial)return;
        this.workDetail=detail;
        const locked=['Voltooid','Goedgekeurd','Factureerbaar','Geannuleerd'].includes(detail.workorder.workflow);
        body=`<p>${safe(r.date)} · ${safe(r.start_time)}–${safe(r.end_time)}<br>Status: ${safe(r.workflow||r.status)}</p><h3>Checklist</h3><p>Sleep een taak naar een kolom of tik op de taak om deze te verplaatsen.</p><div class="spatial-board">${[false,true].map(done=>`<div class="spatial-column" data-done="${done}"><h4>${done?'Afgerond':'Te doen'}</h4>${detail.checklist.filter(t=>Boolean(t.done)===done).map(t=>`<button type="button" class="spatial-task" data-task="${t.id}" draggable="${write&&!locked}" ${write&&!locked?'':'disabled'} aria-label="${safe(t.title)} ${done?'heropenen':'afronden'}">${safe(t.title)}</button>`).join('')}</div>`).join('')}</div>${write&&!locked?'<form data-task-form><label>Nieuwe checklisttaak<input name="title" required maxlength="300"></label><button type="submit">Taak opslaan</button></form>':''}<h3>Uitvoering</h3>${button('work-detail','Volledige werkbon openen')}`;
      }else {
        body=`<p>Status: ${safe(r.status)}<br>Vervaldatum: ${safe(r.due_date)}<br>Bedrag: <strong>${safe(money(r.amount))}</strong></p><p>De hoogte van een factuurknooppunt geeft het factuurbedrag weer. Oranje duidt op een verstreken vervaldatum bij een onbetaalde factuur.</p>${r.workorder_id?button('invoice-detail','Factuurregels en beoordeling'):''}`;
      }
      if(serial!==this.detailSerial||this.disposed)return;
      const connected=related(node,this.data);
      panel.querySelector('[data-detail]').innerHTML=body+`<h3>Verbonden gegevens · ${connected.length}</h3><div class="spatial-related">${connected.slice(0,30).map(n=>`<button type="button" data-node="${safe(n.key)}">${safe(n.label)}<small> · ${SECTORS[n.kind].label}</small></button>`).join('')||'<p>Geen zichtbare koppelingen gevonden.</p>'}${connected.length>30?'<p>Gebruik de zoeklijst voor de overige koppelingen.</p>':''}</div>`;
      panel.querySelector('input,button')?.focus({preventScroll:true});
    }catch(error){if(serial===this.detailSerial)this.say(error.message);}
  }
  drawLinks(node) {
    if(!this.lines)return;
    this.clearLines();this.selection.position.set(...node.position);this.selection.position.y=.15;this.selection.visible=true;
    for(const n of related(node,this.data)) {const geometry=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...node.position),new THREE.Vector3(...n.position)]);const line=new THREE.Line(geometry,new THREE.LineBasicMaterial({color:'#76e6dc',transparent:true,opacity:.32}));this.lines.add(line);}
    this.html.setNodes([node,...related(node,this.data)]);
  }
  clearLines(){for(const line of [...this.lines.children]){line.geometry.dispose();line.material.dispose();this.lines.remove(line);}}
  overview(){++this.detailSerial;this.selected=null;this.host.querySelector('.spatial-panel')?.remove();if(this.lines)this.clearLines();if(this.selection)this.selection.visible=false;this.html?.setNodes(this.nodes);this.frameAll();}
  say(message,success=false) {let el=this.host.querySelector(success?'[data-feedback]':'[data-error]');if(!el){el=document.createElement('p');el.className='spatial-message spatial-glass';el.setAttribute('role',success?'status':'alert');this.host.append(el);}el.textContent=message;}
  async mutate(operation,success) {
    if(this.busy)return;this.busy=true;const key=this.selected?.key;
    try{await operation();if(this.disposed)return;if(key===this.selected?.key){await this.refresh();this.say(success,true);}}
    catch(error){if(!this.disposed&&key===this.selected?.key)this.say(error.message+' Vernieuw de gegevens voordat je opnieuw opslaat.');}
    finally{this.busy=false;}
  }
  changeTask(id,done) {
    const detail=this.workDetail;if(this.selected?.kind!=='workorders'||!detail||detail.workorder.id!==this.selected.record.id)return;
    const task=detail.checklist.find(t=>t.id===id);if(!task||Boolean(task.done)===done||!this.actions.metadata().permissions.workorders?.write)return;
    this.mutate(()=>this.actions.request(`v5/workorders/${detail.workorder.id}/checklist`,'POST',{id,version:task.version,done}),'Checklist opgeslagen');
  }
  onSubmit(e) {
    if(e.target.matches('[data-customer-form]')) {e.preventDefault();const node=this.selected;const data=Object.fromEntries(new FormData(e.target));this.mutate(()=>this.actions.request('v5/entities/customers/'+node.record.id,'PUT',{...data,version:node.record.version}),'Klantgegevens opgeslagen');}
    if(e.target.matches('[data-task-form]')) {e.preventDefault();const id=this.selected.record.id,title=new FormData(e.target).get('title');this.mutate(()=>this.actions.request(`v5/workorders/${id}/checklist`,'POST',{title}),'Taak opgeslagen');}
  }
  async onClick(e) {
    const task=e.target.closest('[data-task]');if(task){const t=this.workDetail?.checklist.find(x=>x.id===Number(task.dataset.task));if(t)this.changeTask(t.id,!t.done);return;}
    const n=e.target.closest('[data-node]');if(n){const node=this.nodes.find(x=>x.key===n.dataset.node);if(node)await this.select(node);return;}
    const action=e.target.closest('[data-spatial]')?.dataset.spatial;
    if(action==='world')return launchWorld();
    if(action==='exit')return this.actions.home();
    if(action==='refresh')return this.refresh();
    if(action==='overview'||action==='close-panel')return this.overview();
    if(action==='zoom-in'||action==='zoom-out'){if(this.controls)this.fly(this.controls.target,this.camera.position.distanceTo(this.controls.target)*(action==='zoom-in'?.7:1.4));}
    if(action==='help')this.say('Kies een knooppunt of zoek een naam. Bewerk klantgegevens in het paneel. Bij een opdracht kun je checklisttaken afwerken. Overzicht brengt je terug. Esc sluit het paneel.');
    if(action==='work-detail'||action==='invoice-detail') {const node=this.selected;await this.actions.home();await (action==='work-detail'?this.actions.work(node.record.id):this.actions.invoice(node.record.id));}
  }
  dispose() {
    this.disposed=true;++this.detailSerial;this.abort.abort();cancelAnimationFrame(this.frame);this.resizeObserver?.disconnect();this.controls?.dispose();this.html?.dispose();
    if(this.lines)this.clearLines();this.geometry?.dispose();Object.values(this.materials||{}).forEach(m=>m.dispose());this.selection?.geometry.dispose();this.selection?.material.dispose();this.grid?.geometry.dispose();if(this.grid)for(const m of [this.grid.material].flat())m.dispose();this.renderer?.dispose();this.renderer?.forceContextLoss();this.host.remove();
  }
}

// Extend existing navigation without replacing the original start screen.
let active=null,cinema=null,launchPresentation=null;
let spatialReady=false;
function launchWorld(options){return launchPresentation?.(options);}
export function handleSpatialPop(event){
  if(!spatialReady)return;
  const url=new URL(location.href);if(url.searchParams.get('ruimte')!=='1')return;
  let id;try{id=decodeURIComponent(url.hash.slice(1)||'start');}catch{return;}
  if(!Object.values(GROUPS).flat().includes(id)||!canView(id))return;
  const overview=event.state?.spatialWorld&&event.state.roefsPage===id?event.state.spatialOverview:id==='start';
  event.stopImmediatePropagation();history.replaceState({roefsPage:id,spatialWorld:true,spatialOverview:overview},'',url);openPage(id,true);
}
export function setupSpatial(entry=new URL(location.href)){
spatialReady=true;
let requested=null;try{if(entry.searchParams.get('ruimte')==='1')requested=decodeURIComponent(entry.hash.slice(1)||'start');}catch{}
let chooser=null,portalChosen=false;
const choiceKey='roefsPortalChoice',account=()=>JSON.stringify([me?.id,me?.username,me?.role]);
function remember(mode){try{sessionStorage.setItem(choiceKey,JSON.stringify({account:account(),mode}));}catch{}}
function remembered(){try{const saved=JSON.parse(sessionStorage.getItem(choiceKey));return saved?.account===account()?saved.mode:null;}catch{return null;}}
function dismissChoice(){chooser?.dispose();chooser=null;}
function resetChoice(){dismissChoice();portalChosen=false;try{sessionStorage.removeItem(choiceKey);}catch{}}
function showChoice(){
  if(chooser||cinema||!token||!v5meta||!document.querySelector('.daily-home'))return;
  chooser=new PortalChoice({root:document.querySelector('#root'),onOld:()=>{portalChosen=true;remember('old');dismissChoice();document.querySelector('.daily-actions button')?.focus({preventScroll:true});},onNew:()=>launchWorld(),onLogout:()=>logout()});
}
launchPresentation=function(options={}){if(cinema)return cinema;dismissChoice();portalChosen=true;remember('new');cinema=mountWorld({groups:GROUPS,names:NAMES,visible:canView,renderPage:renderLegacy,currentPage:()=>page,navigationEpoch:()=>navigationSerial,canRestore:()=>!cinema&&Boolean(token),initial:options.initial||null,onClose:()=>{cinema=null;remember('old');}});return cinema;};
NAMES.spatial='Ruimtelijke werkplek';GROUPS['DAGELIJKS WERK'].splice(1,0,'spatial');
const previousCanView=canView;
canView=function(p){return p==='spatial'?['customers','workorders','invoices'].some(k=>v5meta?.permissions[k]?.read):previousCanView(p);};
const previousStart=v5Start;
function addSpatialEntries(){
  const actions=document.querySelector('.daily-actions');if(page!=='start'||!actions)return;
  for(const [id,label,action] of [['choice','Portaal kiezen',showChoice],['world','3D-portaal',launchWorld],['data','Ruimtelijke werkplek',()=>openPage('spatial')]]){
    if(id==='data'&&!canView('spatial')||actions.querySelector(`[data-spatial-entry="${id}"]`))continue;
    const b=document.createElement('button');b.type='button';b.className='daily-pill';b.dataset.spatialEntry=id;b.textContent=label;b.addEventListener('click',action);actions.append(b);
  }
  if(requested&&v5meta){const initial=requested;requested=null;queueMicrotask(()=>{if(!Object.values(GROUPS).flat().includes(initial)||!canView(initial)){toast('Geen toegang tot deze module.');showChoice();return;}launchWorld({initial});});return;}
  if(!portalChosen&&token&&v5meta&&!cinema){const mode=remembered();if(mode==='old')portalChosen=true;else if(mode==='new')queueMicrotask(()=>{if(!cinema&&token)launchWorld();});else showChoice();}
}
v5Start=async function(){
  // Show the decision before the dashboard's optional widgets finish loading.
  if(!requested&&!portalChosen&&!remembered())showChoice();
  await previousStart();addSpatialEntries();
};
const previousOpen=openPage;
async function renderLegacy(p,fromHistory=false){
  active?.dispose();active=null;
  if(p!=='spatial')return previousOpen(p,fromHistory);
  if(!canView(p))return toast('Geen toegang tot deze werkplek.');
  closeMobileMenu();closeModal();if(!fromHistory&&page!==p)history.pushState({roefsPage:p},'','#'+p);page=p;++navigationSerial;
  const host=document.createElement('div');host.className='spatial-host';document.querySelector('#root').replaceChildren(host);document.title='Ruimtelijke werkplek | ROEFS ONE';
  active=new SpatialCanvas(host,{source:new SpatialDataSource(bridge.request,bridge.metadata)});
}
openPage=async function(p,fromHistory=false){
  if(cinema)return cinema.navigate(p,fromHistory);
  if(fromHistory&&history.state?.spatialWorld){const initial=history.state.spatialOverview?'start':p;launchWorld({initial});return;}
  return renderLegacy(p,fromHistory);
};
const previousLogout=logout;
logout=async function(){++navigationSerial;cinema?.dispose({restorePending:false});cinema=null;active?.dispose();active=null;resetChoice();return previousLogout();};
const previousLoginScreen=loginScreen;
loginScreen=function(){++navigationSerial;cinema?.dispose({restorePending:false});cinema=null;active?.dispose();active=null;resetChoice();return previousLoginScreen();};
const previousLogin=login;
login=async function(event){resetChoice();return previousLogin(event);};
// Reusable architecture for another frontend/data source; authentication remains in bridge.
window.ROEFSSpatial={SpatialCanvas,SpatialDataSource,SpatialHtmlLayer,universe,metrics:()=>cinema?.metrics||null};
// Cookie boot can finish while this local bundle is still downloading.
addSpatialEntries();
}
