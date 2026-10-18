// Optional local sound design. No audio starts before a user gesture.
export class WorldSound {
  constructor(){this.enabled=false;this.context=null;}
  async enable(enabled){
    if(!enabled){this.enabled=false;return false;}
    const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio)return false;
    try{this.context??=new Audio();await this.context.resume();this.enabled=this.context.state==='running';return this.enabled;}catch{return false;}
  }
  play(kind){
    window.dispatchEvent(new CustomEvent('roefs:world-sound',{detail:{kind,enabled:this.enabled}}));
    if(!this.enabled||this.context?.state!=='running')return;
    const c=this.context,t=c.currentTime,g=c.createGain();g.connect(c.destination);
    if(kind==='flight'){
      const buffer=c.createBuffer(1,Math.floor(c.sampleRate*.45),c.sampleRate),d=buffer.getChannelData(0);
      for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;
      const source=c.createBufferSource(),filter=c.createBiquadFilter();filter.type='bandpass';filter.Q.value=.6;filter.frequency.setValueAtTime(1200,t);filter.frequency.exponentialRampToValueAtTime(300,t+.45);
      source.buffer=buffer;source.connect(filter);filter.connect(g);g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.065,t+.12);g.gain.exponentialRampToValueAtTime(.0001,t+.45);source.start(t);source.stop(t+.46);
      source.onended=()=>{source.disconnect();filter.disconnect();g.disconnect();};
    }else{
      const o=c.createOscillator();o.type='sine';o.frequency.setValueAtTime(kind==='arrival'?660:880,t);o.connect(g);g.gain.setValueAtTime(.028,t);g.gain.exponentialRampToValueAtTime(.0001,t+.07);o.start(t);o.stop(t+.08);o.onended=()=>{o.disconnect();g.disconnect();};
    }
  }
  dispose(){this.enabled=false;this.context?.close().catch(()=>{});this.context=null;}
}
