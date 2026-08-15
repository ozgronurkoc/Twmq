# Mimari: Next.js + Python API

**Karar:** React / Next.js UI + JSON API + `spor_toto` motoru.

```
frontend/          Next.js (App Router) + Tailwind
       │  fetch JSON
       ▼
web_app.py         Flask — HTML (eski) + /api/* (yeni)
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
| POST | `/api/solve` | Formül üret (JSON body: `matches` veya `picks`) |

Eski HTML (`/`, `/solve`) geçiş süresince durur.
Yeni UI sadece `/api/*` kullanır.

CORS: `localhost` / `127.0.0.1` origin’lerine açık.

## Kurulum (bir kez)

```bash
python3 scripts/install_premium_ui.py
python3 scripts/install_premium_pages.py   # doğrulama
cd frontend && npm install
```

## Çalıştırma (Replit / yerel)

### Tek komut (önerilen)

```bash
bash scripts/run_next_dev.sh
```

Bu script:
1. `.env.local` yoksa oluşturur
2. `npm install` (gerekirse)
3. Flask API’yi `:8080` arka planda başlatır
4. Next.js’i `:3000` ön planda çalıştırır

### Manuel (iki terminal)

```bash
# Terminal A — API
python web_app.py
# http://127.0.0.1:8080/api/health

# Terminal B — UI
cd frontend
cp .env.example .env.local   # bir kez
npm install                  # bir kez
npm run dev
# http://localhost:3000
```

## Next.js sayfaları

| Rota | Dosya | İçerik |
|------|-------|--------|
| `/` | `app/page.tsx` | Formül üret (maç seçimi, canlı bedel, satır tablosu, log) |
| `/stats` | `app/stats/page.tsx` | Tarihsel 1/0/2 |
| `/health` | `app/health/page.tsx` | Sistem sağlık JSON |

## Notlar

- Flask varsayılan port: **8080** (`PORT` env ile değiştirilebilir)
- Next.js varsayılan port: **3000**
- Replit’te her iki portu da açık tutun / publish ayarlarını kontrol edin
- API cevap vermiyorsa `.env.local` içindeki `NEXT_PUBLIC_API_URL` değerini kontrol edin
