#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 <<'PY'
from pathlib import Path
import re
p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")
if "resetSubmitUI" in t:
    print("Buton fix zaten var.")
else:
    pat = r"  document\.getElementById\('mainForm'\)\.addEventListener\('submit', function\(e\)\{.*?\n  \};"
    m = re.search(pat, t, re.S)
    if not m:
        raise SystemExit("submit handler bulunamadi")
    new = r"""  function resetSubmitUI(){
    const btn=document.getElementById('submitBtn');
    const loading=document.getElementById('loading');
    if(btn){ btn.disabled=false; btn.textContent='Formül Üret'; }
    if(loading) loading.classList.remove('active');
  }
  window.addEventListener('pageshow', resetSubmitUI);
  document.getElementById('mainForm').addEventListener('submit', function(e){
    const mode=document.getElementById('mode').value, budget=document.getElementById('budget').value;
    try{
      const el=document.getElementById('runLogText');
      if(el){
        let cifte=0, banko=0, uclu=0;
        for(let i=1;i<={{ match_count }};i++){
          const n=document.querySelectorAll('input[name="match_'+i+'"]:checked').length;
          const k=n===0?3:n;
          if(k===1) banko++; else if(k===2) cifte++; else uclu++;
        }
        el.value='=== SPOR TOTO (TARAYICI) ===\\n'+
          'zaman: '+new Date().toISOString()+'\\n'+
          'olay: Formül Üret tıklandı\\n'+
          'mode: '+mode+'\\n'+
          'banko/cifte/uclu: '+banko+'/'+cifte+'/'+uclu+'\\n';
      }
    }catch(err){}
    if((mode==='butce'||mode==='maxcov')&&(!budget||Number(budget)<1)){
      e.preventDefault(); resetSubmitUI();
      showClientError('Bütçe modu için pozitif kolon bütçesi giriniz.'); return;
    }
    if(mode==='fix16'){
      let cifte=0;
      for(let i=1;i<={{ match_count }};i++){
        const n=document.querySelectorAll('input[name="match_'+i+'"]:checked').length;
        if(n===2) cifte++;
      }
      if(cifte<7){
        e.preventDefault(); resetSubmitUI();
        showClientError('Fix-16 en az 7 çifte maç ister (şu an '+cifte+'). Bir maçı daha çifte yapın veya Mod=auto seçin.');
        return;
      }
    }
    hideClientError();
    document.getElementById('submitBtn').disabled=true;
    document.getElementById('submitBtn').textContent='Hesaplanıyor…';
    document.getElementById('loading').classList.add('active');
    setTimeout(function(){
      if(document.getElementById('loading')?.classList.contains('active')){
        resetSubmitUI();
        showClientError('İstek çok uzun sürdü. Ports→8080 Open in Browser kullanın.');
      }
    }, 45000);
  });
"""
    p.write_text(t[:m.start()] + new + t[m.end():], encoding="utf-8")
    print("Buton fix uygulandi.")
print("resetSubmitUI:", "resetSubmitUI" in p.read_text())
PY
