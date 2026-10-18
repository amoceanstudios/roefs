// Pointer drag adapter for CSS3D and touch. Reuses the portal's existing actions.
export function installSpatialDrag(root){
  const abort=new AbortController(),options={signal:abort.signal},state={drag:null,suppressUntil:0};
  const clean=()=>{const d=state.drag;if(!d)return;try{if(d.source.hasPointerCapture?.(d.pointer))d.source.releasePointerCapture(d.pointer);}catch{}d.source.classList.remove('world-drag-source');d.target?.classList.remove('world-drop-target');d.ghost?.remove();state.drag=null;};
  root.addEventListener('pointerdown',event=>{
    const source=event.target.closest('[draggable=true][data-roefs-dragstart]');if(!source||event.button!==0)return;
    event.preventDefault();source.setPointerCapture?.(event.pointerId);
    state.drag={source,x:event.clientX,y:event.clientY,pointer:event.pointerId,active:false};
  },options);
  root.addEventListener('pointermove',event=>{
    const d=state.drag;if(!d||event.pointerId!==d.pointer)return;
    if(!d.active&&Math.hypot(event.clientX-d.x,event.clientY-d.y)>8){
      d.active=true;try{d.transfer=new DataTransfer();}catch{const data={};d.transfer={setData:(k,v)=>data[k]=v,getData:k=>data[k]||''};}
      roefsAction(d.source.dataset.roefsDragstart,{dataTransfer:d.transfer},d.source);
      d.source.classList.add('world-drag-source');d.ghost=document.createElement('div');d.ghost.className='world-drag-ghost';d.ghost.textContent=d.source.innerText;document.body.append(d.ghost);
    }
    if(!d.active)return;event.preventDefault();d.ghost.style.transform=`translate(${event.clientX+12}px,${event.clientY+12}px)`;
    const target=document.elementFromPoint(event.clientX,event.clientY)?.closest('[data-roefs-drop]');d.target?.classList.remove('world-drop-target');d.target=root.contains(target)?target:null;d.target?.classList.add('world-drop-target');
  },options);
  root.addEventListener('pointerup',event=>{
    const d=state.drag;if(!d||event.pointerId!==d.pointer)return;state.suppressUntil=performance.now()+700;
    try{d.source.releasePointerCapture?.(event.pointerId);}catch{}
    if(d.active&&d.target){try{Promise.resolve(roefsAction(d.target.dataset.roefsDrop,{dataTransfer:d.transfer,preventDefault(){}},d.target)).catch(e=>toast(e.message));}catch(e){toast(e.message);}}
    else if(!d.active)d.source.click();clean();
  },options);
  root.addEventListener('pointercancel',clean,options);
  window.addEventListener('click',event=>{if(event.isTrusted&&root.contains(event.target)&&performance.now()<state.suppressUntil){event.preventDefault();event.stopImmediatePropagation();}},{...options,capture:true});
  return ()=>{abort.abort();clean();};
}
