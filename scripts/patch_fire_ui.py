# -*- coding: utf-8 -*-
"""web_app + template: secim disi 1-fire / 2-fire UI."""
from pathlib import Path

FIRE_UI = r'''
      {% if result.fire_report %}
      <div class="card" style="margin-top:14px" id="sec-fire">
        <div class="card-title">Secim Disi Fire Analizi
          <span style="font-size:0.68rem;font-weight:600;padding:3px 10px;border-radius:20px;margin-left:8px;background:#fff0f0;color:#c41d1d">KUME DISI</span>
        </div>
        <div style="font-size:0.75rem;color:var(--text-sec);margin-bottom:12px;line-height:1.45">
          Mac secimlerinin <strong>disina</strong> cikan fire. Yukaridaki "1 hata / 2 hata (ici)" kume <em>ici</em> mesafedir; bu blok farklidir.
          Banko / cifte ayrimi ve en iyi kolon skorlari tam sayimla hesaplanir.
        </div>
        <div class="hata-secici" style="margin-bottom:12px">
          <button type="button" class="hata-btn active" id="fireTab1" onclick="showFireTab(1)">1 fire</button>
          <button type="button" class="hata-btn" id="fireTab2" onclick="showFireTab(2)">2 fire</button>
        </div>
        {% if result.fire_report.fire1 %}
        <div id="firePanel1">
          <div style="font-size:0.8rem;color:var(--text-sec);margin-bottom:8px">
            n={{ result.fire_report.fire1.n }} nokta · min en iyi={{ result.fire_report.fire1.min_best }} ·
            P(≥13)={{ result.fire_report.fire1.p_ge_13 }}% · P(≥14)={{ result.fire_report.fire1.p_ge_14 }}%
          </div>
          <div class="prob-grid">
            <div class="prob-box"><div class="prob-label">15 Dogru</div><div class="prob-count">{{ result.fire_report.fire1.scores['15'] }}</div><div class="prob-pct">%{{ result.fire_report.fire1.pct['15'] }}</div></div>
            <div class="prob-box"><div class="prob-label">14 Dogru</div><div class="prob-count">{{ result.fire_report.fire1.scores['14'] }}</div><div class="prob-pct">%{{ result.fire_report.fire1.pct['14'] }}</div></div>
            <div class="prob-box"><div class="prob-label">13 Dogru</div><div class="prob-count">{{ result.fire_report.fire1.scores['13'] }}</div><div class="prob-pct">%{{ result.fire_report.fire1.pct['13'] }}</div></div>
            <div class="prob-box"><div class="prob-label">12 Dogru</div><div class="prob-count">{{ result.fire_report.fire1.scores['12'] }}</div><div class="prob-pct">%{{ result.fire_report.fire1.pct['12'] }}</div></div>
          </div>
          {% if result.fire_report.fire1.by_type %}
          <div style="font-weight:600;font-size:0.82rem;margin:10px 0 6px">Fail tipine gore</div>
          <table class="err-table"><thead><tr><th>Tip</th><th>n</th><th>P(14)</th><th>P(13)</th><th>P(12)</th></tr></thead><tbody>
            {% for tname, tdat in result.fire_report.fire1.by_type.items() %}
            <tr>
              <td>{{ tname }}</td><td>{{ tdat.n }}</td>
              <td>%{{ tdat.pct.get('14', 0) }}</td>
              <td>%{{ tdat.pct.get('13', 0) }}</td>
              <td>%{{ tdat.pct.get('12', 0) }}</td>
            </tr>
            {% endfor %}
          </tbody></table>
          {% endif %}
          {% if result.fire_report.fire1.by_match %}
          <div style="font-weight:600;font-size:0.82rem;margin:12px 0 6px">Mac bazli (bu mac yatarsa)</div>
          <table class="err-table"><thead><tr><th>Mac</th><th>Tip</th><th>n</th><th>P(14)</th><th>P(13)</th></tr></thead><tbody>
            {% for m in result.fire_report.fire1.by_match if m.can_fail %}
            <tr>
              <td>M{{ m.mac }}</td><td>{{ m.type }}</td><td>{{ m.n }}</td>
              <td>%{{ m.pct.get('14', 0) }}</td>
              <td>%{{ m.pct.get('13', 0) }}</td>
            </tr>
            {% endfor %}
          </tbody></table>
          {% endif %}
        </div>
        {% endif %}
        {% if result.fire_report.fire2 %}
        <div id="firePanel2" style="display:none">
          <div style="font-size:0.8rem;color:var(--text-sec);margin-bottom:8px">
            n={{ result.fire_report.fire2.n }} nokta · min en iyi={{ result.fire_report.fire2.min_best }} ·
            P(≥12)={{ result.fire_report.fire2.p_ge_12 }}% · P(≥13)={{ result.fire_report.fire2.p_ge_13 }}%
          </div>
          <div class="prob-grid">
            <div class="prob-box"><div class="prob-label">15 Dogru</div><div class="prob-count">{{ result.fire_report.fire2.scores['15'] }}</div><div class="prob-pct">%{{ result.fire_report.fire2.pct['15'] }}</div></div>
            <div class="prob-box"><div class="prob-label">14 Dogru</div><div class="prob-count">{{ result.fire_report.fire2.scores['14'] }}</div><div class="prob-pct">%{{ result.fire_report.fire2.pct['14'] }}</div></div>
            <div class="prob-box"><div class="prob-label">13 Dogru</div><div class="prob-count">{{ result.fire_report.fire2.scores['13'] }}</div><div class="prob-pct">%{{ result.fire_report.fire2.pct['13'] }}</div></div>
            <div class="prob-box"><div class="prob-label">12 Dogru</div><div class="prob-count">{{ result.fire_report.fire2.scores['12'] }}</div><div class="prob-pct">%{{ result.fire_report.fire2.pct['12'] }}</div></div>
          </div>
          {% if result.fire_report.fire2.by_type %}
          <div style="font-weight:600;font-size:0.82rem;margin:10px 0 6px">Fail tipi cifti</div>
          <table class="err-table"><thead><tr><th>Tip</th><th>n</th><th>P(13)</th><th>P(12)</th><th>P(11)</th></tr></thead><tbody>
            {% for tname, tdat in result.fire_report.fire2.by_type.items() %}
            <tr>
              <td>{{ tname }}</td><td>{{ tdat.n }}</td>
              <td>%{{ tdat.pct.get('13', 0) }}</td>
              <td>%{{ tdat.pct.get('12', 0) }}</td>
              <td>%{{ tdat.pct.get('11', 0) }}</td>
            </tr>
            {% endfor %}
          </tbody></table>
          {% endif %}
        </div>
        {% endif %}
      </div>
      <script>
      function showFireTab(n){
        var p1=document.getElementById('firePanel1'), p2=document.getElementById('firePanel2');
        var b1=document.getElementById('fireTab1'), b2=document.getElementById('fireTab2');
        if(p1) p1.style.display = (n===1)?'block':'none';
        if(p2) p2.style.display = (n===2)?'block':'none';
        if(b1) b1.classList.toggle('active', n===1);
        if(b2) b2.classList.toggle('active', n===2);
      }
      </script>
      {% endif %}

'''

def patch_web():
    p = Path("web_app.py")
    t = p.read_text(encoding="utf-8")
    if "fire_scenario_report" not in t:
        t = t.replace(
            "from spor_toto.analysis import monte_carlo_report, match_error_frequency",
            "from spor_toto.analysis import monte_carlo_report, match_error_frequency\n"
            "from spor_toto.fire_scenarios import fire_scenario_report",
        )
        print("import eklendi")
    if "fire_report = None" not in t:
        old = """        error_freq = None\n\n    guaranteed = worst <= 1\n    return {"""
        new = """        error_freq = None\n\n    fire_report = None\n    try:\n        fire_report = fire_scenario_report(enc, cols, max_fires=2)\n    except Exception:\n        logger.exception(\"fire_scenario_report failed (cols=%s)\", len(cols) if cols is not None else 0)\n        fire_report = None\n\n    guaranteed = worst <= 1\n    return {"""
        if old not in t:
            raise SystemExit("web anchor yok")
        t = t.replace(old, new, 1)
        print("fire_report compute eklendi")
    if '"fire_report": fire_report' not in t:
        t = t.replace(
            '"error_freq": error_freq,',
            '"error_freq": error_freq,\n        "fire_report": fire_report,',
            1,
        )
        print("return key eklendi")
    p.write_text(t, encoding="utf-8")

def patch_template():
    p = Path("templates/index.html")
    t = p.read_text(encoding="utf-8")
    t = t.replace(">1 hata</button>", ">1 hata (ici)</button>", 1)
    t = t.replace(">2 hata</button>", ">2 hata (ici)</button>", 1)
    t = t.replace(">Tümü</button>", ">Tumu (kume ici)</button>", 1)
    t = t.replace(">Tümü</button>", ">Tumu (kume ici)</button>", 1)
    if 'id="sec-fire"' in t:
        print("fire card zaten var")
    else:
        marker = "{% if result.error_freq %}"
        if marker not in t:
            raise SystemExit("error_freq marker yok")
        t = t.replace(marker, FIRE_UI + marker, 1)
        print("fire card eklendi")
    p.write_text(t, encoding="utf-8")

if __name__ == "__main__":
    patch_web()
    patch_template()
    print("DONE")
