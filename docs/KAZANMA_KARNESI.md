# Kazanma Karnesi — 2026/27

> **Bu bir tahmin kaydı DEĞİLDİR.** Plan, her haftanın kupon öncesi
> girdilerinden (oran + oynanma payı, `entered_at`) **bugünkü motorla**
> yeniden türetildi. Sızıntı yok — girdiler sonuç girilmeden kaydedildi ve
> kalabalık modeli 2026/27'yi hiç görmeyen 112 tarihsel haftada kestirildi.
> Ama sonuç görülmeden **dondurulmuş** bir kayıt da değil: motor o gün
> bugünkü hâlinde değildi.
>
> `python scripts/hafta_kos.py --sonrasi` ile yeniden üretilir.

## Kurulum

| | |
|---|---|
| garanti | **15** → kaçak eşiği `k ≤ 3`, hedef `P(en iyi kolon ≥ 12)` |
| kural | **`hak`** — `secim.odul_secim`: kademeler kendi ağırlığıyla (medyan), bütçe **kısıt değil supap** |
| bütçe | 2,000 TL (200 kolon) — **tavan**; kural bedelini kendi seçer ve satırlar tavanı kovalamaz |
| bedel | ₺10/kolon — ölçülmüş (`getiri.KOLON_BEDELI`) |
| ödül | **garanti tabanı**: `k` kaçakta **bir** kolon `15−k` kademesinde. **Alt sınır** — gerçekleşen getiri bundan büyüktür |
| ödeyen olay | `k = 0` → 15. kademe. `P(k≤3)` bunu `k = 1`'le **topluyor** ve o kademe maliyeti karşılamıyor — bkz. başabaş sütunu |
| rakip kolon | 15,000,000 — varsayım (`karne.RAKIP_KOLON`); `E[TL]` buna `1/(N·q)` mertebesinde duyarlı |

## Haftalar

| hf | şekil | kolon | maliyet | P(k≤3) | **P(k=0)** | E[TL] | kaçak | kademe | **başabaş k** | ödül | net | fiyat ölçeği |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 10b/1ç/4ü | 162 | 1,620 | 0.269 | **0.003** | 164 | 5 | 10 | 3 | 0 | -1,620 | `iddaa` |
| 2 | 10b/1ç/4ü | 162 | 1,620 | 0.275 | **0.003** | 462 | 4 | 11 | 2 | 0 | -1,620 | `iddaa-acilis` |
| 3 | 10b/1ç/4ü | 162 | 1,620 | 0.317 | **0.004** | 333 | 5 | 10 | 2 | 0 | -1,620 | `pinnacle-kapanis` |
| 4 | 10b/1ç/4ü | 162 | 1,620 | 0.224 | **0.002** | 358 | 5 | 10 | 3 | 0 | -1,620 | `pinnacle-kapanis` |
| 5 | 8b/6ç/1ü | 192 | 1,920 | 0.337 | **0.005** | — | — | — | — | — | — | `pinnacle-kapanis` |

## Toplam (4 sonuçlanmış hafta)

| | |
|---|---:|
| maliyet | 6,480 TL |
| ödül (garanti tabanı) | 0 TL |
| **net** | **-6,480 TL** |
| geri dönüş | **%0.0** |

## Okuma

**Fiyat ölçeği haftalar arasında değişti** ve bu, olasılıkları doğrudan
karşılaştırmayı engeller: ilk haftalarda ana fiyat ~%17 marjlı iddaa
oranıydı, sonra ~%3,4 marjlı Pinnacle'a geçildi. Sütun bunu her satırda
söylüyor — ama **ilan etmek karşılaştırmayı geçerli kılmıyor** (§3.63).

**Ve bu kayıt, kıyaslandığı geri testle de aynı ölçekte değil.** 114
haftalık geri test `Avg` kapanışla (marj %7,26) koşuyor, yani ortada
**üç** ölçek var. Düzeltilemez de: 2026/27'nin oran arşivi bugün boş,
canlı haftalar `Avg` ölçeğinde yeniden türetilemiyor. Geçersiz olan
karşılaştırmalar açıkça şunlar: canlı `P(k≤3)` ↔ geri
testin ortalaması, ve ölçeğin değiştiği yerde canlı haftaların
olasılıkları **birbiriyle**. Geçerli kalanlar sonuçtan gelenlerdir —
kaçak, kademe, ödül; onlar fiyattan bağımsızdır.

**Ödül sütunu alt sınırdır.** 192 kolonluk bir 15-garanti
sistemi, garantinin söylediği tek kolondan fazlasını da tutturur; karne
onları saymaz çünkü kolon listesi bizde değil (şekle biz karar veriyoruz,
kolonları satıcı üretiyor). Gerçekleşen getiri bu tablodan **büyüktür**.

**`P(k≤3)` bir kapsama ölçüsüdür, kâr ölçüsü değildir.**
Manşet olasılık iki farklı olayı topluyor ve biri para kaybettiriyor:
`k=0` 15. kademeyi verir, `k=1` 14. kademeyi. Karnenin kendi kaydında bugüne kadar **hiçbir hafta** ödeyen kademeye ulaşmadı (4 hafta).
Ödeyen olayın olasılığı `P(k=0)` sütununda ve manşetin
**1/121 ile 1/65 arasında**. **Başabaş k** sütunu her haftanın
KENDİ ikramiye tablosundan türetiliyor (medyan alınmıyor: nominal TL dört
sezonda 72 kat büyümüş), ve o sütun sabit değil — `k=2` 2., 3. haftada; `k=3` 1., 4. haftada.

**`n` küçük.** Bu tablo bir strateji karnesi değil, bir **kayıt
başlangıcı**. Anlamlı bir yargı için haftaların birikmesi gerekiyor ve
biriktirmekten başka yolu yok.

