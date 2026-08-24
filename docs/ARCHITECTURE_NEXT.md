# Mimari (kesin karar)

**Python = sadece backend (JSON API). HTML yok.**  
**Frontend = sadece Next.js (TS/TSX).**

```
Tarayıcı
   │
   ▼
frontend/              ← Next.js :3000, tek UI (7 sayfa — aşağıdaki tablo)
   │  /api/* rewrite
   ▼
backend/web_app.py     ← Flask :8080, sadece JSON
   │
   ▼
backend/spor_toto/     ← Fix-16, ILP, Bayes, MC, Markov, health
```

Repo iki taraflıdır: Python'un tamamı `backend/`, arayüzün tamamı `frontend/`.
Eski Jinja2 arayüzü depodan silinmiştir; runtime'da servis **edilmez** ve
hiçbir şey tarafından import edilmez.

## API

Uçların **tamamı** (13). Bu tablo eskiden dokuz satırdı ve dördü eksikti
(`/api/health/checks`, `/api/backtest`, `/api/pazar`, `/api/tahmin`,
`/api/benzer`) —
üstelik `README.md` ve `backend/README.md` bu tabloyu *kaynak* gösteriyordu,
yani boşluk üç belgeye birden yayılıyordu. Artık liste
`frontend/lib/api-sozlesme.json` ile aynı 13 ucu sayar ve o dosya CI'da
`scripts/api_sozlesme.py --kontrol` ile denetlenir.

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/` | Servis bilgisi + uç envanteri |
| GET | `/health` | Liveness — süreç ayakta mı; hiçbir değişmez koşmaz |
| GET | `/api/meta` | Modlar, Bayes preset'leri, motor varsayılanları, sınırlar, geri test ızgarası |
| GET | `/api/health` | Readiness — değişmezler; `?only=` kısmi, `?fresh=1` önbelleği atlar (bkz. `SAGLIK_VIZYONU.md`) |
| GET | `/api/health/checks` | Kayıtlı kontrol envanteri — kontrolleri **koşturmadan** listeler |
| GET | `/api/health/history` | Sunucudaki son koşuların özeti (süreç ömürlü) |
| POST | `/api/health/kupon` | Kullanıcının kendi kuponunu aynı değişmezlerden geçirir |
| GET | `/api/stats?last=N` | Tarihsel 1/0/2 + analiz blokları (`last` = son N hafta dilimi) |
| GET | `/api/stats/<week>` | Tek hafta detayı (komşular, sıra, sapma, sıra-sıra bağlam) |
| GET | `/api/backtest` | Geri test: sezon + hafta hafta + eşik taraması + hold-out |
| GET | `/api/pazar?arindirma=…` | 1X2 dışı pazarlar (alt/üst 2,5 · Asya handikabı) — fiyat **ve** ölçülmüş kalibrasyonu birlikte |
| GET | `/api/tahmin?limit=N` | Yaklaşan maçlar — olasılık **ve** ölçülmüş isabet birlikte |
| GET | `/api/benzer?oran=…` | "Bu oranda geçmişte ne oldu" — 31 bin maçlık korpus |
| POST | `/api/solve` | Tüm motor özellikleri |

İstatistik katmanının durumu, alınan kararlar ve yol haritası:
[`ISTATISTIK_YOL_HARITASI.md`](ISTATISTIK_YOL_HARITASI.md).

## Sayfalar

| Yol | Ne yapar |
|-----|----------|
| `/` | Formül — kaplama motoru, olasılık, senaryo karşılaştırma |
| `/tahmin` | Yaklaşan maçlara 1/0/2 + ölçülmüş isabet |
| `/super-toto` | Canlı sezon defteri (statik besleme, bkz. aşağısı) |
| `/istatistik` | Tarihsel dağılım, analiz blokları, oran özeti |
| `/istatistik/[week]` | Tek hafta detayı |
| `/istatistik/geri-test` | Eşik taraması + hold-out |
| `/saglik` | Değişmez raporu + kayıtlı kontrol envanteri |

## Sözleşme nasıl korunuyor

Arayüzün okuduğu gövdenin **şekli** `frontend/lib/api-sozlesme.json`
dosyasında durur; `backend/scripts/api_sozlesme.py` onu 13 ucu gerçekten
çağırarak üretir ve `--kontrol` ile bayatlığını denetler. `check.mjs` ayrıca
TypeScript derleyici API'siyle `lib/types.ts` arayüzlerini okuyup aynı
dosyayla karşılaştırır: **sunucunun gönderdiği her alan tipte olmalı, tipte
zorunlu diyen her alan sunucudan gelmeli.**

Bu boşluk gerçekti: bir alan adı değiştiğinde motor sapasağlam kalır, bütün
testler geçer ve sayfa sessizce boş döner — tip denetimi de göremez, çünkü
istemci cevabı doğrulamadan `as T` ile kalıba sokar. Denetim ilk koşusunda
iki gerçek sapma yakaladı (`/api/meta`nın `backtest` bloğu ve
`/api/benzer`in `filtre` bloğu tipte hiç yazmıyordu).

`/api/meta` frontend'in tek gerçek kaynağıdır: mod listesi, preset'ler ve
sayısal sınırlar arayüzde **sabit kodlanmaz**, buradan okunur. Gövde
`spor_toto/meta.py` içinde üretilir; sağlık katmanının `meta_sozlesmesi`
kontrolü aynı envanteri okuyup iç tutarlılığını denetler (her sınırda
min ≤ varsayılan ≤ max, preset ve mod listelerinin motorla örtüşmesi).

### GET `/api/stats`

`?last=N` verilirse özet, bantlar **ve** analiz bloklarının tamamı o dilim
üzerinden hesaplanır (`last` yoksa/geçersizse tüm sezon). Arayüzdeki tek filtre
satırı buraya bağlıdır; böylece iki görsel asla farklı veriyi anlatmaz.

| Alan | İçerik |
|------|--------|
| `meta` | sezon, hafta sayısı, hafta/tarih aralığı, `sliced` |
| `totals` / `weekly_avg` / `bands` | toplam, haftalık ortalama, min–maks–ortanca–σ, ortalama üstü/altı |
| `analytics.positions` | 1.–15. maç sırasına göre 1/0/2 dağılımı |
| `analytics.transitions` | ardışık maçlarda sembol geçiş matrisi (3×3) |
| `analytics.distribution` | "bir haftada k adet" histogramı |
| `analytics.streaks` | hafta içi en uzun aynı-sembol serileri |
| `analytics.extremes` | her sembol için en yüksek/en düşük hafta |
| `analytics.recent` | son 6 haftanın ortalaması ve sezona göre farkı |
| `data_quality` | sayım çelişkileri, tekrar eden diziler, eksik haftalar |
| `odds` | maç sonucu (1X2) özeti: kapsama, favori isabeti, marj, kalibrasyon — arşiv yoksa `null` |
| `weeks` | hafta satırları (`counts`, `max_streak`, `consistent`, …) |

`/api/stats/<week>` ayrıca `odds` (maç numarasına göre 1X2 bloğu) ve `odds_hit`
(o hafta favorinin tuttuğu maç sayısı) döner.

**Arayüze yalnızca maç sonucu oranı çıkar.** Arşivdeki diğer pazarlar (2.5
alt/üst, Asya handikap) ve maç istatistikleri API'ye hiç girmez; onlar
`backend/data/odds/` altında analiz için durur (`backend/README.md`).

Tek doğruluk kaynağı haftanın 15 karakterlik `results` dizisidir; dosyadaki
hazır `n1/n0/n2` alanları çeliştiğinde fark yutulmaz,
`data_quality.count_conflicts` içinde raporlanır ve arayüzde gösterilir.

### POST `/api/solve` body

```json
{
  "matches": [["1"],["1","0"], ...],
  "mode": "fix16 | auto | exact | block | heuristic | butce | maxcov",
  "variant": 0,
  "budget": 32,
  "plan_count": 5,
  "plan_apply": 1,
  "kati": false,
  "probs": [{"1":0.5,"0":0.3,"2":0.2}, ...],
  "use_bayes": false,
  "bayes_preset": "dengeli",
  "prior_strength": 1,
  "evidence_strength": 10,
  "mc_samples": 80000,
  "fire_max": 2,
  "trials": 5,
  "ls_iters": 30000,
  "seed": 42,
  "time_limit": 60,
  "block_limit": 256,
  "exact_limit": 512
}
```

`probs` gönderilmezse `advanced`, `bayes` ve `markov` blokları `null` döner —
olasılık katmanının tamamı bu alana bağlıdır.

`fire` bloğu seçim DIŞI senaryoları ölçer ve olasılık girdisi gerektirmez.
Pahalı olduğu için maliyet sınırı vardır; aşılırsa blok
`{"skipped": true, "reason": …}` döner (sessizce `null` olmaz).

Cevap: `ok`, `error`, `result` (rows, guaranteed, advanced, bayes, markov, …), `run_log_text`.

## Arayüz durumu

Sunucuda oturum yoktur; `/api/solve` durumsuzdur ve her istek kurulumun
tamamını taşır. Formül sayfasının kurulumu bu yüzden **istemcide** saklanır
(`frontend/lib/kurulum.ts`):

| Taşıyıcı | Ne zaman yazılır | Kapsam | Kayıp |
|---|---|---|---|
| `localStorage` | her değişiklikte, kendiliğinden | o tarayıcı | yok |
| URL (`?s=…`) | yalnızca "Bağlantıyı kopyala" | paylaşılabilir | olasılıklar binde bir + normalize |
| `sessionStorage` (`?hafta=`) | hafta detayından devir | o sekme | yok |

Maç adları yalnızca ilk satırdadır: URL'e girmez (15 takım adı adresi üç
katına çıkarır) ve çözüme hiç katılmaz — motor yalnızca işaretleri görür.

Öncelik: **URL > `localStorage`**, ardından devir paketi yalnızca
olasılıkların üzerine yazar. Sonuç hiçbirine girmez — türetilmiş veridir.

Kodlama sabit genişliklidir; taşan bir alan sonraki bütün maçları kaydırır
ve hiçbir yerde patlamaz. `frontend/scripts/check.mjs` bu sınırı CI'da
bekçiye bağlar (`tests.yml` → `frontend` işi).

## İstemcide hesaplanan iki büyüklük

Bu ikisi sunucudan **istenmez**; girdi değiştikçe anında görünmeleri
gerektiği için istemcide durur (`frontend/lib/kume-ici.ts`):

| Büyüklük | Formül | Sunucudaki karşılığı |
|---|---|---|
| Küme-içi koşulu | `∏ᵢ Σ_{s∈secᵢ} pᵢ(s)` | `advanced.exact.p_kume_ici` |
| Küre-kaplama alt sınırı | `⌈uzay / (1 + Σ(kᵢ−1))⌉` | `result.alt_sinir` |

İkisi de sunucunun döndürdüğü değerle birebir tutmak zorundadır; CI bunu
ölçülmüş vakalarla denetler. **Birimlere dikkat:** `advanced.exact.*` yüzde
döner (sunucuda `100 *` uygulanmıştır), `markov.*` ise 0–1 olasılık.

## Çalıştırma

```bash
bash scripts/run_next_dev.sh    # repo kökünden
# Preview = :3000 (Next)
# API     = :8080 (sadece JSON)
```

Yalnızca API: `python backend/web_app.py`
