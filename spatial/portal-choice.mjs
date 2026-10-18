// Presentation only: authentication and access checks remain in the original portal.
export class PortalChoice {
  constructor({root,onOld,onNew,onLogout}) {
    this.root=root;this.previousFocus=document.activeElement;
    this.previousInert=root.inert;this.previousHidden=root.getAttribute('aria-hidden');
    this.host=document.createElement('section');this.host.className='portal-choice-screen';
    this.host.setAttribute('role','dialog');this.host.setAttribute('aria-modal','true');this.host.setAttribute('aria-labelledby','portal-choice-title');
    this.host.innerHTML=`<div class="portal-choice-content">
      <header class="portal-choice-brand"><img src="/assets/amocean-mark.png?v=2" alt="Amocean"><span>ROEFS ONE</span></header>
      <p class="portal-choice-eyebrow">Jouw werk. Jouw omgeving.</p><h1 id="portal-choice-title">Kies je portaal</h1>
      <p class="portal-choice-intro">Dezelfde gegevens en mogelijkheden, in de omgeving die bij je past.</p>
      <div class="portal-choice-options">
        <button type="button" class="portal-choice-card" data-portal-choice="old" aria-labelledby="portal-old-title">
          <span class="portal-choice-preview portal-preview-old" aria-hidden="true"><i></i><span><b></b><b></b><b></b><em></em></span></span>
          <small>Vertrouwd werken</small><strong id="portal-old-title">Oud Portaal</strong><span>Het vertrouwde dashboard met je bestaande menu, planning en werkfuncties.</span><em>Open Oud Portaal <span aria-hidden="true">&rarr;</span></em>
        </button>
        <button type="button" class="portal-choice-card portal-choice-new" data-portal-choice="new" aria-labelledby="portal-new-title">
          <span class="portal-choice-preview portal-preview-new" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>
          <small>Ontdek de 3D-wereld</small><strong id="portal-new-title">Nieuw Portaal</strong><span>Navigeer door de 3D-wereld en open je werkfuncties met een cameravlucht.</span><em>Open Nieuw Portaal <span aria-hidden="true">&rarr;</span></em>
        </button>
      </div>
      <footer><span>Je kunt later van portaal wisselen.</span><button type="button" data-portal-logout>Uitloggen</button></footer>
    </div>`;
    root.inert=true;root.setAttribute('aria-hidden','true');root.classList.add('portal-choice-pending');document.body.append(this.host);
    this.host.querySelector('[data-portal-choice=old]').addEventListener('click',onOld);
    this.host.querySelector('[data-portal-choice=new]').addEventListener('click',onNew);
    this.host.querySelector('[data-portal-logout]').addEventListener('click',onLogout);
    this.host.addEventListener('keydown',event=>{
      if(event.key!=='Tab')return;
      const buttons=[...this.host.querySelectorAll('button')],first=buttons[0],last=buttons.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    });
    this.host.querySelector('[data-portal-choice=old]').focus();
  }
  dispose(){
    this.host.remove();this.root.inert=this.previousInert;this.root.classList.remove('portal-choice-pending');
    if(this.previousHidden===null)this.root.removeAttribute('aria-hidden');else this.root.setAttribute('aria-hidden',this.previousHidden);
    if(this.previousFocus?.isConnected&&!this.root.inert)this.previousFocus.focus({preventScroll:true});
  }
}
