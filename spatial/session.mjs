import {createStore} from 'zustand/vanilla';
import {WorldSound} from './sound.mjs';
import {moduleWorld,qualityFor} from './world-model.mjs';
import {installSpatialDrag} from './drag.mjs';

export function worldUrl(id='start',enabled=true){const url=new URL(location.href);enabled?url.searchParams.set('ruimte','1'):url.searchParams.delete('ruimte');url.hash=id;return url.pathname+url.search+url.hash;}

// Single coordinator: old router renders the same root, camera owns presentation only.
export class WorldSession {
  constructor({groups,names,visible,renderPage,currentPage,onClose,initial=null,navigationEpoch=()=>0,canRestore=()=>true}){
    this.catalogue=moduleWorld(groups,names,visible);this.modules=this.catalogue.flatMap(g=>g.modules);this.visible=visible;this.renderPage=renderPage;this.currentPage=currentPage;this.onClose=onClose;this.initial=initial;
    this.navigationEpoch=navigationEpoch;this.canRestore=canRestore;
    this.root=document.querySelector('#root');this.marker=document.createComment('roefs-root-location');this.root.before(this.marker);this.previousFocus=document.activeElement;this.closed=false;this.serial=0;this.flightKey=0;this.queue=Promise.resolve();this.pending=null;this.slot=null;this.sound=new WorldSound();
    this.stopDrag=installSpatialDrag(this.root);
    this.store=createStore(()=>({hovered:null,selected:null,stage:'overview',flight:null,error:'',sound:false,flash:true,flashTick:0,quality:qualityFor({width:innerWidth,cores:navigator.hardwareConcurrency||4,memory:navigator.deviceMemory||4}),reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,parallax:{x:0,y:0},fps:null}));
    this.park();
    if(!initial)history.pushState({roefsPage:'start',spatialWorld:true,spatialOverview:true},'',worldUrl());
    else history.replaceState({roefsPage:initial,spatialWorld:true,spatialOverview:initial==='start'},'',worldUrl(initial));
  }
  park(){if(this.closed)return;this.mountWaiter?.resolve(false);this.mountWaiter=null;this.slot=null;this.root.inert=true;this.root.classList.add('world-parked');document.body.append(this.root);}
  attach(slot){if(!slot?.isConnected||this.closed)return;this.slot=slot;if(['mounting','inside'].includes(this.store.getState().stage)){this.root.classList.remove('world-parked');slot.append(this.root);this.root.inert=Boolean(document.querySelector('#modalbg'));this.store.setState({stage:'inside'});this.mountWaiter?.resolve(true);this.mountWaiter=null;}}
  pulse(){const s=this.store.getState();if(!s.reduced&&s.flash&&performance.now()-(this.lastFlash||-3000)>1800){this.lastFlash=performance.now();this.store.setState({flashTick:s.flashTick+1});this.sound.play('click');}}
  finishFlight(key){if(this.pending?.key!==key)return;this.motionProgress=1;this.pending.resolve(true);this.pending=null;}
  flight(mode,module){
    this.motionProgress=0;
    this.pending?.resolve(false);const key=++this.flightKey;
    return new Promise(resolve=>{this.pending={key,resolve};this.store.setState({flight:{key,mode,module},stage:mode==='out'?'flying-out':'flying-in',error:''});this.sound.play('flight');this.pulse();if(this.fallback)queueMicrotask(()=>this.finishFlight(key));});
  }
  render(id,serial){
    const task=this.queue.catch(()=>{}).then(async()=>{if(this.closed||serial!==this.serial)return false;await this.renderPage(id,true);return !this.closed&&serial===this.serial&&this.currentPage()===id;});this.queue=task;return task;
  }
  async navigate(id,fromHistory=false){
    if(this.closed)return;
    if(fromHistory&&(!history.state?.spatialWorld||!new URL(location.href).searchParams.has('ruimte'))){this.dispose({preserveUrl:true});return this.renderPage(id,true);}
    if(fromHistory&&history.state?.spatialOverview)return this.overview(false);
    const module=this.modules.find(m=>m.id===id);if(!module||!this.visible(id)){this.store.setState({error:'Geen toegang tot deze module.'});return;}
    this.destination=id;
    const serial=++this.serial,state=this.store.getState(),same=state.stage==='inside'&&state.selected?.id===id;
    if(!fromHistory&&!same)history.pushState({roefsPage:id,spatialWorld:true,spatialOverview:false},'',worldUrl(id));
    else history.replaceState({...history.state,roefsPage:id,spatialWorld:true,spatialOverview:false},'',worldUrl(id));
    if(!same&&state.stage==='inside'&&!state.reduced){this.root.inert=true;this.store.setState({stage:'exiting'});await new Promise(r=>setTimeout(r,120));if(this.closed||serial!==this.serial)return;}
    if(!same){this.park();this.store.setState({selected:module,hovered:null});}
    try{
      const [rendered,arrived]=await Promise.all([this.render(id,serial),same?Promise.resolve(true):this.flight('in',module)]);
      if(this.closed||serial!==this.serial)return;
      if(!rendered||!arrived){this.store.setState({error:'De module kon niet worden geopend. Probeer opnieuw.',stage:'error'});return;}
      const mounted=await new Promise(resolve=>{this.mountWaiter={serial,resolve};this.store.setState({stage:'mounting',flight:null,error:''});this.attach(this.slot);});
      if(!mounted||this.closed||serial!==this.serial)return;
      this.sound.play('arrival');this.pulse();
      requestAnimationFrame(()=>{if(!this.closed&&serial===this.serial)this.root.querySelector('h1,h2,input,button')?.focus({preventScroll:true});});
    }catch(error){if(!this.closed&&serial===this.serial)this.store.setState({stage:'error',error:error.message});}
  }
  async overview(push=true){
    if(this.closed)return;const serial=++this.serial,previous=this.store.getState().selected;this.destination='start';this.root.inert=true;
    if(push)history.pushState({roefsPage:'start',spatialWorld:true,spatialOverview:true},'',worldUrl());
    const arrived=this.flight('out',previous);
    const render=(async()=>{if(!this.store.getState().reduced)await new Promise(r=>setTimeout(r,120));if(this.closed||serial!==this.serial)return;this.park();return this.render('start',serial);})();
    await Promise.all([arrived,render]);
    if(!this.closed&&serial===this.serial)this.store.setState({stage:'overview',selected:null,flight:null,hovered:null,error:''});
  }
  setFallback(value){this.fallback=value;if(value){this.park();if(this.pending)this.finishFlight(this.pending.key);}}
  async toggleSound(){const enabled=await this.sound.enable(!this.store.getState().sound);if(!this.closed){this.store.setState({sound:enabled});if(enabled)this.sound.play('arrival');}}
  dispose({preserveUrl=false,restorePending=true}={}){
    if(this.closed)return;this.closed=true;++this.serial;this.pending?.resolve(false);this.pending=null;this.mountWaiter?.resolve(false);this.mountWaiter=null;this.sound.dispose();this.stopDrag();
    const desired=this.destination||this.store.getState().selected?.id||this.currentPage(),epoch=this.navigationEpoch(),pending=this.queue;
    this.root.classList.remove('world-parked');this.marker.replaceWith(this.root);this.root.inert=Boolean(document.querySelector('#modalbg'));
    if(!preserveUrl)history.replaceState({roefsPage:desired},'',worldUrl(desired,false));this.unmount?.();this.previousFocus?.isConnected&&this.previousFocus.focus({preventScroll:true});this.onClose?.();
    if(!preserveUrl&&restorePending)pending.catch(()=>{}).then(()=>{if(this.canRestore()&&epoch===this.navigationEpoch()&&this.currentPage()!==desired)return this.renderPage(desired,true);}).catch(()=>{});
  }
}
