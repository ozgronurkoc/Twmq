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

**Ne buraya girmez.** Veri üreten beşli (`build_*.py`, `snapshot_iddaa.py`)
yalnızca standart kütüphane kullanır ve `spor_toto`'yu import etmez. Bu
kasıtlıdır: `snapshot-iddaa.yml` onları hiçbir bağımlılık kurmadan koşar ve
üretici katmanın analiz paketine bağımlı olmaması doğru katmanlamadır.
"""
