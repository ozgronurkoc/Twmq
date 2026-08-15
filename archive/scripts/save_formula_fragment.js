  function captureFormula(){
    const table=document.getElementById('resultTable');
    if(!table) return null;
    const rows=[];
    table.querySelectorAll('tbody tr').forEach(tr=>{
      const tds=[...tr.querySelectorAll('td')];
      if(tds.length<2) return;
      const cells=tds.slice(1,-1).map(td=>td.textContent.trim());
      const costTxt=(tds[tds.length-1].textContent||'').trim();
      const cost=parseInt(costTxt,10)||1;
      rows.push({cells, cost});
    });
    if(!rows.length) return null;
    const bedel=rows.reduce((s,r)=>s+(r.cost||1),0);
    let baslik='';
    const titleEl=document.querySelector('.right-col .card-title');
    if(titleEl) baslik=titleEl.textContent.replace(/\s+/g,' ').trim();
    const guaranteed=!!document.querySelector('.stat-box.guarantee-ok');
    return {
      rows, bedel, satir: rows.length, baslik, guaranteed,
      variant: (document.getElementById('variant')||{}).value||'0',
      mode: (document.getElementById('mode')||{}).value||'fix16'
    };
  }
  function saveCoupon(){
    const name=document.getElementById('couponName').value.trim();
    if(!name){ alert('Kupon adı giriniz.'); return; }
    const selections=[];
    for(let i=1;i<=15;i++){
      const checked=[...document.querySelectorAll('input[name="match_'+i+'"]:checked')].map(cb=>cb.value);
      selections.push(checked.length?checked:['1','0','2']);
    }
    const formula=captureFormula();
    if(!formula){
      if(!confirm('Henüz formül üretilmemiş. Sadece maç seçimleri kaydedilsin mi?\n(Formüllü kayıt için önce Formül Üret)')) return;
    }
    const data=getSaved();
    if(data[name] && !confirm('«'+name+'» zaten var. Üzerine yazılsın mı?')) return;
    data[name]={
      selections,
      mode:document.getElementById('mode').value,
      variant:(document.getElementById('variant')||{}).value||'0',
      budget:(document.getElementById('budget')||{}).value||'',
      ts:Date.now(),
      formula: formula
    };
    if(!persistSaved(data)) return;
    document.getElementById('couponName').value='';
    renderSavedList();
    alert(formula ? ('Kaydedildi (formüllü: '+formula.satir+' satır, '+formula.bedel+' kolon).') : 'Kaydedildi (sadece seçimler).');
  }
  function renderSavedFormula(f){
    if(!f||!f.rows||!f.rows.length) return;
    let host=document.getElementById('savedFormulaHost');
    if(!host){
      host=document.createElement('div');
      host.id='savedFormulaHost';
      host.className='card';
      host.style.marginTop='14px';
      const right=document.querySelector('.right-col');
      if(right) right.insertBefore(host, right.firstChild);
      else document.body.appendChild(host);
    }
    const mc=f.rows[0].cells.length;
    let thead='<tr><th>#</th>';
    for(let i=1;i<=mc;i++) thead+='<th>M'+i+'</th>';
    thead+='<th>Fiyat</th></tr>';
    let body='';
    f.rows.forEach((r,idx)=>{
      body+='<tr><td>'+(idx+1)+'</td>';
      (r.cells||[]).forEach(c=>{ body+='<td class="cell-'+c+'">'+c+'</td>'; });
      body+='<td><strong>'+r.cost+'</strong>'+(r.cost>1?'<span class="cost-badge">×'+r.cost+'</span>':'')+'</td></tr>';
    });
    const g=f.guaranteed?'<span style="color:#1a7a3a;font-weight:600">14-Garanti</span>':'<span style="color:#ff3b30">Garanti yok / bilinmiyor</span>';
    host.innerHTML=
      '<div class="card-title">Kayıtlı Formül</div>'+
      '<div class="summary-grid" style="margin-bottom:12px">'+
        '<div class="stat-box"><div class="val">'+f.satir+'</div><div class="lbl">Satır</div></div>'+
        '<div class="stat-box fiyat"><div class="val">'+f.bedel+'</div><div class="lbl">Kolon</div></div>'+
        '<div class="stat-box"><div class="val" style="font-size:0.95rem">'+g+'</div><div class="lbl">Durum</div></div>'+
      '</div>'+
      '<div class="table-header"><h3>Kupona Yazılacak '+f.satir+' Satır</h3>'+
      '<div class="table-actions"><button type="button" class="copy-btn" onclick="copySavedFormula()">Kopyala</button></div></div>'+
      '<div class="table-wrap"><table class="result-table" id="savedResultTable"><thead>'+thead+'</thead><tbody>'+body+'</tbody></table></div>'+
      '<div style="font-size:0.75rem;color:var(--text-sec);margin-top:8px">Bu formül kayıttan yüklendi; yeniden üretmek için Formül Üret.</div>';
    window.__savedFormulaRows=f.rows;
  }
  function copySavedFormula(){
    const rows=window.__savedFormulaRows;
    if(!rows) return;
    let text='';
    rows.forEach((r,i)=>{ text+=(i+1)+' | '+(r.cells||[]).join(' ')+'\n'; });
    navigator.clipboard.writeText(text.trim()).then(function(){ alert('Kopyalandı'); });
  }
  function loadCoupon(name){
    const c=getSaved()[name]; if(!c||!Array.isArray(c.selections)) return;
    c.selections.forEach((syms,idx)=>{
      document.querySelectorAll('input[name="match_'+(idx+1)+'"]').forEach(cb=>{ cb.checked=Array.isArray(syms)&&syms.includes(cb.value); });
    });
    if(c.mode){ document.getElementById('mode').value=c.mode; toggleBudget(c.mode); }
    if(c.variant && document.getElementById('variant')) document.getElementById('variant').value=c.variant;
    if(c.budget && document.getElementById('budget')) document.getElementById('budget').value=c.budget;
    updateLiveStats(); hideClientError();
    if(c.formula) renderSavedFormula(c.formula);
    else {
      const host=document.getElementById('savedFormulaHost');
      if(host) host.innerHTML='<div class="adv-hint">Bu kayıtta formül yok; Formül Üret gerekir.</div>';
    }
  }
  function deleteCoupon(name){
    if(!confirm('«'+name+'» silinsin mi?')) return;
    const data=getSaved(); delete data[name]; persistSaved(data); renderSavedList();
  }
  function renderSavedList(){
    const data=getSaved(), el=document.getElementById('savedList'), names=Object.keys(data).sort();
    if(!names.length){ el.innerHTML='<div style="color:#6e6e73;font-size:0.78rem">Kayıtlı kupon yok.</div>'; return; }
    el.innerHTML=names.map(function(n){
      const hasF=data[n]&&data[n].formula&&data[n].formula.rows&&data[n].formula.rows.length;
      const badge=hasF?' <span style="font-size:0.65rem;color:#1a7a3a;background:#e8f8ee;padding:1px 6px;border-radius:6px">formül</span>':'';
      const meta=hasF?(' · '+data[n].formula.satir+'s / '+data[n].formula.bedel+'k'):'';
      return '<div class="saved-item" data-name="'+encodeURIComponent(n)+'">'+ 
        '<span>'+n+badge+'<span style="color:#6e6e73;font-size:0.7rem">'+meta+'</span></span>'+
        '<span><button type="button" class="saved-load">Yükle</button> <button type="button" class="saved-del">Sil</button></span></div>';
    }).join('');
    el.querySelectorAll('.saved-item').forEach(function(row){
      const nm=decodeURIComponent(row.getAttribute('data-name'));
      row.querySelector('.saved-load').onclick=function(){ loadCoupon(nm); };
      row.querySelector('.saved-del').onclick=function(){ deleteCoupon(nm); };
    });
  }
