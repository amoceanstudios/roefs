import {setupSpatial,handleSpatialPop} from './index.js';
// Capture the original fragment before the unchanged legacy cookie boot resets it.
const entry=new URL(location.href);
window.addEventListener('popstate',handleSpatialPop,true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setupSpatial(entry),{once:true});
else setupSpatial(entry);
