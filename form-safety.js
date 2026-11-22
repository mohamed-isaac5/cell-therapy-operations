/* Unsaved-input safety only. No autosave, persistence, network or business rules. */
(()=>{
 const dirty=new Set(),values=new WeakMap(),pending=new Set(),canceledInput=new WeakSet();
 const connected=()=>[...dirty].filter(f=>f.isConnected);
 const snapshot=e=>e.type==='checkbox'||e.type==='radio'?e.checked:e.value;
 const remember=e=>{if(e.matches?.('input,select,textarea'))values.set(e,snapshot(e))};
 const rememberAll=()=>document.querySelectorAll('input,select,textarea').forEach(e=>{if(!values.has(e))remember(e)});
 function confirmDiscard(except){if(pending.size){window.alert('A save is in progress. Wait for it to finish before changing the view.');return false}const forms=connected().filter(f=>f!==except);if(!forms.length)return true;if(!window.confirm('You have unsaved changes. Discard them and continue? Nothing has been saved.'))return false;forms.forEach(f=>dirty.delete(f));return true}
 function stop(e){e.preventDefault();e.stopImmediatePropagation()}
 document.addEventListener('focusin',e=>remember(e.target),true);
 for(const type of ['input','change'])document.addEventListener(type,e=>{
  const el=e.target;if(!el.matches?.('input,select,textarea'))return;
  if(type==='change'&&canceledInput.has(el)){canceledInput.delete(el);stop(e);return}if(type==='input')canceledInput.delete(el);
  const form=el.closest('form');
  if(form&&el.id!=='wcompany'){if(form.id!=='controls')dirty.add(form);return}
  if(!confirmDiscard()){
   if(values.has(el)){if(el.type==='checkbox'||el.type==='radio')el.checked=values.get(el);else el.value=values.get(el)}
   if(type==='input')canceledInput.add(el);stop(e);return;
  }
  remember(el);
 },true);
 document.addEventListener('click',e=>{
  const el=e.target.closest('a,button');if(!el)return;
  // New-tab source links do not replace the form.
  if(el.matches('a')&&(el.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey))return;
  const form=el.closest('form');
  if(el.matches('button')&&form&&el.type==='submit')return;
  if(!confirmDiscard())stop(e);
 },true);
 document.addEventListener('submit',e=>{if(!confirmDiscard(e.target))stop(e)},true);
 window.addEventListener('beforeunload',e=>{if(connected().length||pending.size){e.preventDefault();e.returnValue=''}});
 // View handlers preserve these remembered values when a user cancels a change.
 rememberAll();new MutationObserver(rememberAll).observe(document.documentElement,{subtree:true,childList:true});
 window.FormSafety={hasUnsaved:()=>connected().length>0,saved:form=>dirty.delete(form),begin:form=>{pending.add(form);form.inert=true;form.setAttribute('aria-busy','true');return ()=>{pending.delete(form);form.inert=false;form.removeAttribute('aria-busy')}}};
})();
