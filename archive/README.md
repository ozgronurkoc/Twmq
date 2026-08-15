# archive/

Bu klasördeki hiçbir şey çalışmıyor, hiçbir şey tarafından import edilmiyor ve
hiçbir build adımına girmiyor. Silinmedi çünkü ileride parça parça geri
canlandırılabilir — ama bulunduğu hâliyle **ölü koddur**.

## İçerik

| Yol | Ne | Neden burada |
|-----|-----|--------------|
| `templates/` | Eski Jinja2 arayüzü (`index.html` 49 KB, `base`, `stats`, `stats_week`, `health`) | `backend/web_app.py` API-only'ye geçtiğinde servis dışı kaldı. Mimari kararı: `docs/ARCHITECTURE_NEXT.md`. |
| `patches/` | 8 adet unified diff (`faz2_ui`, `faz3_parity`, …) | Hedefleri `templates/index.html` ve eski `core.py` satırları. Artık uygulanamazlar. |
| `scripts/` | 20 adet tek-seferlik yamacı | Hepsi `templates/index.html` içine string enjekte ediyordu. |

## Dikkat edilecek iki dosya

- **`scripts/commit_and_sync.sh`** — çalıştırıldığında otomatik olarak
  `git push origin HEAD:main` yapar ve her adımı `|| true` ile yutar. Geri
  canlandırılacaksa bu davranış önce kaldırılmalıdır.
- **`scripts/post-merge.sh`** — eskiden `.replit` içindeki `[postMerge]`
  hook'una bağlıydı ve her merge'de `templates/index.html` üzerinde çalışıyordu.
  Hook kaldırıldı; script hedefiyle birlikte buraya taşındı.

## Geri getirmek istersen

Dosyalar `git mv` ile taşındığı için geçmiş korunmuştur:

```bash
git log --follow archive/templates/index.html
```
