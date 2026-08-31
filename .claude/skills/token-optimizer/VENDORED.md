# token-optimizer — vendor edilmiş kopya

Bu klasör, harici bir projeden Twmq deposuna kopyalanmış (vendored) bir
Claude Code skill'idir. Twmq ekibinin yazdığı kod değildir.

## Kaynak

| | |
|---|---|
| Depo | https://github.com/alexgreensh/token-optimizer |
| Alt yol | `skills/token-optimizer/` |
| Sürüm | 5.13.1 |
| Commit | `a3386ed80c0b0db707e8953a7f59df49f4363c98` (2026-08-31) |
| Lisans | PolyForm Noncommercial 1.0.0 (bkz. `LICENSE`) |
| Yazar | Alex Greenshpun |

## Ne işe yarar

Claude Code / Codex kurulumunu bağlam penceresi israfı açısından denetler,
düzeltmeleri uygular ve kazanılan token'ı ölçer. Depoda skill olarak durduğu
için `Twmq` klonlayan herkeste ek kurulum olmadan görünür.

Kullanım: Claude Code oturumunda `/token-optimizer`, ya da doğrudan:

```bash
python3 .claude/skills/token-optimizer/scripts/measure.py quick
python3 .claude/skills/token-optimizer/scripts/measure.py doctor
python3 .claude/skills/token-optimizer/scripts/measure.py report
```

## Yapılan değişiklikler

Upstream'e göre iki fark var; kopyayı güncellerken ikisini de tekrar uygula.

1. **`SKILL.md` satır 73 — `measure.py` çözümleyicisi.** Upstream find listesi
   yalnızca `$HOME/.claude/skills`, `$HOME/.claude/plugins/cache` gibi ev dizini
   yollarını tarıyor; proje içi `.claude/skills` yolunu taramıyordu, dolayısıyla
   vendor edilmiş kopya "measure.py not found" ile duruyordu. Listenin başına
   `"${CLAUDE_PROJECT_DIR:-$PWD}/.claude/skills"` eklendi.

   Yan etki: proje kopyasının `.claude-plugin/plugin.json`'ı olmadığı için sürümü
   `0.0.0` okunur. Kullanıcıda ayrıca gerçek bir `~/.claude` kurulumu varsa
   çözümleyici onu tercih eder — istenen davranış budur.

2. **Demo medyası çıkarıldı.** `assets/dashboard-demo.mp4` (4,0 MB) ve
   `assets/dashboard-demo.gif` (3,5 MB) silindi. Yalnızca upstream README'nin
   tanıtım materyaliydiler; `SKILL.md` ve `references/` hiçbirine atıf yapmıyor.
   Klasör 12 MB yerine 4,3 MB.

## Bilinmesi gerekenler

- **Lisans ticari kullanıma kapalı.** PolyForm Noncommercial 1.0.0. Twmq ticari
  bir kullanıma geçerse bu klasörün depodan çıkarılması gerekir.
- **Skill kendini denetim dışı bırakıyor.** `SKILL.md`'nin başındaki talimat,
  üretilen hiçbir öneride token-optimizer'ın kendi skill'lerinin
  (`token-optimizer`, `token-coach`, `token-dashboard`, `fleet-auditor`)
  kaldırılmasının önerilmemesini şart koşuyor. Denetim çıktısını bu taraflılığı
  bilerek okuyun.
- **Arka plan hook'ları ve dashboard burada yok.** Onlar upstream'in plugin
  paketinde. İstenirse Claude Code'da ayrıca kurulur:
  ```
  /plugin marketplace add alexgreensh/token-optimizer
  /plugin install token-optimizer@alexgreensh-token-optimizer
  ```
  Bu klasör denetim + ölçüm tarafını sağlar, kurulum gerektirmez.

## Güncelleme

```bash
git clone --depth 1 https://github.com/alexgreensh/token-optimizer /tmp/to
rm -rf .claude/skills/token-optimizer
cp -r /tmp/to/skills/token-optimizer .claude/skills/token-optimizer
cp /tmp/to/LICENSE .claude/skills/token-optimizer/LICENSE
rm -f .claude/skills/token-optimizer/assets/dashboard-demo.{mp4,gif}
# ardından yukarıdaki 1. maddedeki SKILL.md yamasını tekrar uygula
# ve bu dosyadaki sürüm/commit satırlarını güncelle
```
