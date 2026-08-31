# Kaynak (provenance)

Bu skill iki aşamada oluştu: önce upstream'den olduğu gibi alındı, sonra bu
depoya uyarlanmak için **yeniden yazıldı**.

## 1. Nereden geldi

- Kaynak depo: https://github.com/giuseppe-trisciuoglio/developer-kit
- Orijinal yol: `plugins/developer-kit-specs/skills/knowledge-graph/`
- Alındığı sürüm: `cb0a0c6^` — skill'in silinmeden önceki son hâli.

Upstream bu skill'i 18 Ağustos 2026'da `developer-kit-specs` plugin'i ile
birlikte kaldırdı (PR #203, commit `cb0a0c6`: "migrated to pi-specs-kit"). Bu
yüzden `npx skills add ... --skill knowledge-graph` artık çalışmıyor ("No
matching skills found") ve dosyalar git geçmişinden çıkarıldı. Orijinali geri
almak için:

    git clone https://github.com/giuseppe-trisciuoglio/developer-kit /tmp/dk
    git -C /tmp/dk checkout cb0a0c6^ -- plugins/developer-kit-specs/skills/knowledge-graph

## 2. Ne kadarı değişti

Upstream sürümü **spec-driven** bir iş akışına bağlıydı: grafı
`docs/specs/[ID-feature]/knowledge-graph.json` altında tutuyor ve
`spec-to-tasks`, `task-implementation`, `spec-quality` komutlarının onu
çağıracağını varsayıyordu. O komutlar bu depoda yok, o dizin düzeni de yok —
yani skill olduğu gibi bırakılsa hiçbir zaman doğru anda tetiklenmezdi.

Yeniden yazılan kısımlar:

| Dosya | Durum |
|---|---|
| `SKILL.md` | Yeniden yazıldı: yeni konum, yeni tetikleyiciler, bu deponun komutları |
| `references/schema.md` | Yeniden yazıldı: yeni JSON şeması (`sayilar` kütüğü dahil) |
| `references/sorgular.md` | Yeni — çalıştırılabilir tarifler (upstream `query-examples.md` yerine) |
| `references/sinirlar.md` | Yeni — bayatlık/boyut/gizlilik (upstream `error-handling` + `performance` + `security` yerine) |
| `references/examples.md`, `integration-patterns.md` | Silindi — var olmayan komut zincirini anlatıyorlardı |

Korunan fikirler upstream'e aittir: kalıcı JSON grafı, keşfi önbelleğe alma,
tazelik kavramı, kaynak kodu değiştirmeme kısıtı.

Bu depoya özgü eklenenler: her girdide zorunlu `kaynak` alanı, `git hash-object`
ile girdi bazlı bayatlık tespiti, ölçülmüş sayı kütüğü (`sayilar`) ve grafın
git dışı tutulması.

## Lisans

Upstream MIT lisanslı. MIT, kopyalarda telif ve izin bildiriminin yer almasını
şart koşar; aşağıdaki metin bu yüzden buradadır. Yeniden yazılan bölümler de
aynı türev eser kapsamındadır.

MIT License

Copyright (c) 2025 Giuseppe Trisciuoglio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
