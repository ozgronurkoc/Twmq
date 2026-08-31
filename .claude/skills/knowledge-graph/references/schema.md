# `.claude/bilgi_grafi.json` şeması

Tek dosya, tek JSON nesnesi. Bölümler bağımsızdır: biri boş kalabilir.

**Değişmez kural:** her girdi bir `kaynak` alanı taşır. Kaynağı olmayan girdi
yazılmaz — grafın tamamı, ölçülmüş ya da okunmuş bilgiden oluşur.

```json
{
  "surum": 1,
  "yazildi": "2026-08-31T07:00:00Z",
  "git": { "head": "7a6477c...", "dal": "main" },

  "moduller": [
    {
      "yol": "backend/spor_toto/core.py",
      "gorev": "Kaplama kodu çözücüleri; olasılık katmanını hiç bilmez.",
      "kaynak": "backend/spor_toto/core.py:1",
      "hash": "<git hash-object cikti>"
    }
  ],

  "komutlar": [
    {
      "komut": "python -m spor_toto.health --list",
      "ne_yapar": "Kontrol envanterini listeler.",
      "kaynak": "backend/README.md:24"
    }
  ],

  "kapilar": [
    {
      "yol": "backend/tests/test_belgeler.py",
      "ad": "test_mimari_belgesi_butun_uclari_sayar",
      "tuttugu_iddia": "ARCHITECTURE_NEXT.md API tablosu web_app.py'deki uçların tamamını sayar.",
      "kaynak": "backend/tests/test_belgeler.py:44",
      "hash": "<git hash-object cikti>"
    }
  ],

  "sayilar": [
    {
      "deger": "0,579",
      "ne": "Piyasanın Brier skoru.",
      "ureten": "<sayıyı üreten tam komut>",
      "olculdu": "2026-08-31",
      "anildigi_yerler": ["README.md:§1.1"]
    }
  ],

  "boru_hatlari": [
    {
      "yol": "backend/scripts/build_odds.py",
      "uretir": ["backend/data/odds/odds.sqlite3"],
      "git_disi": true,
      "yeniden_uret": "python scripts/build_odds.py",
      "kaynak": ".gitignore:20",
      "hash": "<git hash-object cikti>"
    }
  ]
}
```

## Alanlar

| Alan | Zorunlu | Ne demek |
|---|---|---|
| `surum` | ✓ | Şema sürümü. Şema değişirse artar; eski dosya okunamıyorsa **silinir**, göç yazılmaz (defter yerel ve yeniden üretilebilir). |
| `yazildi` | ✓ | Son yazma anı, UTC ISO-8601. Tazelik konuşmasının başlangıç noktası. |
| `git.head` | ✓ | Yazma anındaki `git rev-parse HEAD`. Okurken farklıysa graf **şüphelidir**, yanlış değil — girdi bazlı `hash` karar verir. |
| `kaynak` | ✓ (her girdide) | `dosya:satır` ya da çalıştırılan komutun tam metni. |
| `hash` | ✓ (dosyaya dayanan girdilerde) | `git hash-object <yol>` çıktısı. Dosya içeriği değişince tutmaz; bayatlığı görünür kılan tek alan budur. |
| `sayilar[].ureten` | ✓ | Sayıyı üreten **komut**. "Belgede yazıyor" bir üretici değildir; belge `anildigi_yerler`e girer. |
| `sayilar[].anildigi_yerler` | ✓ | Sayının geçtiği yerler, `dosya:§bölüm` biçiminde. Bu listenin **eksik** olması grafın en pahalı hatasıdır: bir sayı düzeltilir, kardeşi bayat kalır. |
| `boru_hatlari[].git_disi` | ✓ | Ürettiği dosya `.gitignore`'da mı. Doğruysa `yeniden_uret` zorunludur. |

## Neden `sayilar` ayrı bir bölüm

Modül/kapı/boru hattı envanteri `ls` ve `grep` ile dakikalar içinde yeniden
üretilir — grafın orada kazandırdığı zaman azdır. `sayilar` öyle değil: bir
sayının **hangi belgelerin hangi bölümlerinde** anıldığını bulmak depo çapında
okuma gerektirir ve bu deponun geçmişi, o okumanın atlanmasının bedelini
gösteriyor (`backend/tests/test_belgeler.py` docstring'i). Grafın asıl değeri
bu bölümdedir; diğerleri kolaylıktır.
