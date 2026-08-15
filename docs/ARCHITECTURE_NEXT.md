# Mimari (kesin karar)

**Python = sadece backend (JSON API). HTML yok.**  
**Frontend = sadece Next.js (TS/TSX).**

```
Tarayıcı
   │
   ▼
frontend/              ← Next.js :3000, tek UI (Formül / İstatistik / Sağlık)
   │  /api/* rewrite
   ▼
backend/web_app.py     ← Flask :8080, sadece JSON
   │
   ▼
backend/spor_toto/     ← Fix-16, ILP, Bayes, MC, Markov, health
```

Repo iki taraflıdır: Python'un tamamı `backend/`, arayüzün tamamı `frontend/`.
Eski Jinja2 arayüzü `archive/templates/` altına alınmıştır; runtime'da servis
**edilmez** ve hiçbir şey tarafından import edilmez.

## API

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/` | Servis bilgisi JSON |
| GET | `/api/health` | 13 invariant |
| GET | `/api/stats` | Tarihsel 1/0/2 |
| GET | `/api/stats/<week>` | Tek hafta |
| POST | `/api/solve` | Tüm motor özellikleri |

### POST `/api/solve` body

```json
{
  "matches": [["1"],["1","0"], ...],
  "mode": "fix16 | auto | heuristic | butce | maxcov",
  "variant": 0,
  "budget": 32,
  "use_bayes": false,
  "prior_strength": 1,
  "evidence_strength": 10,
  "mc_samples": 80000,
  "probs": [{"1":0.5,"0":0.3,"2":0.2}, ...]
}
```

Cevap: `ok`, `error`, `result` (rows, guaranteed, advanced, bayes, markov, …), `run_log_text`.

## Çalıştırma

```bash
bash scripts/run_next_dev.sh    # repo kökünden
# Preview = :3000 (Next)
# API     = :8080 (sadece JSON)
```

Yalnızca API: `python backend/web_app.py`
