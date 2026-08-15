# Mimari (kesin karar)

**Python = sadece backend (JSON API). HTML yok.**  
**Frontend = sadece Next.js (TS/TSX).**

```
Tarayıcı
   │
   ▼
Next.js :3000          ← tek UI (Formül / İstatistik / Sağlık)
   │  /api/* rewrite
   ▼
Flask  :8080           ← sadece JSON (spor_toto motoru)
   │
   ▼
spor_toto/             ← Fix-16, ILP, Bayes, MC, Markov, health
```

`templates/` klasörü tarihsel kalıntı; runtime’da servis **edilmez**.

## API

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/` | Servis bilgisi JSON |
| GET | `/api/health` | 13 invariant |
| GET | `/api/stats?last=N` | Tarihsel 1/0/2 + analiz blokları (`last` = son N hafta dilimi) |
| GET | `/api/stats/<week>` | Tek hafta detayı (komşular, sıra, sapma, sıra-sıra bağlam) |
| POST | `/api/solve` | Tüm motor özellikleri |

### GET `/api/stats`

`?last=N` verilirse **tüm bloklar** o dilim üzerinden hesaplanır (`last` yoksa/geçersizse tüm sezon).

| Alan | İçerik |
|------|--------|
| `meta` | sezon, hafta sayısı, hafta aralığı, tarih aralığı, `sliced` |
| `totals` / `weekly_avg` / `bands` | toplam, haftalık ortalama, min–maks–ortanca–σ ve ortalama üstü/altı ayrımı |
| `analytics.positions` | 1.–15. maç sırasına göre 1/0/2 dağılımı |
| `analytics.transitions` | ardışık maçlarda sembol geçiş matrisi (3×3) |
| `analytics.distribution` | “bir haftada k adet” histogramı |
| `analytics.streaks` | hafta içi en uzun aynı-sembol serileri |
| `analytics.extremes` | her sembol için en yüksek/en düşük hafta |
| `analytics.recent` | son 6 haftanın ortalaması ve sezona göre farkı |
| `data_quality` | sayım çelişkileri, tekrar eden diziler, eksik haftalar |
| `weeks` | hafta satırları (`counts`, `max_streak`, `consistent`, …) |

**Tek doğruluk kaynağı** haftanın 15 karakterlik `results` dizisidir; dosyadaki hazır
`n1/n0/n2` alanları çeliştiğinde `data_quality.count_conflicts` içinde raporlanır.

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
bash scripts/run_next_dev.sh
# Preview = :3000 (Next)
# API     = :8080 (sadece JSON)
```
