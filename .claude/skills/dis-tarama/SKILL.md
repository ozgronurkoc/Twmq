---
name: dis-tarama
description: Depo dışına bakma ve bulunanı bu projenin para biriminde fiyatlandırma yordamı. Yeni bir eksen/fikir/iyileştirme açılmadan önce, "bu hedefe ulaşmanın başka yolu var mı", "bunu dışarıda çözen biri var mı", "şu makale/proje/araç işimize yarar mı" sorulduğunda, ya da bir dış kaynak (makale, GitHub projesi, ürün, kişi) değerlendirilecekse kullan. Tetikleyiciler: dış tarama, literatür, makale, başka kim yapmış, dışarıda var mı, bu fikir işe yarar mı, yeni yaklaşım, vizyonu genişlet.
---

# Dış tarama — depo dışını nasıl okuruz, bulduğumuzu nasıl fiyatlandırırız

Bu deponun en büyük riski **içe kapanmaktır**: 114 haftalık ölçüm altyapısı
o kadar rahat ki, her soru "bunu burada nasıl ölçerim"e dönüşebilir. Oysa
hedefe giden yol depo dışından geçiyor olabilir. Sahibi bunu açıkça istedi
(2026-09-14): *"hep böyle dışa dönük ol, kendini bu depoyla sınırlama."*

Ama dışa dönüklük "her fikri dene" demek değil. Bu depoda bir fikrin
değeri **ölçüldüğünde** doğar. Yordam bu ikisini birleştirir.

## Üç soru — yeni bir eksen açılmadan ÖNCE

1. **Bunu dışarıda çözen var mı?** Kim, hangi oyunda, ne kadarını, nasıl
   belgeleyerek? (Vakalar `docs/DIS_UFUK_TARAMASI.md` §7'de biriktirilir.)
2. **Neye mal oldu, ve burada neden tekrarlanır/tekrarlanmaz?** Çoğu vakada
   kopyalanamayan şey *model* değil **yapıdır**: iade oranı, likidite,
   fiyatı kimin koyduğu, ikramiyenin nasıl bölündüğü.
3. **Buradaki fiyatı kaç puan?** Para birimi tektir: **üç ayda 15/15
   olasılığının puanı**. Fiyatlanamayan fikir belgeye girmez — ama
   "fiyatlanamadı" da bir kayıttır, sessizce düşmez.

## Fiyatlandırma — hangi tavana çarpıyor

Her dış fikir, ölçülmüş iki tavandan birine çarpar (§3.76):

| fikir şu eksende ise | tavanı | pratik anlamı |
|---|---|---|
| arama, algoritma, çözücü, donanım, kupon şekli | **+2,6 puan** (81 kupondan serbest kümeye) | 1,8'i yalnızca 729 kupona çıkmak; kalan **0,8** hepsinin toplamı |
| model, özellik, yeni veri, kalibrasyon | **1 puan = 0,02–0,047 Brier** | ölçülen en iyi bulgu (Betfair, 0,001) = **0,02 puan** |

Üretici komutlar:

```bash
cd backend && python scripts/ufuk_kiyasi.py --butce 21000 --serbest
cd backend && python scripts/bilgi_esnekligi.py --butce 21000 --yayilmis
```

Bir fikir bu tavanların **üstünde** bir iddia taşımıyorsa sıraya girmez.
Taşıyorsa, ölçüt projenin geri kalanıyla aynı: sezon dışarıda bırakmalı,
hafta eşleştirmeli bootstrap, %95 aralık tamamen sıfırın bir yanında.

## Hedef değişirse tavanlar da değişir — bunu her seferinde kontrol et

Fiyat listesi **bugünkü hedefe** (`P(15/15)`, kâr ölçüt değil) bağlıdır.
Hedef "beklenen para"ya dönerse en az iki kapalı eksen **anında açılır**:

* **Kalabalıktan sapmak** (Benter'in ekseni) — `P` değişmez ama pay büyür.
* **Çoklu kuponda entropi** (arXiv 2308.14339) — havuz seyrelmesi devreye
  girer ve "en olası `N` kolon" optimal olmaktan çıkar.

Bu yüzden dış bir fikri reddetmeden önce sorulacak son soru: *"bu fikir
bizim hedefimizde mi yoksa başka bir hedefte mi doğru?"*

## Nasıl aranır — işe yarayan sorgular

* **Problemin akademik adıyla**: bu oyunun adı *football pool problem*
  (`K₃(n,1)`, üçlü kaplama kodları). Genel arama "football prediction"
  kalabalıktır; problemin kendi adı literatürü doğrudan açar.
* **Bitişik oyunlarla**: Totocalcio, Stryktipset (13 maç), Veikkaus, UK
  pools, March Madness bracket pools, Pick Six. Yöntem çoğu zaman orada
  yayımlanmıştır.
* **Yapıyla, kişiyle**: "pari-mutuel syndicate", "rebate", "bracket pool
  entropy", "covering design", "budgeted maximum coverage".
* **Karşı kanıtla**: bir iddiayı doğrulayan değil **yalanlayan** arama da
  yapılır ("is X profitable", "does X fail", "replication").

## Tuzaklar — ölçülmüş olanlar

* **"Garantili sistem" satan platform** bir kaynak değildir. Türkiye'de
  birçoğu var; hiçbiri ölçülmüş kayıt yayımlamıyor ve "garanti" kelimesi
  kaplama garantisidir, kazanç garantisi değil.
* **ROI bulgusu Brier bulgusu değildir.** Sabit oranlı bahiste kârlı bir
  model, müşterek bahiste `P(15/15)`i oynatmayabilir; çeviri §2.2'dedir.
* **Dış bir çalışmanın sayısı bizim sayımız değildir.** Künyesiyle,
  kesitiyle ve "bu bizim ölçümümüz değil" notuyla yazılır
  (`DIS_INCELEME.md`in kuralı).
* **Tarama ölçüm değildir.** Bir dış fikir, buradaki bir komuta
  dönüşmediği sürece belgeye *bulgu* olarak değil *aday* olarak girer.

## Çıktı nereye yazılır

1. `docs/DIS_UFUK_TARAMASI.md` — §4 fiyat listesine bir satır, gerekiyorsa
   §7'ye bir varlık kanıtı, §8'e kaynak.
2. Ölçüm ürettiyse `docs/ISTATISTIK_YOL_HARITASI.md` §3'e gerekçesiyle,
   ve `.claude/olcum_kutugu.json`a üreten komutuyla.
3. Reddedildiyse **yeniden açılma şartı** yazılır. Şartsız ret yoktur.
