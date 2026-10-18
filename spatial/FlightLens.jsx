import React,{useEffect,useMemo} from 'react';
import {useFrame} from '@react-three/fiber';
import {Effect,EffectAttribute} from 'postprocessing';
import {Uniform} from 'three';

export function FlightLens({session,store}){
  const effect=useMemo(()=>new Effect('FlightLens',`uniform float strength;void mainImage(const in vec4 inputColor,const in vec2 uv,out vec4 outputColor){if(strength<0.0001){outputColor=inputColor;return;}vec2 d=(uv-0.5)*strength;vec3 c=inputColor.rgb*0.4;for(int i=1;i<=3;i++){c+=texture2D(inputBuffer,uv-d*float(i)).rgb*0.2;}outputColor=vec4(c,inputColor.a);}`,{attributes:EffectAttribute.CONVOLUTION,uniforms:new Map([['strength',new Uniform(0)]])}),[]);
  useFrame(()=>{const s=store.getState();effect.uniforms.get('strength').value=!s.reduced&&s.stage.startsWith('flying')?Math.sin((session.motionProgress||0)*Math.PI)*.006:0;});
  useEffect(()=>()=>effect.dispose(),[effect]);return <primitive object={effect}/>;
}
