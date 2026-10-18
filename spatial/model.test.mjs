import {test} from 'node:test';
import assert from 'node:assert/strict';
import {universe,related} from './model.mjs';

test('800 customers occupy distinct finite positions with stable record identity',()=>{
  const data={customers:Array.from({length:800},(_,i)=>({id:i+1,name:`Klant ${i+1}`}))};
  const nodes=universe(data);
  assert.equal(nodes.length,800);
  assert.equal(new Set(nodes.map(n=>n.position.join(','))).size,800);
  assert(nodes.every(n=>n.position.every(Number.isFinite)));
  assert.equal(nodes[799].record,data.customers[799]);
});
test('connections use persisted customer and location references, never names',()=>{
  const data={customers:[{id:1,name:'Dezelfde naam'},{id:2,name:'Dezelfde naam'}],objects:[{id:10,customer_id:'1'}],workorders:[{id:5,object_id:'10'}],invoices:[{id:7,customer_id:'1'},{id:8,customer_id:2}]};
  assert.deepEqual(related(universe(data)[0],data).map(n=>n.key),['workorders:5','invoices:7']);
});
test('urgency and financial height reflect data without changing records',()=>{
  const r={id:1,amount:'128',due_date:'2000-01-01',status:'Open'};
  const before=JSON.stringify(r),node=universe({invoices:[r]})[0];
  assert.equal(node.urgent,true);assert(node.position[1]>1);assert.equal(JSON.stringify(r),before);
  assert.equal(universe({invoices:[{...r,status:'Betaald'}]})[0].urgent,false);
  assert.deepEqual(universe({}),[]);
});
