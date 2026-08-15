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
| POST | `/api/solve` | Formül üret (JSON body) |

Eski HTML (`/`, `/solve`, `/stats`) geçiş süresince durur.
Yeni UI sadece `/api/*` kullanır.

## Çalıştırma (Replit)

```bash
# 1) API stack kurulum (bir kez)
python3 scripts/install_next_stack.py

# 2) API
python web_app.py

# 3) UI (ayrı terminal)
cd frontend
cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8080
npm install
npm run dev
```

Tarayıcı: `http://localhost:3000`
