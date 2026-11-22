/* Presentation and accessibility only. No fetch, storage, timers or save handlers. */
(()=>{
 const main=document.querySelector('main');if(!main)return;
 const labels={search:'Search records',region:'Filter by region',readiness:'Filter by readiness',category:'Filter by role category',coverage:'Filter by evidence coverage',filter:'Filter records',status:'Filter by status',timing:'Filter by task timing',q:'Search company research',stage:'Filter by pipeline stage',scope:'Assessment scope',reviewer:'Reviewer name',market:'Filter by market',temperature:'Filter by signal temperature',source:'Filter by source',fit:'Filter by fit score'};
 function improve(){
  main.querySelectorAll('input,select,textarea').forEach(el=>{
   if(el.getAttribute('aria-label')||el.getAttribute('aria-labelledby')||el.labels?.length)return;
   const label=labels[el.id]||el.getAttribute('placeholder')||el.getAttribute('title');
   if(label)el.setAttribute('aria-label',label);
  });
  main.querySelectorAll('.feedback,#message,#status').forEach(el=>{if(!el.getAttribute('role')){el.setAttribute('role','status');el.setAttribute('aria-live','polite')}});
  main.querySelectorAll('#error').forEach(el=>el.setAttribute('role','alert'));
  main.querySelectorAll('.table-wrap,.tablewrap').forEach(el=>{el.setAttribute('tabindex','0');el.setAttribute('role','region');el.setAttribute('aria-label','Scrollable evidence table')});
 }
 improve();
 new MutationObserver(improve).observe(main,{childList:true,subtree:true});
 const footer=document.createElement('div');footer.className='ui-end';footer.innerHTML='<span>Local portfolio · retained evidence and labelled fictional practice</span><a href="/dashboard">Back to operations overview ↑</a>';main.append(footer);
})();
