# Kaynak (provenance)

Bu klasor upstream'den oldugu gibi alinmistir (vendored), bu depoda yazilmadi.

- Kaynak depo: https://github.com/giuseppe-trisciuoglio/developer-kit
- Orijinal yol: `plugins/developer-kit-specs/skills/knowledge-graph/`
- Alindigi surum: commit `cb0a0c6` oncesi (`cb0a0c6^`) — yani skill'in
  silinmeden onceki son hali.

Upstream bu skill'i 18 Agustos 2026'da `developer-kit-specs` plugin'i ile
birlikte kaldirdi (PR #203, commit `cb0a0c6`: "migrated to pi-specs-kit").
Bu yuzden `npx skills add ... --skill knowledge-graph` artik calismiyor
("No matching skills found") ve dosyalar git gecmisinden cikarilarak buraya
kopyalandi. Guncelleme gerekirse ayni yerden yeniden cikarilir:

    git clone https://github.com/giuseppe-trisciuoglio/developer-kit /tmp/dk
    git -C /tmp/dk checkout cb0a0c6^ -- plugins/developer-kit-specs/skills/knowledge-graph

## Lisans

Upstream MIT lisansli. MIT, kopyalarda telif ve izin bildiriminin yer
almasini sart kosar; asagidaki metin bu yuzden buradadir.

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
