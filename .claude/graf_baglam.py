#!/usr/bin/env python3
"""Kullanıcı mesajı grafla ilgiliyse ilgili graf girdilerini bağlama enjekte eder.

`UserPromptSubmit` hook'u olarak koşar. Amaç, Claude'un "grafa bakmaya karar
vermesini" beklemek yerine cevabı karar anından önce bağlama koymaktır —
yönlendirme değil, mekanik.

**Bütçe bu dosyanın en önemli kısmıdır.** Çıktı HER mesajda bağlama girer;
kontrolsüz büyürse araç kendisi israf kaynağı olur. Üç savunma var:

1. Mesaj hiçbir tetikleyiciye uymuyorsa **hiçbir şey** basılmaz (0 token).
2. Bölümün tamamı değil, mesajla EŞLEŞEN girdiler basılır. `moduller` 51
   girdidir; tamamını basmak grafın tamamını okumakla aynı şey olurdu.
3. Sert tavan (`TAVAN_KARAKTER`). Aşılırsa kesilir ve sorgu komutu yazılır.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
GRAF = KOK / ".claude" / "bilgi_grafi.json"

TAVAN_KARAKTER = 3500          # ~1.100 token; asilirsa kesilir
AZAMI_GIRDI = 8                # bolum basina en fazla girdi

#: Bölüm -> tetikleyici kökler. Türkçe ekler değişken olduğu için tam sözcük
#: değil KÖK aranır ("modül" -> "modüller", "modülü", "modulun" hepsini yakalar).
TETIK = {
    "moduller": ("modül", "modul", "paket", "spor_toto", "ne yapıyor",
                 "ne yapar", "nerede tanımlı", "hangi dosya", "module"),
    "komutlar": ("komut", "nasıl çalıştır", "nasil calistir", "check.sh",
                 "kalite kapısı", "kalite kapisi", "command", "cli"),
    "sayilar": ("sayı", "sayi", "kaç", "kac", "nereden geliyor", "hangi belge",
                "bayat", "kütük", "kutuk", "metrik", "number", "count"),
    "kapilar": ("bekçi", "bekci", "kapı", "kapi", "iddia", "guardian",
                "test_belgeler", "hangi test", "tutuyor"),
    "boru_hatlari": ("boru hattı", "boru hatti", "pipeline", "üretir", "uretir",
                     "veri", "script", "git dışı", "git disi", "yeniden üret"),
}


#: Bölüm adı -> `graf_sorgu.py` alt komutu. Elle eşlenir; adları türetmek
#: (ek kırpma) `boru_hatlari` gibi adlarda yanlış komut üretiyordu.
_ALT_KOMUT = {"moduller": "modul", "komutlar": "komut", "kapilar": "kapi",
              "sayilar": "sayi", "boru_hatlari": "boru"}


def _oku_istem() -> str:
    """Hook'un stdin'ine gelen JSON'dan kullanıcı mesajını çıkarır.

    Alan adı sürümler arasında değişebildiği için önce bilinen adlar denenir,
    sonra JSON'daki en uzun düz metin değerine düşülür. Okunamazsa boş döner
    ve hook sessizce hiçbir şey enjekte etmez — mesajı ASLA engellemez.
    """
    try:
        veri = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return ""
    if not isinstance(veri, dict):
        return ""
    for ad in ("prompt", "user_prompt", "message", "text"):
        d = veri.get(ad)
        if isinstance(d, str) and d.strip():
            return d
    metinler = [v for v in veri.values() if isinstance(v, str) and len(v) > 20]
    return max(metinler, key=len) if metinler else ""


def _tetiklenen(istem: str) -> list[str]:
    """Mesajın hangi graf bölümlerini tetiklediğini döndürür."""
    kucuk = istem.lower()
    return [b for b, kokler in TETIK.items() if any(k in kucuk for k in kokler)]


def _kelimeler(istem: str) -> set[str]:
    """Mesajdaki anlamlı arama sözcükleri (3 harften uzun)."""
    return {k for k in re.findall(r"[\w./_]+", istem.lower()) if len(k) > 3}


def _eslesen(girdiler: list[dict], alanlar: tuple[str, ...],
             kelime: set[str]) -> list[dict]:
    """Mesajın sözcüklerinden herhangi biri girdinin metninde geçiyor mu."""
    out = []
    for g in girdiler:
        metin = " ".join(str(g.get(a, "")) for a in alanlar).lower()
        if any(k in metin for k in kelime):
            out.append(g)
    return out


def _bolum_metni(bolum: str, g: dict, kelime: set[str]) -> str:
    """Bir bölümün enjekte edilecek metnini üretir; eşleşme yoksa özet verir."""
    girdiler = g.get(bolum, [])
    if not girdiler:
        return ""
    alanlar = {
        "moduller": ("yol", "gorev"),
        "komutlar": ("komut", "ne_yapar"),
        "kapilar": ("ad", "tuttugu_iddia"),
        "sayilar": ("deger", "ne"),
        "boru_hatlari": ("yol", "yeniden_uret", "uretir"),
    }[bolum]

    sec = _eslesen(girdiler, alanlar, kelime)
    if not sec:
        # Eslesme yok: kucuk bolumun tamami verilir, buyuk bolum icin isaret.
        sec = girdiler if len(girdiler) <= AZAMI_GIRDI else []

    # TAM CEVAP VEREMIYORSAK KISMI CEVABIN PARASINI ODEME.
    # Olculdu: 51 modulun 8'ini enjekte etmek soruyu cevaplamiyor, Claude yine
    # graf_sorgu.py kosuyor ve enjeksiyon 668 token'lik SAF EK YUK oluyor
    # (668 + 2.920 > 2.920). Tek satirlik isaret ~30 token.
    if not sec or len(sec) > AZAMI_GIRDI:
        n = len(sec) if sec else len(girdiler)
        return (f"- {bolum}: {n} girdi eslesti — tek mesaja sigmaz. "
                f"Sorgu: python3 .claude/graf_sorgu.py {_ALT_KOMUT[bolum]} "
                f"<terim>\n")

    satir = [f"### {bolum} ({len(sec)}/{len(girdiler)})"]
    for e in sec[:AZAMI_GIRDI]:
        if bolum == "moduller":
            satir.append(f"- {e['yol']} — {e['gorev']}")
        elif bolum == "komutlar":
            satir.append(f"- `{e['komut']}` — {e['ne_yapar']} ({e['kaynak']})")
        elif bolum == "kapilar":
            satir.append(f"- {e['ad']} — {e['tuttugu_iddia']} ({e['kaynak']})")
        elif bolum == "sayilar":
            satir.append(f"- {e['deger']} — {e['ne']}\n  ureten: {e['ureten']}"
                         f"\n  anilir: {', '.join(e['anildigi_yerler']) or '-'}")
        else:
            satir.append(f"- {e['yol']} -> {', '.join(e['uretir'])}"
                         f" | yeniden uret: {e['yeniden_uret']}")
    return "\n".join(satir) + "\n"


def main() -> int:
    """Tetiklenen bölümleri toplayıp `additionalContext` olarak basar."""
    istem = _oku_istem()
    if not istem or not GRAF.exists():
        return 0
    bolumler = _tetiklenen(istem)
    if not bolumler:
        return 0                                   # 0 token: hicbir sey basma
    try:
        g = json.loads(GRAF.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    kelime = _kelimeler(istem)
    parcalar = [p for b in bolumler if (p := _bolum_metni(b, g, kelime))]
    if not parcalar:
        return 0

    govde = "\n".join(parcalar)
    kesildi = ""
    if len(govde) > TAVAN_KARAKTER:
        govde = govde[:TAVAN_KARAKTER]
        kesildi = ("\n[bütçe tavanı — kesildi. Tamamı için: "
                   "python3 .claude/graf_sorgu.py <bölüm> <terim>]")

    baslik = ("Bilgi grafından (`.claude/bilgi_grafi.json`) ilgili girdiler — "
              "bunlar ÖLÇÜLMÜŞ kayıtlardır, tekrar taramaya gerek yok. "
              "Graf kanıt değildir: çelişkide sıra ölçüm > kod > belge > graf.\n")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": baslik + govde + kesildi,
        },
        "suppressOutput": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
