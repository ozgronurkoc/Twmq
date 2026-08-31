# Bilgi Grafi — Token Olcum Kutugu

**Olcum tarihi:** 2026-08-31
**Depo:** ozgronurkoc/twmq @ 8e24697
**Cetvel:** tiktoken cl100k_base (gercek BPE tokenizer; Claude'un tokenizer'i DEGIL)
**Yontem:** soruyu cevaplamak icin baglama girmesi gereken icerigin token sayisi

## Olcum sorusu
"backend/spor_toto paketinde hangi moduller var, her biri ne yapiyor, ve
kalite kapisi scripts/check.sh hangi kontrolleri calistiriyor?"

## ONCESI (grafik yok)
| kalem | deger |
|---|---|
| taranan modul | 52 |
| okunan icerik | 65.657 karakter |
| **token** | **26.020** |

Kesif adimlari:
1. ls backend/spor_toto/  +  ls backend/scripts/ backend/tests/
2. cat scripts/check.sh
3. her modulun ilk 25 satiri (docstring) x 52 modul

NOT: 3. adimda tum dosyalar degil sadece docstring baslari okundu.
Temel olcum BILEREK dusuk tutuldu; boylece kazanc abartilmis olmuyor.

## SONRASI (grafik var)
| kalem | deger |
|---|---|
| token | (adim 6'da doldurulacak) |
