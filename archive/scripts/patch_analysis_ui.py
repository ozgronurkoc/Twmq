# -*- coding: utf-8 -*-
"""Exact/MC/Bayes/Dirichlet/Markov ayri kartlar."""
from pathlib import Path

CSS = '''
    .analysis-card { margin-top: 14px; }
    .analysis-badge {
      display: inline-flex; align-items: center; gap: 6px;
      font-size: 0.68rem; font-weight: 600; letter-spacing: 0.02em;
      padding: 3px 10px; border-radius: 20px; margin-left: 8px;
      vertical-align: middle;
    }
    .badge-exact { background: #eef3ff; color: #2b4acb; }
    .badge-mc { background: #f3eefe; color: #6b3fa0; }
    .badge-bayes { background: #e8f8ee; color: #1a7a3a; }
    .badge-dirichlet { background: #fff4e5; color: #9a5b00; }
    .badge-markov { background: #e8f4fc; color: #0b6e99; }
    .badge-uniform { background: #f0f0f2; color: #6e6e73; }
    .analysis-sub { font-size: 0.75rem; color: var(--text-sec); font-weight: 400; margin-top: 4px; margin-bottom: 12px; line-height: 1.45; }
    .analysis-nav { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0 4px; }
    .analysis-nav a {
      font-size: 0.72rem; font-weight: 500; padding: 5px 11px; border-radius: 16px;
      border: 1px solid var(--border); background: #fff; color: var(--text); text-decoration: none;
    }
    .analysis-nav a:hover { background: var(--bg); border-color: var(--blue); color: var(--blue); }
'''

FRAG = r'''
      {% if result.advanced or result.bayes or result.markov %}
      <div class="analysis-nav" style="margin-top:14px">
        {% if result.advanced %}<a href="#sec-exact">Exact</a><a href="#sec-mc">Monte Carlo</a>{% endif %}
        {% if result.bayes %}<a href="#sec-bayes">Bayes</a><a href="#sec-dirichlet">Dirichlet</a>{% endif %}
        {% if result.markov %}<a href="#sec-markov">Markov</a>{% endif %}
      </div>
      {% endif %}

      {% if result.advanced %}
      <div class="card analysis-card" id="sec-exact">
        <div class="card-title">Exact <span class="analysis-badge badge-exact">KESIN</span>
          {% if result.advanced.source == 'bayes_posterior' %}
          <span class="analysis-badge badge-bayes">kaynak: Bayes posterior</span>
          {% else %}
          <span class="analysis-badge badge-uniform">kaynak: probs / uniform</span>
          {% endif %}
        </div>
        <div class="analysis-sub">Secim uzayinda tam sayim (simulasyon degil). 14-garanti buradan gelmez; kombinatoryaldir.</div>
        <div class="mc-grid">
          <div class="mc-box"><div class="mc-label">Kume ici</div><div class="mc-val">%{{ result.advanced.exact.p_kume_ici }}</div></div>
          <div class="mc-box"><div class="mc-label">P(15)</div><div class="mc-val">%{{ result.advanced.exact.p_15 }}</div></div>
          <div class="mc-box"><div class="mc-label">P(14)</div><div class="mc-val">%{{ result.advanced.exact.p_14 }}</div></div>
          <div class="mc-box"><div class="mc-label">Tek kolon 15</div><div class="mc-val">%{{ result.advanced.exact.p_tek }}</div></div>
        </div>
      </div>
      <div class="card analysis-card" id="sec-mc">
        <div class="card-title">Monte Carlo <span class="analysis-badge badge-mc">SIMULASYON</span>
          <span style="font-weight:400;color:var(--text-sec);font-size:0.82rem">n={{ result.advanced.monte_carlo.n_samples }} · ±95% CI</span>
        </div>
        <div class="analysis-sub">Rastgele orneklem tahmini. Exact ile yakin olmali.</div>
        <div class="mc-grid">
          <div class="mc-box"><div class="mc-label">Kume ici</div><div class="mc-val">%{{ result.advanced.monte_carlo.kume_ici.pct }}</div><div class="mc-ci">±{{ result.advanced.monte_carlo.kume_ici.ci95 }}</div></div>
          <div class="mc-box"><div class="mc-label">P(15)</div><div class="mc-val">%{{ result.advanced.monte_carlo.p15.pct }}</div><div class="mc-ci">±{{ result.advanced.monte_carlo.p15.ci95 }}</div></div>
          <div class="mc-box"><div class="mc-label">P(14)</div><div class="mc-val">%{{ result.advanced.monte_carlo.p14.pct }}</div><div class="mc-ci">±{{ result.advanced.monte_carlo.p14.ci95 }}</div></div>
          <div class="mc-box"><div class="mc-label">P(13)</div><div class="mc-val">%{{ result.advanced.monte_carlo.p13.pct }}</div><div class="mc-ci">±{{ result.advanced.monte_carlo.p13.ci95 }}</div></div>
          <div class="mc-box"><div class="mc-label">P(12)</div><div class="mc-val">%{{ result.advanced.monte_carlo.p12.pct }}</div><div class="mc-ci">±{{ result.advanced.monte_carlo.p12.ci95 }}</div></div>
        </div>
      </div>
      {% endif %}

      {% if result.bayes %}
      <div class="card analysis-card" id="sec-bayes">
        <div class="card-title">Bayes <span class="analysis-badge badge-bayes">BAYES</span>
          <span class="analysis-badge badge-dirichlet">Dirichlet prior</span>
        </div>
        <div class="analysis-sub">
          Prior α={{ result.bayes.prior_strength }} · Evidence n={{ result.bayes.evidence_strength }}
          · Ort. KL={{ result.bayes.summary.mean_kl_prior_post }}
          {% if result.bayes.summary.mean_kl_label %} · <strong>{{ result.bayes.summary.mean_kl_label }}</strong>{% endif %}
          <br>14-garanti degismez. {% if result.advanced and result.advanced.source == 'bayes_posterior' %}Exact/MC kaynagi: <strong>posterior</strong>.{% endif %}
        </div>
      </div>
      <div class="card analysis-card" id="sec-dirichlet">
        <div class="card-title">Dirichlet Posterior <span class="analysis-badge badge-dirichlet">MAC BAZLI</span></div>
        <div class="analysis-sub">Prior → evidence → posterior. KL: prior'dan sapma.</div>
        <table class="bayes-table">
          <thead><tr><th>Mac</th><th>Prior 1/0/2</th><th>Evidence</th><th>Posterior</th><th>KL</th><th>Yorum</th></tr></thead>
          <tbody>
            {% for m in result.bayes.matches %}
            <tr>
              <td>M{{ m.mac }}</td>
              <td>{{ m.prior['1'] }}/{{ m.prior['0'] }}/{{ m.prior['2'] }}</td>
              <td>{{ m.evidence['1'] }}/{{ m.evidence['0'] }}/{{ m.evidence['2'] }}</td>
              <td><strong>{{ m.posterior['1'] }}</strong>/{{ m.posterior['0'] }}/{{ m.posterior['2'] }}</td>
              <td>{{ '%.4f'|format(m.kl) }}</td>
              <td>{{ m.kl_label or '—' }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% endif %}

      {% if result.markov %}
      <div class="card analysis-card" id="sec-markov">
        <div class="card-title">Markov Zinciri <span class="analysis-badge badge-markov">SIRALI RISK</span></div>
        <div class="analysis-sub">Kume-ici hayatta kalma + hata butcesi. Kaplama kodunu degistirmez.{% if result.markov.summary.method %} · {{ result.markov.summary.method }}{% endif %}</div>
        <div class="markov-grid">
          <div class="markov-box good"><div class="mk-label">Kume ici</div><div class="mk-val">%{{ '%.2f'|format(100 * result.markov.summary.p_kume_ici) }}</div></div>
          <div class="markov-box good"><div class="mk-label">Garanti yolu</div><div class="mk-val">%{{ '%.2f'|format(100 * result.markov.summary.p_garanti_path) }}</div></div>
          <div class="markov-box"><div class="mk-label">P(0 hata)</div><div class="mk-val">%{{ '%.2f'|format(100 * result.markov.summary.p0) }}</div></div>
          <div class="markov-box"><div class="mk-label">P(1 hata)</div><div class="mk-val">%{{ '%.2f'|format(100 * result.markov.summary.p1) }}</div></div>
          <div class="markov-box {% if result.markov.summary.p2plus > 0.01 %}warn{% else %}good{% endif %}"><div class="mk-label">P(2+ hata)</div><div class="mk-val">%{{ '%.2f'|format(100 * result.markov.summary.p2plus) }}</div></div>
        </div>
        {% if result.markov.survival and result.markov.survival.transitions %}
        <div style="font-size:0.78rem;font-weight:600;margin:8px 0 4px">Mac bazli hayatta kalma (IN→IN)</div>
        <table class="surv-table">
          <thead><tr><th>Mac</th><th>P(stay)</th><th>P(exit)</th><th>Kumultatif IN</th></tr></thead>
          <tbody>
            {% for tr in result.markov.survival.transitions %}
            <tr>
              <td>M{{ tr.mac }}</td>
              <td>%{{ '%.2f'|format(100 * tr.p_stay) }}</td>
              <td>%{{ '%.2f'|format(100 * tr.p_exit) }}</td>
              <td>%{{ '%.2f'|format(100 * result.markov.survival.p_in_after[tr.mac]) }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        {% endif %}
      </div>
      {% endif %}

'''

p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")
if 'id="sec-exact"' in t and 'id="sec-markov"' in t:
    print("analiz kartlari zaten var")
else:
    if ".analysis-card" not in t:
        t = t.replace("  </style>", CSS + "\n  </style>", 1)
    start = t.find("{% if result.advanced %}")
    end = t.find("{% if result.notlar %}")
    if start > 0 and end > start and 'id="sec-exact"' not in t[start:end]:
        t = t[:start] + "\n        " + t[end:]
    if 'id="sec-exact"' not in t:
        ins = t.find("{% if result.error_freq %}")
        if ins < 0:
            raise SystemExit("insert noktasi yok")
        t = t[:ins] + FRAG + t[ins:]
    t = t.replace(
        '<div class="card-title" style="margin:0">Uniform Dağılım</div>',
        '<div class="card-title" style="margin:0" id="sec-uniform">Uniform Dağılım <span class="analysis-badge badge-uniform">KOMBINATORIK</span></div>',
        1,
    )
    t = t.replace("Bayes güncelle (Dirichlet)", "Bayes + Dirichlet prior", 1)
    p.write_text(t, encoding="utf-8")
    print("analiz kartlari eklendi")
for k in ["sec-exact", "sec-mc", "sec-bayes", "sec-dirichlet", "sec-markov"]:
    print(k, p.read_text().count('id="%s"' % k))
