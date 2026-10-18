import React,{useEffect,useMemo,useRef} from 'react';
import {Html} from '@react-three/drei';
import {useThree} from '@react-three/fiber';
import {useStore} from 'zustand';
import gsap from 'gsap';
import * as THREE from 'three';

// All lightweight bodies and labels use just two instanced draw calls.
export function LowMonoliths({all,store,onOpen,signTexture,colours}){
  const invalidate=useThree(s=>s.invalidate);
  const body=useRef(),signs=useRef(),hovered=useStore(store,s=>s.hovered),reduced=useStore(store,s=>s.reduced);
  const offsets=useMemo(()=>all.map(()=>({y:0})),[all]);
  const resources=useMemo(()=>{
    const rows=Math.max(1,Math.ceil(all.length/8)),height=2**Math.ceil(Math.log2(rows*128));
    const canvas=document.createElement('canvas');canvas.width=2048;canvas.height=height;const ctx=canvas.getContext('2d'),rects=[];
    all.forEach((m,i)=>{const t=signTexture(m);ctx.drawImage(t.image,i%8*256,Math.floor(i/8)*128,256,128);t.dispose();rects.push(i%8/8,1-(Math.floor(i/8)+1)*128/height,1/8,128/height);});
    const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
    const geometry=new THREE.PlaneGeometry(1.62,.81);geometry.setAttribute('atlasRect',new THREE.InstancedBufferAttribute(new Float32Array(rects),4));
    const material=new THREE.MeshBasicMaterial({map:texture,toneMapped:false});
    material.onBeforeCompile=shader=>{shader.vertexShader='attribute vec4 atlasRect;\n'+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <uv_vertex>','#include <uv_vertex>\n#ifdef USE_MAP\nvMapUv = vMapUv * atlasRect.zw + atlasRect.xy;\n#endif');};
    return {texture,geometry,material,box:new THREE.BoxGeometry(1.76,1,.92)};
  },[all,signTexture]);
  const update=index=>{
    if(!body.current||!signs.current)return;const m=all[index],angle=m.variant===1?-.12:m.variant===2?.12:0,q=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),angle),lift=offsets[index].y;
    body.current.setMatrixAt(index,new THREE.Matrix4().compose(new THREE.Vector3(m.position[0],m.height/2+lift,m.position[2]),q,new THREE.Vector3(1,m.height,1)));
    const p=new THREE.Vector3(0,m.height*.65,.474).applyQuaternion(q).add(new THREE.Vector3(...m.position));p.y+=lift;
    signs.current.setMatrixAt(index,new THREE.Matrix4().compose(p,q,new THREE.Vector3(1,1,1)));
    body.current.setColorAt(index,new THREE.Color(hovered===m.id?'#fff3d6':colours[m.district%7]));body.current.instanceMatrix.needsUpdate=true;signs.current.instanceMatrix.needsUpdate=true;if(body.current.instanceColor)body.current.instanceColor.needsUpdate=true;invalidate();
  };
  useEffect(()=>{all.forEach((_,i)=>update(i));body.current?.computeBoundingSphere();signs.current?.computeBoundingSphere();},[all,resources]);
  useEffect(()=>{const tweens=[];all.forEach((m,i)=>{const y=m.id===hovered?.17:0;if(Math.abs(offsets[i].y-y)>.001)tweens.push(gsap.to(offsets[i],{y,duration:reduced?0:.35,onUpdate:()=>update(i)}));update(i);});return ()=>tweens.forEach(t=>t.kill());},[hovered,reduced,all]);
  useEffect(()=>()=>{resources.texture.dispose();resources.geometry.dispose();resources.material.dispose();resources.box.dispose();},[resources]);
  const events={onPointerOver:e=>{e.stopPropagation();store.setState({hovered:all[e.instanceId]?.id||null});},onPointerOut:()=>store.setState({hovered:null}),onClick:e=>{e.stopPropagation();const m=all[e.instanceId];if(m)onOpen(m.id);}};
  const selected=all.find(m=>m.id===hovered);
  return <><instancedMesh ref={body} args={[resources.box,undefined,all.length]} {...events}><meshPhongMaterial color="#ffffff" specular="#8c887c" shininess={65}/></instancedMesh><instancedMesh ref={signs} args={[resources.geometry,resources.material,all.length]} {...events}/>{selected&&<Html position={[selected.position[0],selected.height+.6,selected.position[2]]} center style={{pointerEvents:'none'}}><span className="world-object-label">{selected.label}</span></Html>}</>;
}
