# Patches

Bu klasör, büyük dosyaları (özellikle `templates/index.html`, `spor_toto/core.py`)
güvenli şekilde güncellemek için unified diff yamaları tutar.

## Uygulama (Replit / lokal)

```bash
git pull
git apply patches/fazN_....patch
# doğrula
python -m spor_toto.health
pytest tests/test_edge_cases.py tests/test_cli.py -q
git add -u
git commit -m "apply fazN patch"
git push
```

`git apply` başarısız olursa dosya zaten yamalanmış olabilir — `grep` ile içeriği kontrol et.

| Patch | İçerik |
|-------|--------|
| `faz2_ui.patch` | UI: Bayes preset, KL yorum, health tips, localStorage |
| `faz3_parity.patch` | Boş-slot `parse_picks`, web preset = CLI STRENGTH_PRESETS |
| `faz4_cli.patch` | CLI Bayes: Kaynak + top KL kaymaları |

Yeni özellik ekleme yeri değildir; perfection / parity düzeltmeleri içindir.
