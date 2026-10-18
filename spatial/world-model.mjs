// Presentation-only catalogue. Route IDs, labels and visibility come from the portal.
const CENTERS=[[-12,6],[0,1],[12,6],[-12,-8],[0,-11],[12,-8],[0,-24]];
export function moduleWorld(groups,names,visible) {
  const seen=new Set();
  return Object.entries(groups).map(([label,ids],district)=>({
    label,district,center:CENTERS[district]||[district*12,-24],
    modules:ids.filter(id=>!seen.has(id)&&visible(id)&&(seen.add(id),true)).map((id,i)=>({
      id,label:names[id]||id,district,index:i,
      position:[(CENTERS[district]?.[0]||0)+(i%3-1)*2.65,0,(CENTERS[district]?.[1]||0)+Math.floor(i/3)*2.9],
      height:2.6+((i*7+district*3)%5)*.48,
      variant:(district+i)%3
    }))
  })).filter(group=>group.modules.length);
}
export function qualityFor({width=1440,cores=8,memory=8,renderer=''}={}) {
  if(/swiftshader|llvmpipe|software/i.test(renderer)||cores<=2||memory<=2) return 'low';
  return width<760||cores<=4||memory<=4?'medium':'high';
}
export const QUALITY={high:{dpr:1.5,post:true,dof:true},medium:{dpr:1,post:true,dof:false},low:{dpr:.75,post:false,dof:false}};
// Smooth deterministic value noise for tiny handheld offsets, independent of frame rate.
export function cameraNoise(time,seed=1) {
  const n=Math.floor(time),f=time-n,s=f*f*(3-2*f);
  const hash=x=>{const value=Math.sin(x*127.1+seed*311.7)*43758.5453;return (value-Math.floor(value))*2-1;};
  return hash(n)*(1-s)+hash(n+1)*s;
}
export function workspacePose(module){const [x,,z]=module.position,y=module.height*.65;return {target:[x,y,z+1.4],camera:[x,y,z+9.4]};}
export function entryPoints(module,start){
  const {camera:end}=workspacePose(module),arc=(module.district%2?1:-1)*(2.5+module.index*.08);
  return [start,[start[0]*.62+end[0]*.38+arc,start[1]*.6+end[1]*.4+1.4,start[2]*.62+end[2]*.38],[end[0]-arc*.3,end[1]+.6,end[2]+3.7],[end[0],end[1],end[2]-.12],end];
}
