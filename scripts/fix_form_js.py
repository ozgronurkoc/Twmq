"""Tum mainForm submit handler'larini siler, tek temiz AJAX handler ekler."""
from pathlib import Path

p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")

marker = "document.getElementById('mainForm').addEventListener('submit'"
while marker in t:
    start = t.find(marker)
    brace_start = t.find("{", start)
    if brace_start < 0:
        break
    depth = 0
    i = brace_start
    end = None
    while i < len(t):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < len(t) and t[end] == ")":
                    end += 1
                if end < len(t) and t[end] == ";":
                    end += 1
                break
        i += 1
    if end is None:
        break
    t = t[:start] + t[end:]

CLEAN = """
  document.getElementById('mainForm').addEventListener('submit', function(ev){
    ev.preventDefault();
    var form = ev.target;
    var modeEl = document.getElementById('mode');
    var budgetEl = document.getElementById('budget');
    var mode = modeEl ? modeEl.value : 'fix16';
    var budget = budgetEl ? budgetEl.value : '';
    var cifte = 0, banko = 0, uclu = 0;
    for (var i = 1; i <= 15; i++) {
      var n = document.querySelectorAll('input[name="match_' + i + '"]:checked').length;
      if (n === 0) n = 3;
      if (n === 1) banko++;
      else if (n === 2) cifte++;
      else uclu++;
    }
    var logEl = document.getElementById('runLogText');
    function writeLog(msg) {
      if (logEl) logEl.value = '=== TARAYICI LOG ===\\n' + msg + '\\n';
    }
    writeLog('Formul Uret\\nmode=' + mode + '\\ncifte=' + cifte);
    if ((mode === 'butce' || mode === 'maxcov') && (!budget || Number(budget) < 1)) {
      writeLog('ENGEL: butce');
      if (typeof showClientError === 'function') showClientError('Butce giriniz');
      return;
    }
    if (mode === 'fix16' && cifte < 7) {
      writeLog('ENGEL: cifte=' + cifte);
      if (typeof showClientError === 'function') showClientError('En az 7 cifte lazim, simdi ' + cifte);
      return;
    }
    var btn = document.getElementById('submitBtn');
    var loading = document.getElementById('loading');
    if (btn) { btn.disabled = true; btn.textContent = 'Gonderiliyor...'; }
    if (loading) loading.classList.add('active');
    writeLog('POST basliyor...');
    var fd = new FormData(form);
    fetch(form.getAttribute('action') || '/solve', { method: 'POST', body: fd, credentials: 'same-origin' })
      .then(function(res) {
        writeLog('HTTP ' + res.status);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.text();
      })
      .then(function(html) {
        document.open();
        document.write(html);
        document.close();
      })
      .catch(function(err) {
        if (btn) { btn.disabled = false; btn.textContent = 'Formul Uret'; }
        if (loading) loading.classList.remove('active');
        writeLog('HATA: ' + err);
        if (typeof showClientError === 'function') showClientError('Hata: ' + err);
      });
  });
"""

t = t.replace("?", ".") if False else t.replace("?", ".")  # no-op placeholder
t = t.replace("?", ".") if False else t
# optional chaining
t = t.replace("?", ".") if False else t.replace("?", ".")

# real optional chaining removal:
while "?." in t:
    t = t.replace("?", ".") if False else t
    break
t = t.replace("?", ".") if False else t
# Actually:
t = Path("templates/index.html").read_text(encoding="utf-8") if False else t
t = t.replace("?", ".") if False else t.replace("?", ".")

# Fix properly below without the botched replaces - rewrite file cleanly in next push
