import React,{Suspense,useEffect,useMemo,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Canvas,useFrame,useThree} from '@react-three/fiber';
import {Html,useTexture} from '@react-three/drei';
import {EffectComposer,Bloom,DepthOfField,Noise,Vignette,ChromaticAberration} from '@react-three/postprocessing';
import {BlendFunction} from 'postprocessing';
import {createStore} from 'zustand/vanilla';
import {useStore} from 'zustand';
import gsap from 'gsap';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {QUALITY,qualityFor,cameraNoise,workspacePose,entryPoints} from './world-model.mjs';
import {WorldSession} from './session.mjs';
import {LowMonoliths} from './LowMonoliths.jsx';
import {FlightLens} from './FlightLens.jsx';

const COLOURS=['#dbd1bb','#d8a66c','#d4cabb','#aaafa7','#d1a16b','#bec7c0','#9e9e98'];
// Flights use wall time even if a shader compile temporarily stalls the ticker.
gsap.ticker.lagSmoothing(0);
function surfaceTexture() {
  const canvas=document.createElement('canvas');canvas.width=canvas.height=128;
  const ctx=canvas.getContext('2d'),pixels=ctx.createImageData(128,128);
  let seed=1741;
  for(let i=0;i<pixels.data.length;i+=4){seed=(seed*16807)%2147483647;const v=110+seed%65;pixels.data.set([v,v,v,255],i);}
  ctx.putImageData(pixels,0,0);const texture=new THREE.CanvasTexture(canvas);texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.repeat.set(3,6);return texture;
}
function signTexture(module) {
  const c=document.createElement('canvas');c.width=512;c.height=256;const ctx=c.getContext('2d');
  ctx.fillStyle='#101111';ctx.fillRect(0,0,512,256);ctx.fillStyle='#d7ceba';ctx.font='18px monospace';ctx.fillText(`ROEFS / ${String(module.district+1).padStart(2,'0')}.${String(module.index+1).padStart(2,'0')}`,28,39);
  ctx.fillStyle='#faf5e9';ctx.font='500 36px sans-serif';
  const words=module.label.split(' ');let line='',y=110;
  for(const word of words){if(ctx.measureText(line+word).width>455&&line){ctx.fillText(line,28,y);y+=42;line='';}line+=word+' ';}ctx.fillText(line,28,y);
  ctx.fillStyle='#a28c6a';ctx.fillRect(28,220,456,2);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}
function BrandPlane(){
  const source=useTexture('/assets/amocean-mark.png?v=2'),map=useMemo(()=>{const t=source.clone();t.colorSpace=THREE.SRGBColorSpace;return t;},[source]);useEffect(()=>()=>map.dispose(),[map]);
  return <mesh position={[0,6,-32.04]}><planeGeometry args={[7,7]}/><meshBasicMaterial map={map} transparent toneMapped={false}/></mesh>;
}

function Monolith({module,store,onOpen,materialMap}) {
  const invalidate=useThree(s=>s.invalidate);
  const group=useRef(),body=useRef();const hovered=useStore(store,s=>s.hovered===module.id);const reduced=useStore(store,s=>s.reduced);
  const quality=useStore(store,s=>s.quality),light=quality==='low';
  const geometry=useMemo(()=>light?new THREE.BoxGeometry(1.76,module.height,.92):new RoundedBoxGeometry(1.76,module.height,.92,2,.07),[module.height,light]);
  const texture=useMemo(()=>signTexture(module),[module]);
  useEffect(()=>()=>{geometry.dispose();texture.dispose();},[geometry,texture]);
  useEffect(()=>{if(!group.current)return;const tween=gsap.to(group.current.position,{y:hovered?.17:0,duration:reduced?0:.45,ease:'power3.out',onUpdate:invalidate});return ()=>tween.kill();},[hovered,reduced,invalidate]);
  const setHover=id=>store.setState({hovered:id});
  return <group position={module.position}>
    <group ref={group} rotation={[0,module.variant===1?-.12:module.variant===2?.12:0,0]}>
      <mesh ref={body} geometry={geometry} position={[0,module.height/2,0]} castShadow
        onPointerOver={e=>{e.stopPropagation();setHover(module.id);}} onPointerOut={()=>setHover(null)}
        onClick={e=>{e.stopPropagation();onOpen(module.id);}}>
        {light?<meshPhongMaterial color={hovered?'#fff3d6':COLOURS[module.district%7]} specular="#8c887c" shininess={65} emissive={hovered?'#241c0e':'#000000'}/>:<meshPhysicalMaterial color={hovered?'#fff3d6':COLOURS[module.district%7]} metalness={.72} roughness={.32} bumpMap={materialMap} bumpScale={.045} clearcoat={.4} emissive={hovered?'#604324':'#000000'} emissiveIntensity={.2}/>}
      </mesh>
      <mesh position={[0,module.height*.65,.474]}><planeGeometry args={[1.62,.81]}/><meshBasicMaterial map={texture} toneMapped={false}/></mesh>
      {!light&&<mesh position={[.72,module.height/2,.49]}><boxGeometry args={[.027,module.height*.84,.025]}/><meshBasicMaterial color={hovered?'#ffe0a0':'#ad8d5c'} toneMapped={false}/></mesh>}
      {!light&&module.variant===1&&<mesh position={[0,module.height+.16,0]} rotation={[0,0,.14]}><boxGeometry args={[2.1,.12,1.2]}/><meshStandardMaterial color="#737670" metalness={.9} roughness={.2}/></mesh>}
      {!light&&module.variant===2&&<mesh position={[0,.14,.1]}><boxGeometry args={[2.1,.22,1.35]}/><meshStandardMaterial color="#51544e" metalness={.7} roughness={.3}/></mesh>}
    </group>
    {!light&&<mesh position={[0,-.03,0]}><boxGeometry args={[2.2,.12,1.55]}/><meshStandardMaterial color="#20231f" metalness={.7} roughness={.35}/></mesh>}
    {hovered&&<Html position={[0,module.height+.6,0]} center style={{pointerEvents:'none'}}><span className="world-object-label">{module.label}</span></Html>}
  </group>;
}

function CameraRig({store,bounds,onReady,session}) {
  const {camera,gl,size,invalidate}=useThree();const reduced=useStore(store,s=>s.reduced),hovered=useStore(store,s=>s.hovered);
  const flight=useStore(store,s=>s.flight),motion=useRef(null),home=useRef(null);
  const intro=useRef({value:0}),light=useRef(),frames=useRef({time:0,count:0,slow:0}),elapsed=useRef(0),flashTime=useRef({tick:0,time:0});
  const curve=useMemo(()=>new THREE.CatmullRomCurve3([new THREE.Vector3(22,19,37),new THREE.Vector3(20,18,35),new THREE.Vector3(17,19,36),new THREE.Vector3(18,20,38),new THREE.Vector3(22,19,37)],true),[]);
  useEffect(()=>{const tween=gsap.to(intro.current,{value:1,duration:reduced?0:1.6,ease:'power3.out',onUpdate:invalidate});onReady();return ()=>tween.kill();},[reduced,onReady,invalidate]);
  useEffect(()=>{
    const unsubscribe=store.subscribe(()=>invalidate());
    const wake=()=>{frames.current={time:0,count:0,slow:0};if(!document.hidden)invalidate();};
    document.addEventListener('visibilitychange',wake);invalidate();
    return ()=>{unsubscribe();document.removeEventListener('visibilitychange',wake);};
  },[store,invalidate]);
  useEffect(()=>{
    if(!flight)return;
    const start=camera.position.clone(),oldTarget=new THREE.Vector3(0,1,-4);camera.getWorldDirection(oldTarget);oldTarget.multiplyScalar(8).add(start);
    if(!home.current)home.current={camera:start.clone(),target:new THREE.Vector3(0,1,-4)};
    const target=flight.mode==='out'?home.current.target.clone():new THREE.Vector3(...workspacePose(flight.module).target);
    const end=flight.mode==='out'?home.current.camera.clone():new THREE.Vector3(...workspacePose(flight.module).camera);
    const points=flight.mode==='out'?[start,start.clone().lerp(end,.35).add(new THREE.Vector3(2,3,1)),end.clone().lerp(start,.12),end]:entryPoints(flight.module,start.toArray()).map(p=>new THREE.Vector3(...p));
    const path=new THREE.CatmullRomCurve3(points),movement={p:0,path,oldTarget,target,startFov:camera.fov,endFov:flight.mode==='out'?46:50};motion.current=movement;
    const tween=gsap.to(movement,{p:1,duration:reduced?.12:1.55,ease:reduced?'power1.out':'power3.inOut',onUpdate:invalidate,onComplete:()=>{
      camera.position.copy(end);camera.lookAt(target);camera.fov=movement.endFov;camera.updateProjectionMatrix();motion.current=null;
      if(flight.mode==='out')elapsed.current=0;
      session.finishFlight(flight.key);invalidate();
    }});
    return ()=>{tween.kill();motion.current=null;};
  },[flight?.key,reduced,camera,session,invalidate]);
  const position=new THREE.Vector3(),target=new THREE.Vector3();
  useFrame((state,delta)=>{
    if(document.hidden)return;
    elapsed.current+=Math.min(delta,.1);const time=elapsed.current;
    const active=bounds.find(m=>m.id===hovered);
    curve.getPointAt(reduced?0:(time*.006)%1,position);
    const mobile=size.width<700;
    if(mobile){position.set(28,29,57);}
    position.multiplyScalar(1+(1-intro.current.value)*.25);
    if(!reduced){
      const p=store.getState().parallax;
      position.x+=state.pointer.x*.28+p.x*.32+cameraNoise(time*.7,1)*.025+cameraNoise(time*2,2)*.008;
      position.y+=state.pointer.y*.14+p.y*.2+cameraNoise(time*.6,3)*.02;
    }
    target.set(active?active.position[0]*.025:0,1,active?-4+active.position[2]*.025:-4);
    if(active&&!reduced)position.multiplyScalar(.985);
    const movement=motion.current,s=store.getState();
    if(movement){session.motionProgress=movement.p;movement.path.getPoint(movement.p,camera.position);target.lerpVectors(movement.oldTarget,movement.target,movement.p);camera.lookAt(target);camera.fov=THREE.MathUtils.lerp(movement.startFov,movement.endFov,movement.p)+(!reduced?Math.sin(movement.p*Math.PI)*1.2:0);camera.updateProjectionMatrix();}
    else if(s.selected&&['inside','mounting','exiting','error'].includes(s.stage)){const pose=workspacePose(s.selected);camera.position.set(...pose.camera);target.set(...pose.target);camera.lookAt(target);}
    else if(s.stage==='flying-in'||s.stage==='flying-out'){camera.getWorldDirection(target).multiplyScalar(8).add(camera.position);}
    else {camera.position.lerp(position,reduced?1:1-Math.exp(-delta*3));camera.lookAt(target);if(!reduced)camera.rotateZ(cameraNoise(time*.4,4)*.0007);}
    if(light.current){light.current.position.copy(camera.position);light.current.target.position.copy(target);light.current.target.updateMatrixWorld();}
    if(flashTime.current.tick!==s.flashTick)flashTime.current={tick:s.flashTick,time:performance.now()};gl.toneMappingExposure=1.25+(!reduced&&s.flash&&s.flashTick?Math.exp(-(performance.now()-flashTime.current.time)/65)*.65:0);
    const continuous=!reduced||Boolean(movement);
    session.renderedFrames=(session.renderedFrames||0)+1;
    session.metrics={drawCalls:gl.info.render.calls,triangles:gl.info.render.triangles,dpr:gl.getPixelRatio(),quality:s.quality,fps:continuous?s.fps:null,renderMode:continuous?'continuous':'on-demand',renderedFrames:session.renderedFrames};
    if(continuous)invalidate();
    // Sparse updates in a stationary scene are intentional, not slow GPU frames.
    if(!continuous){frames.current={time:0,count:0,slow:0};return;}
    if(!frames.current.time)frames.current.time=performance.now();frames.current.count++;
    if(frames.current.count>=90||(performance.now()-frames.current.time>=1800&&frames.current.count>=4)){const fps=frames.current.count*1000/(performance.now()-frames.current.time);const tier=store.getState().quality;
      store.setState({fps:Math.round(fps)});
      if(fps<(mobile?28:45)){frames.current.slow++;if(frames.current.slow>=2&&tier!=='low'){const q=tier==='high'?'medium':'low';store.setState({quality:q});gl.setPixelRatio(QUALITY[q].dpr);frames.current.slow=0;}}else frames.current.slow=0;
      frames.current.count=0;frames.current.time=performance.now();
    }
  });
  return <><spotLight ref={light} intensity={3600} distance={105} decay={2} angle={.64} penumbra={.06} color="#fff0d4"/><primitive object={light.current?.target||new THREE.Object3D()}/></>;
}

function WorldScene({catalogue,store,onOpen,onReady,session}) {
  const quality=useStore(store,s=>s.quality),reduced=useStore(store,s=>s.reduced),hovered=useStore(store,s=>s.hovered);const all=useMemo(()=>catalogue.flatMap(g=>g.modules),[catalogue]);
  const focus=useRef(new THREE.Vector3(0,2,-4)),dof=useRef();
  useFrame((_,delta)=>{const module=store.getState().selected||all.find(m=>m.id===hovered);focus.current.lerp(module?new THREE.Vector3(...workspacePose(module).target):new THREE.Vector3(0,2,-4),1-Math.exp(-delta*3));if(dof.current?.target)dof.current.target.copy(focus.current);});
  const map=useMemo(surfaceTexture,[]);useEffect(()=>()=>map.dispose(),[map]);
  const tier=QUALITY[quality];
  return <>
    <color attach="background" args={['#080a09']}/><fog attach="fog" args={['#080a09',35,110]}/>
    <ambientLight intensity={.12} color="#bec9ce"/><directionalLight position={[-20,12,-20]} intensity={1.8} color="#8b9a9d"/>
    <CameraRig store={store} bounds={all} onReady={onReady} session={session}/>
    <mesh rotation={[-Math.PI/2,0,0]} position={[0,-.16,0]}><planeGeometry args={[240,240]}/>{quality==='low'?<meshPhongMaterial color="#151b15" specular="#484b40" shininess={40}/>:<meshStandardMaterial color="#101511" metalness={.65} roughness={.38} bumpMap={map} bumpScale={.08}/>}</mesh>
    <gridHelper args={[100,50,'#393b30','#1c221c']} position={[0,-.145,-5]}/>
    {quality==='low'&&<LowMonoliths all={all} store={store} onOpen={onOpen} signTexture={signTexture} colours={COLOURS}/>}
    {catalogue.map(group=><group key={group.label}>
      {quality!=='low'&&group.modules.map(module=><Monolith key={module.id} module={module} store={store} onOpen={onOpen} materialMap={map}/>)}
      <Html position={[group.center[0],.15,group.center[1]-2.1]} center style={{pointerEvents:'none'}}><span className="world-district">{String(group.district+1).padStart(2,'0')} / {group.label}</span></Html>
    </group>)}
    <mesh position={[0,6,-32]}><torusGeometry args={[8,.055,8,96]}/><meshBasicMaterial color="#a18b62"/></mesh>
    <BrandPlane/>
    <mesh position={[-21,5,-10]}><boxGeometry args={[.3,10,.3]}/><meshStandardMaterial color="#4c514a" metalness={.8} roughness={.2}/></mesh>
    <mesh position={[21,5,-10]}><boxGeometry args={[.3,10,.3]}/><meshStandardMaterial color="#4c514a" metalness={.8} roughness={.2}/></mesh>
    <ModuleSurface session={session} store={store}/>
    {tier.post&&<EffectComposer multisampling={0} enableNormalPass={false}>
      <FlightLens session={session} store={store}/>
      <Bloom intensity={.25} luminanceThreshold={1.1} luminanceSmoothing={.3} mipmapBlur/>
      {tier.dof&&!reduced&&<DepthOfField ref={dof} target={[0,2,-4]} focalLength={.02} bokehScale={.8} height={360}/>}
      <Noise opacity={reduced?0:.026} blendFunction={BlendFunction.SOFT_LIGHT}/>
      <Vignette eskil={false} offset={.15} darkness={.48}/>
      {quality==='high'&&!reduced&&<ChromaticAberration offset={new THREE.Vector2(.00035,.00035)} radialModulation modulationOffset={.75}/>}
    </EffectComposer>}
  </>;
}

function LegacySlot({session}){
  const ref=useRef();useEffect(()=>{session.attach(ref.current);return ()=>{if(!session.closed&&session.root.parentElement===ref.current)session.park();if(session.slot===ref.current)session.slot=null;};},[session]);
  return <div className="world-module-ui" ref={ref}/>;
}
function ModuleSurface({session,store}){
  const {size}=useThree(),stage=useStore(store,s=>s.stage),module=useStore(store,s=>s.selected),quality=useStore(store,s=>s.quality);
  if(!module||!['mounting','inside','exiting','flying-out'].includes(stage))return null;
  const pose=workspacePose(module),width=Math.min(1200,size.width-32),height=Math.max(180,size.height-250);
  const factor=400*16*Math.tan(THREE.MathUtils.degToRad(25))/size.height;
  return <group position={pose.target}>
    <mesh position={[0,0,-.05]}><boxGeometry args={[width*factor/400+.14,height*factor/400+.14,.08]}/>{quality==='high'?<meshPhysicalMaterial color="#d4c5a9" transmission={.92} thickness={.22} roughness={.14} ior={1.35}/>:<meshPhongMaterial color="#292f25" shininess={75}/>}</mesh>
    <Html transform distanceFactor={factor} zIndexRange={[4,3]} style={{pointerEvents:'auto'}}>
      <section className="world-module-panel" aria-label={'Werkruimte '+module.label} style={{width,height}}
        onPointerDown={e=>e.stopPropagation()} onPointerUp={e=>e.stopPropagation()} onPointerMove={e=>e.stopPropagation()} onClick={e=>e.stopPropagation()} onWheel={e=>e.stopPropagation()}><LegacySlot session={session}/></section>
    </Html>
  </group>;
}

class RenderBoundary extends React.Component {
  constructor(props){super(props);this.state={failed:false};}
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(){this.props.onFail();}
  render(){return this.state.failed?null:this.props.children;}
}

function World({session,onClose}) {
  const store=session.store,catalogue=session.catalogue;
  const [supported,setSupported]=useState(null),[ready,setReady]=useState(false),[query,setQuery]=useState(''),[list,setList]=useState(false),[tilt,setTilt]=useState('off');
  const quality=useStore(store,s=>s.quality),hovered=useStore(store,s=>s.hovered),reduced=useStore(store,s=>s.reduced);
  const stage=useStore(store,s=>s.stage),selected=useStore(store,s=>s.selected),error=useStore(store,s=>s.error),sound=useStore(store,s=>s.sound),flash=useStore(store,s=>s.flash),flashTick=useStore(store,s=>s.flashTick),started=useRef(false);
  const modules=useMemo(()=>catalogue.flatMap(g=>g.modules),[catalogue]);const current=modules.find(m=>m.id===hovered);
  useEffect(()=>{
    const canvas=document.createElement('canvas');let gl;
    try{gl=canvas.getContext('webgl2');}catch{}
    if(gl){const info=gl.getExtension('WEBGL_debug_renderer_info');const renderer=info?gl.getParameter(info.UNMASKED_RENDERER_WEBGL):'';store.setState({quality:qualityFor({width:innerWidth,cores:navigator.hardwareConcurrency||4,memory:navigator.deviceMemory||4,renderer})});gl.getExtension('WEBGL_lose_context')?.loseContext();}
    setSupported(Boolean(gl));
    session.setFallback(!gl);
    const media=matchMedia('(prefers-reduced-motion: reduce)'),change=()=>store.setState({reduced:media.matches});media.addEventListener('change',change);
    const onKey=e=>{if(e.key==='Escape'&&!document.querySelector('#modalbg')){e.stopPropagation();store.getState().stage==='overview'?onClose():session.overview();}};
    document.addEventListener('keydown',onKey,true);
    return ()=>{media.removeEventListener('change',change);document.removeEventListener('keydown',onKey,true);};
  },[store,onClose]);
  useEffect(()=>{if(ready&&!started.current){started.current=true;if(session.initial&&session.initial!=='start')session.navigate(session.initial,true);}},[ready,session]);
  useEffect(()=>{if(supported===false){setReady(true);setList(true);}},[supported]);
  useEffect(()=>{
    if(tilt!=='on'||reduced)return;
    const handler=e=>store.setState({parallax:{x:THREE.MathUtils.clamp((e.gamma||0)/35,-1,1),y:THREE.MathUtils.clamp((e.beta||0)/45,-1,1)}});
    window.addEventListener('deviceorientation',handler);return ()=>{window.removeEventListener('deviceorientation',handler);store.setState({parallax:{x:0,y:0}});};
  },[tilt,reduced,store]);
  async function enableTilt(){
    if(!window.DeviceOrientationEvent){setTilt('unavailable');return;}
    try{const request=window.DeviceOrientationEvent.requestPermission;if(request&&await request.call(window.DeviceOrientationEvent)!=='granted'){setTilt('denied');return;}setTilt('on');}catch{setTilt('unavailable');}
  }
  const markReady=React.useCallback(()=>setReady(true),[]),fail=React.useCallback(()=>{session.setFallback(true);setSupported(false);},[session]);
  const open=id=>{if(modules.some(m=>m.id===id)){setList(false);session.navigate(id);}};
  return <div className={`cinema-world ${ready?'world-ready':''} ${reduced?'world-still':''}`} data-stage={stage} data-module={selected?.id||''} data-quality={quality} data-webgl={supported===true?'active':supported===false?'fallback':'checking'} role="dialog" aria-modal="true" aria-label="3D-portaal" onKeyDown={e=>{
    if(document.querySelector('#modalbg'))return;
    if(e.key!=='Tab')return;const focusable=[...e.currentTarget.querySelectorAll('button:not(:disabled),input,select')].filter(el=>el.getClientRects().length),first=focusable[0],last=focusable.at(-1);
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
  }}>
    {supported&&<RenderBoundary onFail={fail}><Canvas frameloop="demand" camera={{position:[22,19,37],fov:46,near:.2,far:180}} dpr={QUALITY[quality].dpr} gl={{antialias:quality==='high',alpha:false,powerPreference:'high-performance'}}
      onCreated={({gl})=>{gl.toneMapping=THREE.ACESFilmicToneMapping;gl.toneMappingExposure=1.25;gl.domElement.setAttribute('aria-label','3D-wereld met bedrijfsmodules');gl.domElement.addEventListener('webglcontextlost',fail,{once:true});}}
      fallback={null}><Suspense fallback={null}><WorldScene catalogue={catalogue} store={store} onOpen={open} onReady={markReady} session={session}/></Suspense></Canvas></RenderBoundary>}
    <div className="world-lens" aria-hidden="true"/>
    <div className="world-extras"><button onClick={()=>session.toggleSound()} aria-pressed={sound}>Geluid {sound?'aan':'uit'}</button><button onClick={()=>store.setState({flash:!flash})} disabled={reduced} aria-pressed={flash&&!reduced}>Flits {flash&&!reduced?'aan':'uit'}</button></div>
    {!reduced&&flash&&flashTick>0&&<div key={flashTick} className="world-flash" aria-hidden="true"/>}
    {stage!=='overview'&&<div className="world-workbar"><button onClick={()=>session.overview()}>← Terug naar wereld</button><span>{selected?.label||'Overzicht'}</span></div>}
    {['flying-in','flying-out'].includes(stage)&&<div className="world-flight-status" role="status">{stage==='flying-in'?'Onderweg naar '+selected?.label:'Terug naar het overzicht'}</div>}
    {error&&<div className="world-error" role="alert">{error}<button onClick={()=>selected?session.navigate(selected.id):session.overview()}>Opnieuw proberen</button><button onClick={()=>session.overview()}>Naar overzicht</button></div>}
    {supported===false&&['mounting','inside','exiting','flying-out'].includes(stage)&&<section className="world-module-panel world-fallback-panel" aria-label={'Werkruimte '+selected?.label}><LegacySlot session={session}/></section>}
    {!ready&&<div className="world-preloader" role="status"><span>AMOCEAN / ROEFS ONE</span><strong>Ruimte maken<br/>voor jouw werk.</strong><div className="world-load-line"/><small>De modulewereld wordt opgebouwd</small></div>}
    <header className="world-header"><div className="world-brand"><img src="/assets/amocean-mark.png?v=2" alt="Amocean"/><span>ROEFS ONE<small>SPATIAL OPERATING SPACE</small></span></div><div className="world-toolbar"><button onClick={()=>setList(!list)} aria-expanded={list} aria-controls="world-directory">Modules <span>{String(modules.length).padStart(2,'0')}</span></button><button onClick={onClose} autoFocus aria-label="Sluit 3D-portaal">Sluiten <span>×</span></button></div></header>
    <section className="world-intro"><p><i/> JOUW BEDRIJF, IN ÉÉN WERELD</p><h1>Alles verbonden.<br/><em>Alle ruimte.</em></h1><span>{supported===false?'3D is niet beschikbaar op dit apparaat. Alle modules blijven hieronder bereikbaar.':'Elke ruimte is een onderdeel van je werk. Kies waar je begint.'}</span></section>
    <nav id="world-directory" className={`world-directory ${list?'is-open':''}`} aria-label="Alle beschikbare modules" hidden={!list}><label>Zoek een module<input value={query} onChange={e=>setQuery(e.target.value)} type="search" placeholder="Bijvoorbeeld planning"/></label>{catalogue.map(group=><section key={group.label}><h2>{group.label}</h2>{group.modules.filter(m=>m.label.toLocaleLowerCase('nl').includes(query.toLocaleLowerCase('nl'))).map(m=><button key={m.id} onMouseEnter={()=>store.setState({hovered:m.id})} onMouseLeave={()=>store.setState({hovered:null})} onFocus={()=>store.setState({hovered:m.id})} onBlur={()=>store.setState({hovered:null})} onClick={()=>open(m.id)} data-world-module={m.id}><small>{String(m.district+1).padStart(2,'0')}.{String(m.index+1).padStart(2,'0')}</small>{m.label}<span>↗</span></button>)}</section>)}</nav>
    <footer className="world-footer"><div className="world-coordinates"><span>ROEFS / CONTROL ROOM</span><small>{supported===false?'TOEGANKELIJKE MODULELIJST':`REALTIME 3D · ${quality==='high'?'HOOG':quality==='medium'?'GEBALANCEERD':'LICHT'}`}</small></div><div className="world-hover" aria-live="polite">{current?<><small>RUIMTE {String(current.district+1).padStart(2,'0')}.{String(current.index+1).padStart(2,'0')}</small><strong>{current.label}</strong><span>Klik om te openen ↗</span></>:<><small>VERKEN DE WERELD</small><strong>Kies je volgende stap.</strong><span>Beweeg over een object of open de modulelijst.</span></>}</div><div className="world-motion"><select aria-label="Weergavekwaliteit" value={quality} onChange={e=>store.setState({quality:e.target.value})}><option value="high">Hoog</option><option value="medium">Gebalanceerd</option><option value="low">Licht</option></select><button onClick={()=>store.setState({reduced:!reduced})} aria-pressed={reduced}>{reduced?'Beweging uit':'Beweging aan'}</button><button onClick={tilt==='on'?()=>setTilt('off'):enableTilt} disabled={reduced||tilt==='unavailable'} aria-pressed={tilt==='on'}>Kantelen {tilt==='on'?'aan':tilt==='denied'?'geweigerd':tilt==='unavailable'?'niet beschikbaar':'uit'}</button></div></footer>
  </div>;
}

export function mountWorld(options) {
  const session=new WorldSession(options),host=document.createElement('div');host.className='cinema-mount';document.body.append(host);
  const react=createRoot(host),close=()=>session.dispose();
  session.unmount=()=>{react.unmount();host.remove();};
  react.render(<World session={session} onClose={close}/>);
  return session;
}
