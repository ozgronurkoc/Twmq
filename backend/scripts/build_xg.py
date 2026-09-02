#!/usr/bin/env python3
"""Şut → xG kalibrasyonu — **vekilin katsayısını ölçülmüş hale getirir.**

`spor_toto/disari.py` xG'yi *"türetilemeyen"* diye kayda geçirmişti ve
gerekçesinin ilk yarısı artık geçersiz: `hudl/open-data` (eski adıyla
`statsbomb/open-data`) olay düzeyi veriyi serbestçe yayımlıyor ve her şutta
`shot.statsbomb_xg` alanı var. Understat'ın `robots.txt`'ine ya da fbref'in
Cloudflare'ine gerek kalmadı.

**Ama gerekçenin ikinci yarısı ayakta.** Depoyu lig-sezon lig-sezon saydım:
Süper Lig yok, alt İngiliz ligleri (E1/E2/E3/EC) yok. Korpusun penceresiyle
(2021/22–2024/25) kesişim 31.103 maçta topu topu 92 maç — ve o 92'nin hepsi
tek takıma yanlı (PSG'nin Ligue 1 maçları, Leverkusen'in Bundesliga maçları).
Yani StatsBomb `/tahmin` için bir GİRDİ olamaz; canlı akışı da yok, veri
maçlardan yıllar sonra yayımlanıyor.

Kullanılabilir olan şey başka: **dört lig-sezon eksiksiz.**

    Premier League 2015/16   380 mac    football-data 1516/E0
    La Liga        2015/16   380 mac    football-data 1516/SP1
    Serie A        2015/16   380 mac    football-data 1516/I1
    Ligue 1        2015/16   377 mac    football-data 1516/F1

Bu 1.517 maçın hem gerçek xG'si (StatsBomb) hem şut sayımı (football-data
`HS/HST`) var. Korpus zaten `ev_sut`/`ev_isabet` taşıyor ama onlardan
kurulacak bir "fakir adamın xG'si"nin katsayısı bugüne kadar **keyfî**
olurdu. Bu kesit tam olarak onu çözer: vekil gerçek xG'ye karşı kalibre
edilir, kalibre edilmiş vekil 31.103 maçın tamamına uygulanır.

**StatsBomb böylece üretim girdisi değil, KALİBRASYON REFERANSI olur.**

─── Lisans — betiğin biçimini belirleyen kısıt ──────────────────────────

`LICENSE.pdf`, "StatsBomb Public Data User Agreement". Madde 1.2.1 kullanıcının
veriyi *"edit, distort, distribute, reproduce, sell or in any way provide ...
to any external or third party"* etmesini yasaklıyor. `ozgronurkoc/Twmq`
public bir depo; dolayısıyla **ham JSON commit edilemez.** Girişteki cümle
ise şunu açıkça serbest bırakıyor: *"Any analysis or conclusions that are
created as a result of using this data, may be shared publicly."*

Bu yüzden depoya giren tek şey **katsayılar ve ölçüm raporudur**; maç başına
xG satırı bile girmez. Madde 1.4 ayrıca künye ister: StatsBomb verisinden
oluşan analizin her yayımı StatsBomb marka logosuyla künyelenmek zorundadır
(`docs/VERI_TOPLAMA_VE_ISLEME.md`). Deponun diğer kaynakları (CC0, kamu malı)
böyle bir yükümlülük taşımıyordu; bu ilk.

─── Neden ham dosyalar diske yazılmıyor ─────────────────────────────────

Diğer üreticiler kaynağı `_kaynak/` altına indirip önbelleklerler. Burada
olmaz: bir olay dosyası ~3,4 MB ve 1.517 tane var — **~5,2 GB.** Olay
dosyaları akışta işlenir, maç başına dört sayıya indirgenir ve atılır. Diske
yazılan tek şey o özetin `_kaynak/xg_ozet.jsonl` kaydıdır (birkaç yüz KB) ve
işi yeniden başlatılabilir kılmaktır — indirme sıralı ve ~25 dakika sürer.

─── Eşleme: ada göre değil, MAÇA göre ───────────────────────────────────

StatsBomb "Sporting Gijón" der, football-data "Sp Gijon". Bulanık ad eşlemesi
bu depoda zaten bir zayıf nokta (`sehir_rapor.json`: 12 takım eşleşmiyor).
Burada birincil anahtar **(lig, tarih ±1 gün, ev golü, deplasman golü)**;
ad benzerliği yalnızca çakışma çözücü. Böylece ad haritası küratörlük değil
eşlemenin **çıktısı** olur — rapora yazılır ve denetlenebilir.

Tarih toleransı ±1 gündür çünkü StatsBomb yerel tarihi, football-data
İngiltere tarihini yazar; geç başlayan maçlar iki kaynakta bir gün kayabilir.

─── Neden numpy yok ─────────────────────────────────────────────────────

`scripts/__init__.py` üretici katmanın hafif kalmasını istiyor. Üç bilinmeyenli
en küçük kareler zaten 3×3'lük bir normal denklem sistemidir; Gauss elemesi
yirmi satır. Bir bağımlılık eklemeye değmez.

Kullanım:

    python scripts/build_xg.py --dry-run     # kapsama + katsayi ozeti, yazmaz
    python scripts/build_xg.py               # data/xg/ altina iki dosya
    python scripts/build_xg.py --limit 40    # gelistirirken kucuk kesit
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from scripts._ortak import indir_bellek

VARSAYILAN_CIKTI = KOK / "data" / "xg"

from scripts.build_avrupa import sadelestir

UA = "Mozilla/5.0 (compatible; spor-toto-lab/1.0)"
SB_KOK = "https://raw.githubusercontent.com/hudl/open-data/master/data"
FD_URL = "https://www.football-data.co.uk/mmz4281/{sezon}/{lig}.csv"

#: Kalibrasyon kesiti. Yalnizca **eksiksiz** lig-sezonlar; tek takima
#: indirgenmis olanlar (Bundesliga 23/24 = yalniz Leverkusen, Ligue 1
#: 21/22-22/23 = yalniz PSG) buraya girmez — 34 macin 34'u ayni takimin
#: oldugu bir kesitte olculen katsayi o takimin sut profilini olcer.
KESIT: tuple[tuple[int, int, str, str], ...] = (
    (2, 27, "E0", "Premier League 2015/16"),
    (11, 27, "SP1", "La Liga 2015/16"),
    (12, 27, "I1", "Serie A 2015/16"),
    (7, 27, "F1", "Ligue 1 2015/16"),
)

#: football-data sezon etiketi — KESIT'teki dort lig-sezon da 2015/16.
FD_SEZON = "1516"

#: Tarih toleransi (gun). Bkz. modul docstring'i.
GUN_TOLERANSI = 1

#: Penalti xG'si ~0,79 sabittir ve sut sayimiyla iliskisi yoktur; acik oyun
#: xG'siyle ayni regresyona sokulursa katsayilari kirletir. Ayri tasinir.
PENALTI = "Penalty"


# ─── indirme ──────────────────────────────────────────────────────────────

#: Bellege indirme TEK kaynaktan: `scripts._ortak.indir_bellek`.
#: Ayni govde `build_fixtures.indir` olarak da yaziliydi.
_getir = indir_bellek


def sb_maclari(comp: int, sezon: int) -> list[dict[str, Any]]:
    """Bir lig-sezonun StatsBomb maç listesi."""
    ham = _getir(f"{SB_KOK}/matches/{comp}/{sezon}.json")
    if ham is None:
        return []
    return json.loads(ham)


def sb_xg(mac_id: int) -> dict[str, Any] | None:
    """Bir maçın olay dosyasını akışta özetle: takım başına xG ve şut.

    Dönen sözlükte takım **adları** anahtardır; ev/deplasman ayrımı burada
    yapılmaz çünkü olay dosyası hangi takımın ev sahibi olduğunu söylemez —
    onu maç listesi söyler ve eşleme orada yapılır.
    """
    ham = _getir(f"{SB_KOK}/events/{mac_id}.json")
    if ham is None:
        return None
    try:
        olaylar = json.loads(ham)
    except json.JSONDecodeError:
        print(f"  events/{mac_id}.json cozulemedi", file=sys.stderr)
        return None
    out: dict[str, dict[str, float]] = {}
    for o in olaylar:
        if (o.get("type") or {}).get("name") != "Shot":
            continue
        sut = o.get("shot") or {}
        takim = (o.get("team") or {}).get("name")
        if not takim:
            continue
        k = out.setdefault(takim, {"xg": 0.0, "pen_xg": 0.0, "sut": 0.0})
        xg = float(sut.get("statsbomb_xg") or 0.0)
        if (sut.get("type") or {}).get("name") == PENALTI:
            k["pen_xg"] += xg
        else:
            k["xg"] += xg
            k["sut"] += 1.0
    return out


def ozet_uret(limit: int | None, onbellek: Path) -> list[dict[str, Any]]:
    """Kesitin maç başına xG özeti. `_kaynak/xg_ozet.jsonl` ile yeniden başlatılabilir.

    Sıralı indirir. Paralellik bilerek yok: kaynak tek bir kamu deposu ve
    1.517 eşzamanlı istek kibarlık sınırını zorlar; ~25 dakika kabul edilebilir
    çünkü bu betik elle, seyrek koşar (`scripts/check.sh` onu koşmaz, commit
    edilmiş katsayı dosyasını okur).
    """
    bilinen: dict[int, dict[str, Any]] = {}
    if onbellek.exists():
        for satir in onbellek.read_text(encoding="utf-8").splitlines():
            if satir.strip():
                k = json.loads(satir)
                bilinen[int(k["mac_id"])] = k
        print(f"  onbellek: {len(bilinen)} mac zaten ozetlenmis")

    out: list[dict[str, Any]] = []
    onbellek.parent.mkdir(parents=True, exist_ok=True)
    with open(onbellek, "a", encoding="utf-8") as kayit:
        for comp, sezon, lig, ad in KESIT:
            maclar = sb_maclari(comp, sezon)
            if not maclar:
                print(f"  {ad}: mac listesi alinamadi", file=sys.stderr)
                continue
            if limit:
                maclar = maclar[:limit]
            print(f"  {ad} ({lig}): {len(maclar)} mac")
            for i, m in enumerate(maclar, 1):
                mac_id = int(m["match_id"])
                if mac_id in bilinen:
                    out.append(bilinen[mac_id])
                    continue
                takimlar = sb_xg(mac_id)
                if not takimlar:
                    continue
                ev = m["home_team"]["home_team_name"]
                dep = m["away_team"]["away_team_name"]
                e = takimlar.get(ev) or {"xg": 0.0, "pen_xg": 0.0, "sut": 0.0}
                d = takimlar.get(dep) or {"xg": 0.0, "pen_xg": 0.0, "sut": 0.0}
                kayit_satiri = {
                    "mac_id": mac_id, "lig": lig, "tarih": m["match_date"],
                    "ev": ev, "dep": dep,
                    "ev_gol": int(m["home_score"]),
                    "dep_gol": int(m["away_score"]),
                    "ev_xg": round(e["xg"], 6), "dep_xg": round(d["xg"], 6),
                    "ev_pen_xg": round(e["pen_xg"], 6),
                    "dep_pen_xg": round(d["pen_xg"], 6),
                    "ev_sb_sut": int(e["sut"]), "dep_sb_sut": int(d["sut"]),
                }
                out.append(kayit_satiri)
                kayit.write(json.dumps(kayit_satiri, ensure_ascii=False) + "\n")
                kayit.flush()
                if i % 50 == 0:
                    print(f"    {i}/{len(maclar)}")
    return out


# ─── football-data tarafi ─────────────────────────────────────────────────

def _tam_sayi(ham: str | None) -> int | None:
    h = (ham or "").strip()
    return int(h) if h.isdigit() else None


def fd_satirlari(lig: str) -> list[dict[str, Any]]:
    """football-data 1516 satırları — gerekli sütunu eksik olan atılır."""
    ham = _getir(FD_URL.format(sezon=FD_SEZON, lig=lig))
    if ham is None:
        return []
    metin = ham.decode("utf-8-sig", errors="replace")
    out: list[dict[str, Any]] = []
    for r in csv.DictReader(io.StringIO(metin)):
        tarih = None
        for bicim in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                tarih = datetime.strptime((r.get("Date") or "").strip(), bicim)
                break
            except ValueError:
                continue
        if tarih is None:
            continue
        alanlar = {ad: _tam_sayi(r.get(ad))
                   for ad in ("FTHG", "FTAG", "HS", "AS", "HST", "AST")}
        if any(v is None for v in alanlar.values()):
            continue
        out.append({
            "lig": lig, "tarih": tarih.date(),
            "ev": (r.get("HomeTeam") or "").strip(),
            "dep": (r.get("AwayTeam") or "").strip(),
            **alanlar,
        })
    return out


def _ad_yakinligi(a: str, b: str) -> float:
    """Sadeleştirilmiş adların ortak kelime payı — yalnızca çakışma çözücü."""
    ka, kb = set(sadelestir(a).split()), set(sadelestir(b).split())
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / len(ka | kb)


def eslestir(ozetler: list[dict[str, Any]], fd: dict[str, list[dict[str, Any]]]
             ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """`(eslesenler, eslesmeyenler, ad_haritasi)`.

    Anahtar `(lig, skor)`; tarih ±1 gün süzer; birden fazla aday kalırsa ad
    yakınlığı çözer. Bir football-data satırı **en fazla bir kez** eşleşir.
    """
    indeks: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    for lig, satirlar in fd.items():
        for s in satirlar:
            indeks.setdefault((lig, s["FTHG"], s["FTAG"]), []).append(s)

    kullanilan: set[int] = set()
    eslesen: list[dict[str, Any]] = []
    eslesmeyen: list[dict[str, Any]] = []
    ad_haritasi: dict[str, str] = {}

    for o in sorted(ozetler, key=lambda x: (x["lig"], x["tarih"])):
        gun = datetime.strptime(o["tarih"], "%Y-%m-%d").date()
        adaylar = [s for s in indeks.get((o["lig"], o["ev_gol"], o["dep_gol"]), ())
                   if id(s) not in kullanilan
                   and abs((s["tarih"] - gun).days) <= GUN_TOLERANSI]
        if not adaylar:
            eslesmeyen.append(o)
            continue
        if len(adaylar) > 1:
            adaylar.sort(key=lambda s: -(_ad_yakinligi(o["ev"], s["ev"])
                                         + _ad_yakinligi(o["dep"], s["dep"])))
        s = adaylar[0]
        kullanilan.add(id(s))
        ad_haritasi.setdefault(o["ev"], s["ev"])
        ad_haritasi.setdefault(o["dep"], s["dep"])
        eslesen.append({**o, "fd_ev": s["ev"], "fd_dep": s["dep"],
                        "HS": s["HS"], "AS": s["AS"],
                        "HST": s["HST"], "AST": s["AST"]})
    return eslesen, eslesmeyen, ad_haritasi


# ─── en kucuk kareler (stdlib) ────────────────────────────────────────────

def _coz(A: list[list[float]], b: list[float]) -> list[float] | None:
    """Kısmi pivotlu Gauss elemesi. Tekil sistemde `None`."""
    n = len(b)
    M = [[*satir, b[i]] for i, satir in enumerate(A)]
    for s in range(n):
        p = max(range(s, n), key=lambda i: abs(M[i][s]))
        if abs(M[p][s]) < 1e-12:
            return None
        M[s], M[p] = M[p], M[s]
        for i in range(s + 1, n):
            f = M[i][s] / M[s][s]
            for j in range(s, n + 1):
                M[i][j] -= f * M[s][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))) / M[i][i]
    return x


def uydur(ornekler: list[tuple[float, float, float]]) -> dict[str, float] | None:
    """`xg ≈ a·isabet + b·(sut − isabet) + c` — normal denklemler.

    Örnek üçlüsü `(isabet, isabetsiz, xg)`. Dönen sözlükte katsayılar, artık
    standart sapması ve R² var.
    """
    if len(ornekler) < 30:
        return None
    X = [(i, s, 1.0) for i, s, _ in ornekler]
    y = [g for _, _, g in ornekler]
    A = [[sum(X[k][r] * X[k][c] for k in range(len(X))) for c in range(3)]
         for r in range(3)]
    rhs = [sum(X[k][r] * y[k] for k in range(len(X))) for r in range(3)]
    kat = _coz(A, rhs)
    if kat is None:
        return None
    a, b, c = kat
    artiklar = [y[k] - (a * X[k][0] + b * X[k][1] + c) for k in range(len(X))]
    n = len(y)
    ort = sum(y) / n
    ss_res = sum(r * r for r in artiklar)
    ss_tot = sum((v - ort) ** 2 for v in y)
    return {
        "isabet": round(a, 6), "isabetsiz": round(b, 6), "sabit": round(c, 6),
        "n": n,
        "artik_ss": round((ss_res / n) ** 0.5, 6),
        "r2": round(1.0 - ss_res / ss_tot, 6) if ss_tot > 0 else 0.0,
    }


def _ornekler(eslesen: list[dict[str, Any]], ev_mi: bool,
              ligler: set[str] | None = None) -> list[tuple[float, float, float]]:
    sut, isabet, xg = ("HS", "HST", "ev_xg") if ev_mi else ("AS", "AST", "dep_xg")
    return [(float(r[isabet]), float(r[sut] - r[isabet]), float(r[xg]))
            for r in eslesen
            if (ligler is None or r["lig"] in ligler) and r[sut] >= r[isabet]]


def _rmse(kat: dict[str, float],
          ornekler: list[tuple[float, float, float]]) -> float:
    if not ornekler:
        return 0.0
    hata = [(kat["isabet"] * i + kat["isabetsiz"] * s + kat["sabit"]) - g
            for i, s, g in ornekler]
    return round((sum(h * h for h in hata) / len(hata)) ** 0.5, 6)


def lig_disarida_birak(eslesen: list[dict[str, Any]]) -> dict[str, Any]:
    """Her lig sırayla dışarıda: katsayı lige ne kadar duyarlı?

    Bu ölçüm olmadan vekil 22 lige uygulanamaz. Dört ligde uydurulmuş bir
    katsayının beşinci bir ligde ne yapacağını bilmiyoruz; bildiğimiz tek şey
    **dördün birbirine ne kadar benzediğidir** ve rapor onu yazar.
    """
    out: dict[str, Any] = {}
    tum = {r["lig"] for r in eslesen}
    for lig in sorted(tum):
        kalan = tum - {lig}
        blok: dict[str, Any] = {}
        for yan, ev_mi in (("ev", True), ("dep", False)):
            kat = uydur(_ornekler(eslesen, ev_mi, kalan))
            if kat is None:
                continue
            blok[yan] = {**kat, "disarida_rmse": _rmse(
                kat, _ornekler(eslesen, ev_mi, {lig}))}
        out[lig] = blok
    return out


# ─── dogrulama ────────────────────────────────────────────────────────────

def dogrula(kalibrasyon: dict[str, Any], kapsama: float,
            en_az_kapsama: float) -> list[str]:
    """Yazmadan önceki kapı. Boş liste = geçti.

    İşaret kontrolü süs değil: isabetli şutun katsayısı isabetsizinkinden
    büyük olmalı ve ikisi de pozitif olmalı. Değilse vekil ters uydurulmuş
    demektir ve o dosyayı yazmak sessiz bir yalan olurdu.
    """
    hatalar: list[str] = []
    if kapsama < en_az_kapsama:
        hatalar.append(f"kapsama {kapsama:.1%} < {en_az_kapsama:.1%}")
    for yan in ("ev", "dep"):
        k = kalibrasyon.get(yan)
        if not k:
            hatalar.append(f"{yan}: katsayi uydurulamadi")
            continue
        if k["isabet"] <= 0:
            hatalar.append(f"{yan}: isabet katsayisi pozitif degil ({k['isabet']})")
        if k["isabetsiz"] < 0:
            hatalar.append(f"{yan}: isabetsiz katsayisi negatif ({k['isabetsiz']})")
        if k["isabet"] <= k["isabetsiz"]:
            hatalar.append(f"{yan}: isabetli sut isabetsizden degerli degil "
                           f"({k['isabet']} <= {k['isabetsiz']})")
    return hatalar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=VARSAYILAN_CIKTI)
    ap.add_argument("--limit", type=int, default=None,
                    help="lig basina en fazla kac mac (gelistirme icin)")
    ap.add_argument("--en-az-kapsama", type=float, default=0.95)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    onbellek = args.out_dir / "_kaynak" / "xg_ozet.jsonl"
    print("StatsBomb ozetleri:")
    ozetler = ozet_uret(args.limit, onbellek)
    if not ozetler:
        print("StatsBomb kesiti bos", file=sys.stderr)
        return 1

    print("\nfootball-data 1516:")
    fd: dict[str, list[dict[str, Any]]] = {}
    for _, _, lig, _ in KESIT:
        fd[lig] = fd_satirlari(lig)
        print(f"  {lig}: {len(fd[lig])} satir")

    eslesen, eslesmeyen, ad_haritasi = eslestir(ozetler, fd)
    toplam = len(eslesen) + len(eslesmeyen)
    kapsama = (len(eslesen) / toplam) if toplam else 0.0
    print(f"\nEsleme: {len(eslesen)}/{toplam} = {kapsama:.1%}")
    for o in eslesmeyen[:15]:
        print(f"  eslesmedi  {o['lig']} {o['tarih']} {o['ev']} {o['ev_gol']}"
              f"-{o['dep_gol']} {o['dep']}")

    kalibrasyon = {yan: uydur(_ornekler(eslesen, ev_mi))
                   for yan, ev_mi in (("ev", True), ("dep", False))}
    for yan, k in kalibrasyon.items():
        if k:
            print(f"  {yan}: xg = {k['isabet']:.4f}*isabet + "
                  f"{k['isabetsiz']:.4f}*isabetsiz + {k['sabit']:.4f}   "
                  f"R2={k['r2']:.3f}  n={k['n']}")

    hatalar = dogrula(kalibrasyon, kapsama, args.en_az_kapsama)
    if hatalar:
        print("\nDOGRULAMA BASARISIZ — dosya yazilmadi:", file=sys.stderr)
        for h in hatalar:
            print(f"  {h}", file=sys.stderr)
        return 1

    dis = lig_disarida_birak(eslesen)
    print("\nLig disarida birak (disaridaki ligde RMSE):")
    for lig, blok in dis.items():
        parca = "  ".join(f"{y}={b['disarida_rmse']:.3f}" for y, b in blok.items())
        print(f"  {lig:<5}{parca}")

    # StatsBomb sut sayimi ile football-data'nin HS'i ayni sey mi? Tanilama:
    # ikisi ayri tanimlar (bloke edilen sutlar, ofsayt sonrasi vurus...) ve
    # aralarindaki fark vekilin tavanini belirler.
    sb = [r["ev_sb_sut"] + r["dep_sb_sut"] for r in eslesen]
    fdd = [r["HS"] + r["AS"] for r in eslesen]
    n = len(eslesen) or 1
    sut_farki = round(sum(a - b for a, b in zip(sb, fdd)) / n, 3)

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "xg_kalibrasyon.json").write_text(json.dumps({
        "uretildi": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kaynak": "StatsBomb Open Data (hudl/open-data)",
        "kesit": [f"{ad} [{lig}]" for _, _, lig, ad in KESIT],
        "mac": len(eslesen),
        "katsayilar": kalibrasyon,
        "lig_disarida": dis,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.out_dir / "xg_rapor.json").write_text(json.dumps({
        "uretildi": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kaynak": "StatsBomb Open Data (hudl/open-data) + football-data.co.uk",
        "lisans": ("StatsBomb Public Data User Agreement — md. 1.2.1 ham "
                   "veriyi cogaltmayi/dagitmayi yasaklar, bu yuzden depoya "
                   "yalnizca KATSAYI ve RAPOR girer; md. 1.4 yayimlanan her "
                   "analizin StatsBomb logosuyla kunyelenmesini ister"),
        "eslesen": len(eslesen), "eslesmeyen": len(eslesmeyen),
        "kapsama": round(kapsama, 4),
        "sb_eksi_fd_ortalama_sut": sut_farki,
        "ad_haritasi": dict(sorted(ad_haritasi.items())),
        "eslesmeyenler": [f"{o['lig']} {o['tarih']} {o['ev']}-{o['dep']}"
                          for o in eslesmeyen],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nyazildi: {args.out_dir}/xg_kalibrasyon.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
