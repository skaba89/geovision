(()=>{
  const form=document.querySelector('#quote'), result=document.querySelector('#result');
  const submit=form.querySelector('[type=submit]'), nav=document.querySelector('.links'), menu=document.querySelector('.menu');
  const closeMenu=()=>{nav.classList.remove('open');menu.setAttribute('aria-expanded','false')};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav.classList.contains('open')){closeMenu();menu.focus()}});
  const requested=new URLSearchParams(location.search).get('service'), choice=form.elements.service;
  if(requested&&Array.from(choice.options).some(o=>o.value===requested))choice.value=requested;
  for(const field of form.querySelectorAll('input,textarea'))field.maxLength=field.name==='projet'?4000:250;
  for(const b of form.querySelectorAll('button[type=button]'))b.remove();
  const trap=document.createElement('input');trap.name='website';trap.tabIndex=-1;trap.autocomplete='off';trap.setAttribute('aria-hidden','true');trap.style.cssText='position:absolute;left:-10000px';form.append(trap);
  submit.textContent='Envoyer ma demande';
  form.querySelector('.note').textContent='Vos informations seront utilisées uniquement pour traiter votre demande. Consultez les informations de confidentialité en pied de page.';
  let busy=false;
  form.onsubmit=async(e)=>{
    e.preventDefault();if(busy||!form.reportValidity())return;
    busy=true;const body=Object.fromEntries(new FormData(form));const fields=Array.from(form.elements);
    fields.forEach(x=>x.disabled=true);submit.textContent='Envoi en cours…';result.classList.remove('hide');result.textContent='Transmission de votre demande…';
    try{
      const r=await fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const data=await r.json();if(!r.ok)throw Error(data.error||'Envoi impossible.');
      form.reset();
      form.after(result);form.hidden=true;form.style.display='none';
      result.style.cssText='padding:28px;border-radius:12px;background:#e7f4dc;color:#14313c';
      result.replaceChildren();
      const title=document.createElement('h3');title.textContent='Votre demande a bien été reçue !';
      const details=document.createElement('p');details.textContent='Référence : '+data.reference+'. '+(data.acknowledgement_sent?'Un accusé de réception vous a été envoyé par e-mail.':'L’accusé de réception par e-mail n’a pas pu être envoyé. Conservez votre référence.')+' GeoVision vous répondra dans les meilleurs délais.';
      const again=document.createElement('button');again.type='button';again.className='btn dark';again.textContent='Nouvelle demande';
      again.onclick=()=>{result.classList.add('hide');result.removeAttribute('style');result.replaceChildren();form.append(result);form.hidden=false;form.style.removeProperty('display');form.querySelector('input').focus()};
      result.append(title,details,again);result.tabIndex=-1;result.focus();
    }catch(e){result.textContent='Votre demande n’a pas été confirmée. '+e.message+' Merci de réessayer.'}
    finally{busy=false;fields.forEach(x=>x.disabled=false);submit.textContent='Envoyer ma demande'}
  };
})();
