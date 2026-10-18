import {test} from 'node:test';
import assert from 'node:assert/strict';
import {moduleWorld,qualityFor,QUALITY,cameraNoise,workspacePose,entryPoints} from './world-model.mjs';

test('every permitted module maps to exactly one object with its existing route and label',()=>{
  const groups={Daily:['start','planning','hours'],Clients:['crm','planning'],Finance:['invoices']},names={planning:'Planning',crm:'Klanten'};
  const snapshot=JSON.stringify(groups),world=moduleWorld(groups,names,id=>id!=='hours');
  const modules=world.flatMap(g=>g.modules);
  assert.deepEqual(modules.map(m=>m.id),['start','planning','crm','invoices']);
  assert.equal(modules.find(m=>m.id==='planning').label,'Planning');
  assert.equal(new Set(modules.map(m=>m.position.join(','))).size,modules.length);
  assert.equal(JSON.stringify(groups),snapshot);
});
test('empty or completely unauthorized groups produce no objects',()=>{
  assert.deepEqual(moduleWorld({Admin:['settings']},{},()=>false),[]);
  assert.deepEqual(moduleWorld({},{},()=>true),[]);
});
test('quality lowers cost for software rendering, mobile and constrained memory',()=>{
  assert.equal(qualityFor({renderer:'Google SwiftShader'}),'low');
  assert.equal(qualityFor({width:390}),'medium');
  assert.equal(qualityFor({memory:2}),'low');
  assert.equal(qualityFor({width:1440,cores:8,memory:8,renderer:'Hardware GPU'}),'high');
  assert(QUALITY.low.dpr<QUALITY.medium.dpr&&QUALITY.medium.dpr<QUALITY.high.dpr);
  assert.equal(QUALITY.low.post,false);
});
test('handheld noise is bounded, continuous at integer times and deterministic',()=>{
  for(let t=0;t<20;t+=.01)assert(Math.abs(cameraNoise(t))<=1);
  assert(Math.abs(cameraNoise(1-.0001)-cameraNoise(1+.0001))<.0001);
  assert.equal(cameraNoise(2.3,5),cameraNoise(2.3,5));
});
test('authored entry paths have a lateral arc and settle at the module workspace',()=>{
  const module={position:[12,0,-8],height:4,district:2,index:3},snapshot=JSON.stringify(module),start=[22,19,37];
  const points=entryPoints(module,start),pose=workspacePose(module);
  assert.deepEqual(points[0],start);assert.deepEqual(points.at(-1),pose.camera);
  assert(points.every(p=>p.every(Number.isFinite)));
  assert.notEqual(points[1][0],start[0]*.62+pose.camera[0]*.38);
  assert(points.at(-2)[2]<pose.camera[2]);assert.equal(JSON.stringify(module),snapshot);
});
