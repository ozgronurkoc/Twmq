# Spor Toto Lab — Next.js UI

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

API ayrı terminalde: `python web_app.py`

Sayfalar: `/` formül · `/stats` istatistik · `/stats/<hafta>` hafta detayı · `/health`

## İstatistik sayfası

`components/stats/` altındaki parçalar bağımlılıksız inline SVG ile çizilir:

- `tokens.ts` — sembol renkleri ve sequential ramp. Kategorik palet
  (`1` mavi `#2a78d6`, `0` turuncu `#eb6834`, `2` yeşil `#1baf7a`) renk körlüğü ve
  kontrast kontrollerinden geçmiş sabit yuva sırasıdır; **yeni seri için renk üretmeyin**.
- `charts.tsx` — pay çubuğu, haftalık seyir, bant şeridi, dağılım, ısı haritası, geçiş matrisi.
- `WeeksTable.tsx` — sıralanabilir/aranabilir tablo (her görselin tablo karşılığı).
- `primitives.tsx` — kart, efsane, sayı kutusu, sonuç şeridi, aralık filtresi, veri kalitesi paneli.

Sayfanın en üstündeki tek filtre satırı (`Tüm sezon / Son 24 / Son 12 / Son 6`) `?last=N`
ile API'ye gider; tüm bloklar aynı dilim üzerinden yeniden hesaplanır.
