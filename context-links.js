/* Explicit per-record links. No fuzzy matching and no programmatic saving. */
(()=>{
 const q=new URLSearchParams(location.search),company=q.get('company'),record=q.get('record');
 const menu=document.querySelector('.ui-menu');if(menu)menu.onclick=()=>{const open=document.querySelector('.ui-shell').classList.toggle('nav-open');menu.setAttribute('aria-expanded',String(open))};
 const p=location.pathname;
 if(p!=='/operations'&&(company||record)){const bar=document.createElement('div');bar.className='ui-context';const a=document.createElement('a');a.href='/operations?'+new URLSearchParams({view:'account',company:company||''});a.textContent=company?'Account context: '+company:'Return to operations accounts';bar.append(a);const note=document.createElement('span');note.textContent='Direct source view. Save here; planning never upgrades evidence.';bar.append(note);document.querySelector('.ui-shell')?.after(bar)}
 if(!company&&!record)return;
 function missing(){const b=document.querySelector('.ui-context');if(b)b.append(document.createTextNode(' Requested record is not available in this source. No matching record was selected.'))}
 let n=0;
 const timer=setInterval(()=>{if(window.FormSafety?.hasUnsaved()){clearInterval(timer);return}if(++n>100){clearInterval(timer);return}try{
  if(p==='/committee'&&typeof data!=='undefined'&&data?.accounts){let a=data.accounts.find(x=>x.company===company);if(a){current=a.id;renderList();renderDetail()}else{current=null;renderDetail();missing()}clearInterval(timer)}
  else if(p==='/hospitals'&&typeof data!=='undefined'&&data?.hospitals){if(data.hospitals.some(x=>x.id===record)){current=record;paintList();paintDetail()}else{current=null;paintDetail();missing()}clearInterval(timer)}
  else if(p==='/reviews'&&typeof data!=='undefined'&&data?.accounts){if(data.accounts.some(x=>x.company===company)){selected=company;drawList();drawDetail()}else{selected=null;drawDetail();missing()}clearInterval(timer)}
  else if(p==='/crm'&&typeof data!=='undefined'&&data?.accounts){const a=data.accounts.find(x=>x.company===company);if(q.get('space')==='simulation'&&space!=='simulation'){space='simulation';data=null;load();return}if(a){selected=a.id;render()}else{selected=null;detail();missing()}clearInterval(timer)}
  else if(p==='/'&&typeof apiState!=='undefined'&&apiState?.work){const sel=document.querySelector('#wcompany');if([...sel.options].some(o=>o.value===company)){sel.value=company;loadWork()}else{sel.value="";document.querySelector("#workForm").inert=true;missing()}clearInterval(timer)}
 }catch(e){clearInterval(timer);console.warn('Direct record context unavailable')}} ,100);
})();

/* Return to the exact redesigned account context after a source edit. */
(()=>{try{const raw=sessionStorage.getItem('cgt-workspace-return');if(!raw)return;const u=new URL(raw,location.origin);if(u.origin!==location.origin||!['/home','/accounts','/sites','/delivery','/reports'].includes(u.pathname))return;const a=document.querySelector('.ui-local a');if(a){a.href=u.pathname+u.search;a.textContent='Return to workspace →'}}catch{}})();
