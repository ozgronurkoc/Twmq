"""Veri üreten ve rapor üreten çalıştırılabilir betikler.

**Neden burası bir paket.** Bu dizindeki altı dosya birbirini
`importlib.util.spec_from_file_location` ile **dosya yolundan** yüklüyordu;
aynı on bir satırlık yükleyici altı kez kopyalanmıştı ve her kopya
`sys.argv`'yi geçici olarak eziyordu. Sonuç fiilen iki ayrı kod tabanıydı:
düzgün paket `spor_toto/` ve dosya yolundan çağrılan `scripts/`. Artık
sıradan `from scripts import super_toto_hafta` yeterli.

**Neden kurulmuyor.** `pyproject.toml`'un `packages.find`'ı yalnızca
`spor_toto*` alır. `scripts` çok genel bir addır; site-packages'a
kurulsaydı başka bir dağıtımın aynı adlı paketiyle çakışırdı. Buradaki
dosyalar `backend/` dizininden çalıştırılır (CI de `working-directory:
backend` kullanır) ve o dizin zaten `sys.path`'tedir — kurulum gerekmez.

**Bağımlılıksız koşan iki betik.** Bu paragraf önceden "veri üreten beşli
(`build_*.py`, `snapshot_iddaa.py`) yalnızca standart kütüphane kullanır ve
`spor_toto`'yu import etmez" diyordu. **Ölçüldü ve doğru değildi:**
`build_avrupa`, `build_sehir`, `build_egitim` ve `build_fixtures` dördü de
`spor_toto` import ediyor (ilk ikisi korpus takımları için, son ikisi
`odds.FIYAT_VARSAYILAN` için).

Kuralın gerçekten geçerli olduğu — ve geçerli KALMASI gereken — iki betik
şunlar: **`snapshot_iddaa.py` ve `build_sportoto_arsiv.py`**. Actions bu
ikisini haftalık cron ile, hiçbir bağımlılık kurmadan koşuyor ve depoya
commit atıyor; oraya bir `spor_toto` importu girerse hata ancak cron
ateşlendiğinde görünür. Bekçisi artık var:
`tests/test_scripts_ortak.py::test_bagimliliksiz_betikler_spor_toto_import_etmez`.

**Paylaşılan gövde nereye gider.** Saf standart kütüphane yardımcıları
`scripts/_ortak.py`ye (indirme, tarih çözme, üretilmiş JSON metni, kardeş
betik getirme); sayısal/olasılıksal hesaplar `spor_toto.ortak`a. İkisi de
kopyalanmaz — bekçileri `tests/test_scripts_ortak.py` ve `tests/test_ortak.py`.
"""
