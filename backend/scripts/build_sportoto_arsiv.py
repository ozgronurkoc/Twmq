#!/usr/bin/env python3
"""Spor Toto'nun RESMI arsivinden hafta kaydi ve ikramiye tablosu ceker.

    python scripts/build_sportoto_arsiv.py              # cek ve yaz
    python scripts/build_sportoto_arsiv.py --dry-run    # yazmadan kapsama raporu
    python scripts/build_sportoto_arsiv.py --sezon 2023/2024
    python scripts/build_sportoto_arsiv.py --kaynak-dizin /tmp/ham   # kayitli ham JSON'dan

NEDEN VAR
=========
`docs/VERI_TOPLAMA_VE_ISLEME.md` §3.1 uzun sure sunu yaziyordu:

    sportoto.gov.tr | Resmi sonuc arsivi | Kullanilamadi
                    | Toplu, makine dostu arsiv ucu bulunamadi

Bu **yanlisti** ve nedeni olculdu: `sportoto.gov.tr` bir Next.js uygulamasi,
hafta verisini istemci tarafindan ayri bir hosttan cekiyor
(`webapi.sportoto.gov.tr`). Uclar sayfa kaynaginda degil, JS parcalarinda
duruyor — bu yuzden ilk aramada gorunmedi.

Bulunan uclar (hepsi kimlik dogrulamasiz, acik):

    /api/GameRound                                TUM haftalar (her sezon)
    /api/GameResult/GetGameResultByGameRoundId    haftanin IKRAMIYE tablosu

`GetGameRoundYears` (sezon listesi) de var ama BU BETIK ONU CAGIRMIYOR:
`/api/GameRound` zaten butun sezonlarin butun haftalarini tek seferde
veriyor, yani ayri bir sezon listesi ikinci bir ag cagrisi olurdu ve hicbir
sey eklemezdi. Uzun sure bir `YIL_URL` sabiti duruyordu ve hicbir yerden
okunmuyordu — cagrilmayan bir uc, uc degil yorumdur; burada oyle duruyor.

Bu, deponun ilk **resmi** veri kaynagidir. Oteki dordu ucuncu parti:
football-data piyasa orani, sportototahmin hafta payload'i, iddaa bulteni,
openfootball fikstur. Burasi Spor Toto'nun kendisi — ikramiye ve kazanan
adedinde baska hicbir kaynak ona esit degildir.

NE COZER
========
§10.1'in havuz eksenini. O bolum "ikramiye ve havuz verisi yok" diye acildi,
sonra §6B'nin ELLE girilen sinifiyla n = 3 haftaya cikti ve orada takildi:

    Bu, B2'nin (populerlik modeli) asil isidir ve hafta biriktikce kosulur.
    n = 2 iken hicbir sayi sonuc degildir.

Bu betik n'i bir hamlede ~220'ye cikarir ve elle girise gerek birakmaz.

NE COZMEZ — ve bu acikca yazilir
=================================
Resmi ucta **mac listesi yok**. Haftanin 15 maci yalnizca bir BULTEN GORSELI
olarak yayimlaniyor (`attachment.attachmentName` -> `/image/<ad>`), yani
15 maclik 1/0/2 dizisi bu kaynaktan DOGRUDAN gelmiyor. Gorseller de ancak
2023/2024'ten itibaren erisilebiliyor; 2021/22 ve 2022/23 icin 404.

Dolayisiyla bu betigin cikardigi sey **hafta + kapanis tarihi + ikramiye**dir;
kupon dizisi degil. Kupon ayagi icin §10.2 hala acik ve yolu Faz 2'dir
(bulten bilesimini `build_odds.py`'nin eslestiricisiyle skora baglamak).
Doktrin 2 geregi eksik olan uydurulmaz: `payout` alinamayan hafta
`payout: null` tasir ve raporda sayilir.

CIKTI
=====
    data/sportoto_arsiv/<sezon>.json        sezon basina hafta kaydi (surumlenir)
    data/sportoto_arsiv/arsiv_rapor.json    kapsama raporu (surumlenir)
    data/sportoto_arsiv/_kaynak/*.json      indirilen ham payload (git disi)

Dosya `st_history_2025_26.json` ile KARISMAZ ve `/api/stats` yoluna girmez:
biri kupon sonuc arsivi, oteki ikramiye/havuz arsivi. Ayni sezonu iki dosya
birden anlatabilir ve bu bilerek boyledir — kokenleri farklidir.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
# Kardes betiklerle paylasilan SAF STDLIB yardimcilar. `spor_toto` DEGIL:
# bu betik GitHub Actions'ta hicbir bagimlilik kurulmadan kosuyor ve
# `scripts/_ortak.py` tam da bunun icin stdlib disina cikmiyor
# (bekcisi `tests/test_scripts_ortak.py`).
sys.path.insert(0, str(KOK))

from scripts._ortak import indir_json

CIKTI_DIZIN = KOK / "data" / "sportoto_arsiv"
UA = "spor-toto-lab/1.0 (kisisel arsiv analizi)"

TABAN = "https://webapi.sportoto.gov.tr"
HAFTA_URL = f"{TABAN}/api/GameRound"
SONUC_URL = f"{TABAN}/api/GameResult/GetGameResultByGameRoundId"
GORSEL_TABAN = f"{TABAN}/image/"

KAYNAK_ADI = "sportoto.gov.tr resmi arsivi (webapi.sportoto.gov.tr) — RESMI KAYNAK"

#: Ucun kademe alan adlari -> kupondaki dogru sayisi. Sira bilincli:
#: rapor ve JSON'da 15'ten 12'ye dogru okunur, kupon duzeniyle tutarli.
KADEMELER: tuple[tuple[int, str, str], ...] = (
    (15, "fifteenWinCount", "fifteenWinPrize"),
    (14, "fourteenWinCount", "fourteenWinPrize"),
    (13, "thirteenWinCount", "thirteenWinPrize"),
    (12, "twelveWinCount", "twelveWinPrize"),
)

HAFTA_DESENI = re.compile(r"^\s*(\d{1,2})\s*\.\s*Hafta\s*$", re.IGNORECASE)


# ─── indirme ──────────────────────────────────────────────────────────────────

#: Indirme TEK kaynaktan: `scripts._ortak.indir_json`. Ayni govde iki
#: betikte birebir yaziliydi ve ikisi de Actions'ta depoya commit atiyor.


def _govde(payload: Any) -> Any:
    """`{object, status, isSucceed, message}` sarmalini acar.

    `isSucceed: false` bir hatadir ve yutulmaz. Ama `object: null` +
    `isSucceed: true` **hata degildir** — ucun "kayit yok" cevabidir
    (ornegin heniz kapanmamis hafta) ve None dondurulur.
    """
    if not isinstance(payload, dict):
        return payload
    if payload.get("isFailed") is True or payload.get("isSucceed") is False:
        raise RuntimeError(f"API basarisiz: {payload.get('message')}")
    return payload.get("object")


# ─── ayristirma ───────────────────────────────────────────────────────────────

def hafta_no(ad: str) -> int | None:
    """"9. Hafta" -> 9. Desene uymayan ad TAHMIN EDILMEZ, None doner.

    Doktrin 2: hafta numarasi uydurulmaz. Uymayan kayit `data_warnings`a
    yazilir ve `week: null` ile durur — elenmez, cunku ikramiye tablosu
    hafta numarasi olmadan da gecerli bir kayittir.
    """
    m = HAFTA_DESENI.match(ad or "")
    return int(m.group(1)) if m else None


def sezon_anahtari(yil: str) -> str:
    """"2023/2024" -> "2023_24". Depo `data/super_toto/2026_27` ile ayni duzen."""
    parcalar = (yil or "").split("/")
    if len(parcalar) != 2 or not all(p.strip().isdigit() for p in parcalar):
        raise ValueError(f"anlasilmayan sezon: {yil!r}")
    return f"{parcalar[0].strip()}_{parcalar[1].strip()[-2:]}"


def _tarih(ham: Any) -> str | None:
    """ISO damgayi "YYYY-MM-DD HH:MM"e indirir. Bos/bozuksa None."""
    if not isinstance(ham, str) or not ham:
        return None
    # Uc "0001-01-01T00:00:00" yaziyor: alan bos demek, tarih degil.
    if ham.startswith("0001-01-01"):
        return None
    try:
        return datetime.fromisoformat(ham).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


def ikramiye_ayristir(nesne: Any) -> dict[str, Any] | None:
    """Sonuc ucunun govdesini `payout` blogua cevirir; eksikse None.

    Bir kademe sayisi None ise o kademe ATLANIR, sifir sayilmaz — "kimse
    bilemedi" ile "veri yok" ayri seylerdir ve ikisini karistirmak havuz
    modelini sessizce zehirler.
    """
    if not isinstance(nesne, dict):
        return None
    katlar: list[dict[str, Any]] = []
    for dogru, sayi_alani, odul_alani in KADEMELER:
        sayi = nesne.get(sayi_alani)
        odul = nesne.get(odul_alani)
        if sayi is None and odul is None:
            continue
        katlar.append({
            "correct": dogru,
            "winners": int(sayi) if isinstance(sayi, (int, float)) else None,
            "prize": float(odul) if isinstance(odul, (int, float)) else None,
        })
    if not katlar:
        return None
    aciklama = (nesne.get("resultDescription") or "").strip()
    return {
        "currency": "TRY",
        "tiers": katlar,
        "description": aciklama or None,
        "close_date": _tarih(nesne.get("gameRoundCloseDate")),
    }


def hafta_kaydi(ham: dict[str, Any], ikramiye: dict[str, Any] | None) -> dict[str, Any]:
    uyarilar: list[str] = []
    ad = (ham.get("name") or "").strip()
    no = hafta_no(ad)
    if no is None:
        uyarilar.append(f"hafta numarasi ad'dan cikarilamadi: {ad!r} — week null birakildi")

    kapanis = _tarih(ham.get("roundCloseDate"))
    if ikramiye and ikramiye.get("close_date") and kapanis:
        if ikramiye["close_date"] != kapanis:
            # Doktrin 4: celiski gizlenmez, biri "dogru" secilmez.
            uyarilar.append(
                f"kapanis tarihi iki uctan farkli geldi: hafta kaydi {kapanis}, "
                f"ikramiye kaydi {ikramiye['close_date']} — ikisi de saklandi"
            )

    ek = ham.get("attachment") or {}
    return {
        "week": no,
        "name": ad,
        "season": (ham.get("year") or "").strip(),
        "game_round_id": ham.get("id"),
        "close_date": kapanis,
        "is_published": bool(ham.get("isPublished")),
        "payout": ikramiye,
        # Gorsel INDIRILMEZ, yalnizca adreslenir: 15 maclik liste orada duruyor
        # ama okunmasi OCR ister ve o ayri bir istir (Faz 2).
        "bulletin_image": (
            {"name": ek.get("attachmentName"),
             "url": GORSEL_TABAN + urllib.parse.quote(ek["attachmentName"])}
            if ek.get("attachmentName") else None
        ),
        "data_warnings": uyarilar,
    }


# ─── dogrulama (doktrin 5: dogrulanmadan yazilmaz) ────────────────────────────

def dogrula(sezonlar: dict[str, list[dict[str, Any]]]) -> None:
    for anahtar, haftalar in sezonlar.items():
        assert haftalar, f"{anahtar}: bos sezon yazilamaz"
        kimlikler = [h["game_round_id"] for h in haftalar]
        assert len(kimlikler) == len(set(kimlikler)), f"{anahtar}: mukerrer game_round_id"
        numaralar = [h["week"] for h in haftalar if h["week"] is not None]
        assert len(numaralar) == len(set(numaralar)), f"{anahtar}: mukerrer hafta numarasi"
        sezon_adlari = {h["season"] for h in haftalar}
        assert len(sezon_adlari) == 1, f"{anahtar}: tek dosyada birden fazla sezon {sezon_adlari}"
        for h in haftalar:
            odeme = h["payout"]
            if odeme is None:
                continue
            dogrular = [k["correct"] for k in odeme["tiers"]]
            assert dogrular == sorted(dogrular, reverse=True), (
                f"{anahtar} hafta {h['week']}: kademeler 15->12 sirasinda degil"
            )
            for k in odeme["tiers"]:
                assert k["winners"] is None or k["winners"] >= 0, (
                    f"{anahtar} hafta {h['week']}: negatif kazanan adedi"
                )
                assert k["prize"] is None or k["prize"] >= 0, (
                    f"{anahtar} hafta {h['week']}: negatif ikramiye"
                )


# ─── giris ────────────────────────────────────────────────────────────────────

def _ham_haftalar(kaynak_dizin: Path | None) -> list[dict[str, Any]]:
    if kaynak_dizin:
        return json.loads((kaynak_dizin / "gamerounds.json").read_text(encoding="utf-8"))
    govde = _govde(indir_json(HAFTA_URL))
    if not isinstance(govde, list):
        raise RuntimeError("GameRound listesi beklenen bicimde degil")
    return govde


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Spor Toto resmi arsivi — hafta kaydi ve ikramiye tablosu"
    )
    ap.add_argument("--dry-run", action="store_true", help="dosya yazma, yalnizca kapsama raporu")
    ap.add_argument("--sezon", action="append", help="yalnizca bu sezon(lar), or. 2023/2024")
    ap.add_argument("--kaynak-dizin", type=Path, help="indirmek yerine kayitli ham JSON'dan oku")
    ap.add_argument("--out-dir", type=Path, default=CIKTI_DIZIN)
    args = ap.parse_args()

    simdi = datetime.now(timezone.utc)
    cekildi = simdi.strftime("%Y-%m-%d %H:%M")

    try:
        ham_haftalar = _ham_haftalar(args.kaynak_dizin)
    except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, ValueError) as e:
        print(f"hafta listesi alinamadi: {e}", file=sys.stderr)
        return 1

    if args.sezon:
        istenen = {s.strip() for s in args.sezon}
        ham_haftalar = [h for h in ham_haftalar if (h.get("year") or "").strip() in istenen]
        if not ham_haftalar:
            print(f"istenen sezon(lar) bulunamadi: {sorted(istenen)}", file=sys.stderr)
            return 1

    print(f"hafta kaydi   : {len(ham_haftalar)}")

    ham_ikramiye: dict[int, Any] = {}
    if args.kaynak_dizin:
        kayitli = json.loads(
            (args.kaynak_dizin / "gameresults.json").read_text(encoding="utf-8")
        )
        ham_ikramiye = {int(k): v for k, v in kayitli.items()}
    else:
        hatali = 0
        for i, h in enumerate(ham_haftalar, 1):
            kimlik = h.get("id")
            if not isinstance(kimlik, int):
                continue
            try:
                ham_ikramiye[kimlik] = _govde(
                    indir_json(f"{SONUC_URL}?id={kimlik}")
                )
            except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as e:
                # Tek haftanin dusmesi kosumu bitirmez; rapora yazilir.
                hatali += 1
                print(f"  uyari: hafta {kimlik} ikramiyesi alinamadi ({e})")
            if i % 25 == 0:
                print(f"  ... {i}/{len(ham_haftalar)}")
        if hatali:
            print(f"ikramiye hatasi: {hatali}")

    sezonlar: dict[str, list[dict[str, Any]]] = {}
    anlasilmayan: list[str] = []
    for h in ham_haftalar:
        try:
            anahtar = sezon_anahtari((h.get("year") or "").strip())
        except ValueError as e:
            anlasilmayan.append(str(e))
            continue
        kimlik = h.get("id")
        ham_odeme = ham_ikramiye.get(kimlik) if isinstance(kimlik, int) else None
        kayit = hafta_kaydi(h, ikramiye_ayristir(ham_odeme))
        sezonlar.setdefault(anahtar, []).append(kayit)

    for haftalar in sezonlar.values():
        # Sira: hafta numarasi. Numarasiz kayit sona duser, kaybolmaz.
        haftalar.sort(key=lambda k: (k["week"] is None, k["week"] or 0))

    toplam = sum(len(v) for v in sezonlar.values())
    odemeli = sum(1 for v in sezonlar.values() for h in v if h["payout"])
    gorselli = sum(1 for v in sezonlar.values() for h in v if h["bulletin_image"])
    uyarili = sum(1 for v in sezonlar.values() for h in v if h["data_warnings"])

    print(f"\nsezon         : {len(sezonlar)}")
    for anahtar in sorted(sezonlar):
        haftalar = sezonlar[anahtar]
        n_odeme = sum(1 for h in haftalar if h["payout"])
        print(f"  {anahtar}  hafta {len(haftalar):>3}  ikramiye {n_odeme:>3}"
              f"  ({haftalar[0]['season']})")
    print(f"toplam hafta  : {toplam}")
    print(f"ikramiyeli    : {odemeli}  (%{100 * odemeli / toplam:.1f})")
    print(f"bulten gorseli: {gorselli}")
    if uyarili:
        print(f"uyarili hafta : {uyarili}")
    if anlasilmayan:
        print(f"sezonu anlasilmayan kayit: {len(anlasilmayan)}")

    try:
        dogrula(sezonlar)
    except AssertionError as e:
        print(f"\nDOGRULAMA BASARISIZ, dosya yazilmadi: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "_kaynak").mkdir(exist_ok=True)
    if not args.kaynak_dizin:
        (args.out_dir / "_kaynak" / "gamerounds.json").write_text(
            json.dumps(ham_haftalar, ensure_ascii=False), encoding="utf-8")
        (args.out_dir / "_kaynak" / "gameresults.json").write_text(
            json.dumps({str(k): v for k, v in ham_ikramiye.items()}, ensure_ascii=False),
            encoding="utf-8")

    for anahtar in sorted(sezonlar):
        haftalar = sezonlar[anahtar]
        govde = {
            "meta": {
                "season": haftalar[0]["season"],
                "season_key": anahtar,
                "weeks": len(haftalar),
                "weeks_with_payout": sum(1 for h in haftalar if h["payout"]),
                "source": KAYNAK_ADI,
                "source_endpoints": [
                    "GET /api/GameRound",
                    "GET /api/GameResult/GetGameResultByGameRoundId?id=<gameRoundId>",
                ],
                "fetched_at": cekildi,
                "contains": "hafta kaydi + IKRAMIYE tablosu",
                "close_date_note": (
                    "`close_date` KUPON KAPANISIDIR, haftanin bitisi degil. "
                    "Olculdu: 2025/26'nin 41 haftasinin 41'inde bu tarih haftanin "
                    "ILK macinin gunune esit. `st_history_2025_26.json`in ayni adli "
                    "alani ise haftanin SON macina denk duser ve 1-4 gun sonradir; "
                    "iki alan celismiyor, farkli seyleri olcuyor."
                ),
                "does_not_contain": (
                    "15 maclik liste ve 1/0/2 dizisi YOK — resmi ucta mac listesi "
                    "yalnizca bulten GORSELI olarak var (bulletin_image). "
                    "Kupon dizisi icin st_history veri setine bakilir."
                ),
            },
            "weeks": haftalar,
        }
        yol = args.out_dir / f"{anahtar}.json"
        yol.write_text(json.dumps(govde, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        print(f"yazildi: {yol}")

    rapor = {
        "generated_at": cekildi,
        "source": KAYNAK_ADI,
        "seasons": {
            anahtar: {
                "season": sezonlar[anahtar][0]["season"],
                "weeks": len(sezonlar[anahtar]),
                "with_payout": sum(1 for h in sezonlar[anahtar] if h["payout"]),
                "with_bulletin_image": sum(
                    1 for h in sezonlar[anahtar] if h["bulletin_image"]),
            }
            for anahtar in sorted(sezonlar)
        },
        "totals": {
            "weeks": toplam,
            "with_payout": odemeli,
            "with_bulletin_image": gorselli,
            "with_warnings": uyarili,
        },
        "limits": [
            "Mac listesi ve 1/0/2 dizisi bu kaynakta YOK; yalnizca bulten gorseli var.",
            "Bulten gorseli 2023/2024'ten itibaren erisilebiliyor; oncesi 404.",
            "Kazanan adedi KOLON sayisidir, bilet degil (§3.40) — havuz modeli "
            "kurulurken bu ayrim tasinir.",
            "Havuzun kendisi (haftalik hasilat) ucta yok; yalnizca kademe basina "
            "kazanan adedi ve kisi basi ikramiye var.",
        ],
        "note": (
            "Deponun ilk RESMI kaynagi. §6B'nin elle girilen ikramiye blogunun "
            "yerini alir; elle girilen hafta kayitlari kendi sinifinda kalir ve "
            "bu dosya onlarla karsilastirilarak dogrulanabilir."
        ),
    }
    rapor_yol = args.out_dir / "arsiv_rapor.json"
    rapor_yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
    print(f"yazildi: {rapor_yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
