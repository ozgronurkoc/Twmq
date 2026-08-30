"""MCP yüzeyi — motoru bir yapay zekâ ajanına açar (DENEY, §6H).

**Bu modül bir karar değil bir deneydir.** `sports-betting` incelemesi bir
MCP sunucusu önerdi (`src/sportsbet/mcp/_server.py`, 539 satır) ve soru
şuydu: *bize gerçekten bir şey katıyor mu?* Ölçütler `docs/
DIS_INCELEME_SPORTS_BETTING.md` §5'te, **sonuç görülmeden** yazıldı.

─── Tek çevirici kuralı — modülün asıl tasarım kısıtı ────────────────────

Depoda `/api/solve`ın parametre çevirisi (picks ayrıştırma, bayes preset,
bütçe, plan sayısı, motor parametreleri) **Flask işleyicisinin içinde**
duruyor; `cli.py` kendi çevirisini ayrıca yapıyor. İkisi de `engines.py`ye
varıyor ama yoldaki çeviri iki ayrı yerde yazılı.

Üçüncü bir yüzey, üçüncü bir çevirici demektir — ve o an `/api/meta` tek
kaynak olmaktan çıkar. Bu yüzden bu sunucu **kendi çevirisini yazmaz**:
Flask uygulamasının `test_client`ını kullanır, yani HTTP sözleşmesinin
tam olarak aynı yolundan geçer. Süreç içinde kalır (ağ yok, port yok,
sunucu ayakta olmak zorunda değil) ama gövde ve doğrulama tektir.

Bunun bedeli açık: MCP burada **yeni bir yetenek değil, yeni bir taşıma
katmanı**dır.

─── ÖLÇÜLDÜ — ve ölçüt 1 GEÇMEDİ ─────────────────────────────────────────

Dört ölçüt sonuç görülmeden yazılmıştı. Sonuç:

    2 sözleşme bölünmüyor    GEÇTİ  — `--envanter` `saglam: true`; araçlar
                                      yalnızca Flask'ın kayıt tablosunda
                                      olan uçlara bağlanıyor, çeviri tek
    3 kapıyı yavaşlatmıyor   GEÇTİ  — import 0,05 sn; süit bu modülü
                                      yalnızca `test_mcp.py`de açıyor ve
                                      `mcp` yoksa ATLIYOR
    4 üretimi taşımıyor      GEÇTİ  — `run_prod.sh`, `build.sh`, `.replit`
                                      değişmedi; `mcp` isteğe bağlı ekstra
    1 yeni yetenek           GEÇMEDİ

Ölçüt 1 şunu istiyordu: *ajanın MCP ile yapıp `curl`/CLI ile yapamadığı en
az bir iş.* Beş adımlı zincir kuruldu ve çalıştı (yetenekler → tahmin →
2.000 kolon bütçesiyle kupon → geri test → kuponun kendi doğrulama ucundan
geçmesi; tek süreçte, ağsız, 44,7 sn). Ama **her adım zaten bir uçtur** ve
hepsi `curl` ile erişilebilir. Kazanç gerçek fakat ergonomiktir: ajan
uçları kendi keşfeder, sunucu ayağa kaldırmak gerekmez, zincir kabuk
istemez. Bu bir *yetenek* değil bir *kolaylıktır*.

Kural "dördü de doğruysa kalır" diyordu. Dolayısıyla bu modül kendi
ölçütüne göre **yerini hak etmiyor** ve duruyor olması bir karar değil,
kullanıcının görmesi içindir. Kaldırmak tek komuttur.

─── Deneyin YAN ÜRÜNÜ kalıcı oldu ────────────────────────────────────────

Envanter denetimi ilk koşumda gerçek bir kusur buldu: servis kökünün uç
listesi elle yazılıydı ve eskiden kalmıştı — `/api/pazar` ve
`/api/takimlar` aylardır kayıtlı, çalışır ve `replit.md`de yazılıyken o
listede YOKTU. Liste artık `web_app.uc_envanteri()` ile Flask'ın kayıt
tablosundan türüyor. Deney düşse de bu kalır.

    pip install -e "backend[mcp]"
    python -m spor_toto.mcp_server --envanter   # araclar meta ile birebir mi
    python -m spor_toto.mcp_server              # stdio sunucusu
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

#: Araç adı → sardığı uç. **Tek kaynak burasıdır** ve `--envanter`
#: bunu `/api/meta` ile karşılaştırır; ikisi ayrışırsa envanter kırmızı
#: döner. Ayrı bir yetenek listesi tutmak, `meta.py`nin tek-kaynak
#: olmasını bozardı.
ARACLAR: dict[str, str] = {
    "yetenekler": "/api/meta",
    "kupon_uret": "/api/solve",
    "hafta_tahmini": "/api/tahmin",
    "hafta_istatistigi": "/api/stats",
    "pazarlar": "/api/pazar",
    "benzer_maclar": "/api/benzer",
    "kupon_dogrula": "/api/health/kupon",
    "geri_test": "/api/backtest",
}


def _istemci() -> Any:
    """Flask `test_client` — süreç içi, ağsız, TEK çeviriciyi kullanır."""
    import web_app

    web_app.app.config.update(TESTING=True)
    return web_app.app.test_client()


def _al(yol: str, **sorgu: Any) -> dict[str, Any]:
    """`GET` — boş parametreler düşürülür (uçların varsayılanı kazansın)."""
    temiz = {k: v for k, v in sorgu.items() if v is not None}
    cevap = _istemci().get(yol, query_string=temiz)
    return {"durum": cevap.status_code, "govde": cevap.get_json()}


def _gonder(yol: str, govde: dict[str, Any]) -> dict[str, Any]:
    """`POST` — gövde doğrulaması uçta yapılır, burada DEĞİL."""
    cevap = _istemci().post(yol, json=govde)
    return {"durum": cevap.status_code, "govde": cevap.get_json()}


def envanter() -> dict[str, Any]:
    """Araç listesi `/api/meta` ile tutuyor mu — sözleşme ikiye bölündü mü?

    Ölçüt 2'nin bekçisi. `ARACLAR`daki her uç gerçekten var olmalı;
    olmayan bir uç sarmak, ajana var olmayan bir yetenek vaat etmektir.
    """
    import web_app

    # Kaynak Flask'in KAYIT TABLOSU — `/` govdesinin metin bicimi degil.
    # Ilk surum `/` cevabini ayristiriyordu ve bu yanlisti: bir sozlesme
    # denetimi, denetledigi seyin GORUNTUSUNU degil KENDISINI okumali.
    kayitli = {str(k.rule) for k in web_app.app.url_map.iter_rules()}
    eksik = sorted(u for u in ARACLAR.values() if u not in kayitli)
    # Ters yon de onemli: sarilmamis bir uc, ajanin goremedigi bir yetenek.
    sarilmamis = sorted(
        y for y in kayitli
        if y.startswith("/api") and y not in set(ARACLAR.values()))
    return {
        "arac_sayisi": len(ARACLAR),
        "araclar": dict(sorted(ARACLAR.items())),
        "kayitli_uclar": sorted(y for y in kayitli if y.startswith("/api")),
        # Bir araç var olmayan bir ucu sariyorsa, ajana olmayan bir yetenek
        # vaat edilmis demektir — bu KIRMIZIDIR.
        "olmayan_uca_baglanan": eksik,
        # Sarilmamis uc bir kusur DEGIL, bir kapsam bilgisi.
        "sarilmamis_uclar": sarilmamis,
        "meta_okundu": _al("/api/meta")["durum"] == 200,
        "saglam": not eksik,
    }


def sunucu() -> Any:
    """MCP sunucusunu kurar. `mcp` kurulu değilse anlaşılır biçimde düşer."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as e:  # pragma: no cover - ortama bagli
        raise SystemExit(
            "mcp kurulu degil — `pip install -e \"backend[mcp]\"`") from e

    s = MCPServer("spor-toto")

    @s.tool()
    def yetenekler() -> dict[str, Any]:
        """Motorun yetenek envanteri: modlar, preset'ler, ızgaralar, sezonlar."""
        return _al("/api/meta")

    @s.tool()
    def kupon_uret(picks: str, mode: str = "fix16",
                   budget: int | None = None,
                   probs: str | None = None,
                   use_bayes: bool = False,
                   bayes_preset: str | None = None) -> dict[str, Any]:
        """15 maçlık seçimden kaplama kuponu üretir (`/api/solve` ile aynı yol)."""
        govde: dict[str, Any] = {"picks": picks, "mode": mode,
                                 "use_bayes": use_bayes}
        if budget is not None:
            govde["budget"] = budget
        if probs is not None:
            govde["probs"] = probs
        if bayes_preset is not None:
            govde["bayes_preset"] = bayes_preset
        return _gonder("/api/solve", govde)

    @s.tool()
    def hafta_tahmini(limit: int | None = None,
                      genis: bool = False) -> dict[str, Any]:
        """Yaklaşan maçlara 1/0/2 + **ölçülmüş** isabet (ikisi ayrılmaz)."""
        return _al("/api/tahmin", limit=limit, genis=1 if genis else None)

    @s.tool()
    def hafta_istatistigi(last: int | None = None,
                          sezon: str | None = None) -> dict[str, Any]:
        """Sezon istatistikleri: dağılım, seyir, bantlar, piyasa oranları."""
        return _al("/api/stats", last=last, sezon=sezon)

    @s.tool()
    def pazarlar(yontem: str | None = None) -> dict[str, Any]:
        """Alt/üst 2,5 ve Asya handikabı — ölçülmüş kalibrasyonlarıyla."""
        return _al("/api/pazar", yontem=yontem)

    @s.tool()
    def benzer_maclar(oran_1: float, oran_0: float, oran_2: float,
                      tolerans: float | None = None) -> dict[str, Any]:
        """"Bu oranda geçmişte ne oldu" — 31 bin maçlık korpusta arar."""
        return _al("/api/benzer", oran_1=oran_1, oran_0=oran_0,
                   oran_2=oran_2, tolerans=tolerans)

    @s.tool()
    def kupon_dogrula(picks: str, rows: str) -> dict[str, Any]:
        """Kullanıcının kendi kuponunu 14-garanti kaplamaya karşı doğrular."""
        return _gonder("/api/health/kupon", {"picks": picks, "rows": rows})

    @s.tool()
    def geri_test(last: int | None = None,
                  sweep: bool = False) -> dict[str, Any]:
        """Oranlardan strateji üretip geçmiş haftaları motorla koşturur."""
        return _al("/api/backtest", last=last, sweep=1 if sweep else None)

    return s


def main(argv: list[str] | None = None) -> int:
    """`--envanter` ölçütü denetler; argümansız stdio sunucusunu açar."""
    ap = argparse.ArgumentParser(description="Spor Toto MCP yuzeyi (deney)")
    ap.add_argument("--envanter", action="store_true",
                    help="araclar /api/meta ile tutuyor mu — dosya yazmaz")
    args = ap.parse_args(argv)

    if args.envanter:
        print(json.dumps(envanter(), ensure_ascii=False, indent=1))
        return 0

    sunucu().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
