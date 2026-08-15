# Mimari: Next.js + Python API

**Karar:** React / Next.js UI + JSON API + `spor_toto` motoru.

```
frontend/          Next.js (App Router) + Tailwind  → :3000  (preview)
       │  /api/* rewrite (aynı origin)
       ▼
web_app.py         Flask  → :8080
       │
       ▼
spor_toto/         Fix-16, MC, Bayes, history, …
```

## API uçları

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/api/health` | Sağlık JSON |
| GET | `/api/stats` | 1/0/2 özet + haftalar |
| GET | `/api/stats/<week>` | Tek hafta |
| POST | `/api/solve` | Formül üret (`matches` veya `picks`) |

`next.config.mjs` içinde `/api/*` → `http://127.0.0.1:8080/api/*` rewrite var.
Tarayıcı sadece `:3000` görür; Flask tarayıcıya açılmaz.

## Replit

**Run** butonu:
1. Flask’ı arka planda `:8080` açar
2. Next.js’i `:3000` açar
3. **Preview = port 3000** (Next.js UI)

```bash
# Elle de aynı script:
bash scripts/run_next_dev.sh
```

`npm install` sadece ilk sefer (veya `package.json` değişince) çalışır.

## Yerel (iki terminal)

```bash
# A
python web_app.py

# B
cd frontend && npm run dev
```

## Sayfalar

| Rota | Dosya |
|------|-------|
| `/` | Formül üret (seçim, canlı bedel, satır tablosu, log) |
| `/stats` | Tarihsel 1/0/2 |
| `/health` | Sistem sağlık |
