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
| garanti | **13** → kaçak eşiği `k ≤ 1`, hedef `P(en iyi kolon ≥ 12)` |
| bütçe | 2,000 TL (200 kolon) |
| bedel | ₺10/kolon — ölçülmüş (`getiri.KOLON_BEDELI`) |
| ödül | **garanti tabanı**: `k` kaçakta **bir** kolon `13−k` kademesinde. **Alt sınır** — gerçekleşen getiri bundan büyüktür |
| ödeyen olay | `k = 0` → 13. kademe. `P(k≤1)` bunu `k = 1`'le **topluyor** ve o kademe maliyeti karşılamıyor — bkz. başabaş sütunu |
| rakip kolon | 15,000,000 — varsayım (`karne.RAKIP_KOLON`); `E[TL]` buna `1/(N·q)` mertebesinde duyarlı |

## Haftalar

| hf | şekil | kolon | maliyet | P(k≤1) | **P(k=0)** | E[TL] | kaçak | kademe | **başabaş k** | ödül | net | fiyat ölçeği |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 6b/1ç/8ü | 162 | 1,620 | 0.249 | **0.052** | 75 | 4 | 9 | 1 | 0 | -1,620 | `iddaa` |
| 2 | 6b/1ç/8ü | 162 | 1,620 | 0.219 | **0.044** | 94 | 1 | 12 | 0 | 1,439 | -181 | `iddaa-acilis` |
| 3 | 6b/1ç/8ü | 162 | 1,620 | 0.282 | **0.064** | 93 | 1 | 12 | 0 | 1,230 | -390 | `pinnacle-kapanis` |
| 4 | 6b/1ç/8ü | 162 | 1,620 | 0.175 | **0.032** | — | — | — | — | — | — | `pinnacle-kapanis` |

## Toplam (3 sonuçlanmış hafta)

| | |
|---|---:|
| maliyet | 4,860 TL |
| ödül (garanti tabanı) | 2,668 TL |
| **net** | **-2,192 TL** |
| geri dönüş | **%54.9** |

## Okuma

**Fiyat ölçeği haftalar arasında değişti** ve bu, olasılıkları doğrudan
karşılaştırmayı engeller: ilk haftalarda ana fiyat ~%17 marjlı iddaa
oranıydı, sonra ~%3,4 marjlı Pinnacle'a geçildi. Sütun bunu her satırda
söylüyor — ama **ilan etmek karşılaştırmayı geçerli kılmıyor** (§3.63).

**Ve bu kayıt, kıyaslandığı geri testle de aynı ölçekte değil.** 114
haftalık geri test `Avg` kapanışla (marj %7,26) koşuyor, yani ortada
**üç** ölçek var. Düzeltilemez de: 2026/27'nin oran arşivi bugün boş,
canlı haftalar `Avg` ölçeğinde yeniden türetilemiyor. Geçersiz olan
karşılaştırmalar açıkça şunlar: canlı `P(k≤1)` ↔ geri
testin ortalaması, ve ölçeğin değiştiği yerde canlı haftaların
olasılıkları **birbiriyle**. Geçerli kalanlar sonuçtan gelenlerdir —
kaçak, kademe, ödül; onlar fiyattan bağımsızdır.

**Ödül sütunu alt sınırdır.** 162 kolonluk bir 13-garanti
sistemi, garantinin söylediği tek kolondan fazlasını da tutturur; karne
onları saymaz çünkü kolon listesi bizde değil (şekle biz karar veriyoruz,
kolonları satıcı üretiyor). Gerçekleşen getiri bu tablodan **büyüktür**.

**`P(k≤1)` bir kapsama ölçüsüdür, kâr ölçüsü değildir.**
Manşet olasılık iki farklı olayı topluyor ve biri para kaybettiriyor:
`k=0` 13. kademeyi verir, `k=1` 12. kademeyi. Karnenin
kendi kaydı bunu iki kez yazdı — 2. ve 3. hafta 12 tutturdu ve ikisi de
zarar etti. Ödeyen olayın olasılığı `P(k=0)` sütununda ve manşetin
**dörtte biri ile beşte biri** arasında. **Başabaş k** sütunu her haftanın
KENDİ ikramiye tablosundan türetiliyor (medyan alınmıyor: nominal TL dört
sezonda 72 kat büyümüş), ve o sütun sabit değil — 1. haftada `k=1` bile
maliyeti karşılardı, 2. ve 3. haftada yalnızca `k=0`.

**`n` küçük.** Bu tablo bir strateji karnesi değil, bir **kayıt
başlangıcı**. Anlamlı bir yargı için haftaların birikmesi gerekiyor ve
biriktirmekten başka yolu yok.

