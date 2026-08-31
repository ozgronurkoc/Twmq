#!/usr/bin/env python3
"""Bilgi grafını bölüm bölüm sorgular — tamamını belleğe almadan.

Grafın tamamı ~8.000 token; bu araç yalnızca eşleşen girdileri basar, yani
soruyu cevaplamak için bağlama giren miktar soruyla orantılı kalır.
"""
import json
import pathlib
import subprocess
import sys

GRAF = pathlib.Path(".claude/bilgi_grafi.json")


def yukle() -> dict:
    """Grafı okur; yoksa nasıl üretileceğini söyleyip çıkar."""
    if not GRAF.exists():
        sys.exit("graf yok — üretmek için: .claude/skills/knowledge-graph/"
                 "references/sorgular.md")
    return json.loads(GRAF.read_text(encoding="utf-8"))


def ozet(g: dict) -> None:
    """Bölüm bölüm girdi sayısı ve grafın yazıldığı an."""
    print(f"yazildi: {g['yazildi']}  ·  head: {g['git']['head'][:8]}"
          f"  ·  dal: {g['git']['dal']}")
    for ad in ("moduller", "komutlar", "kapilar", "sayilar", "boru_hatlari"):
        print(f"  {ad:>13}: {len(g[ad])}")


def modul(g: dict, ara: str) -> None:
    """Yol veya görev metninde geçen modülleri basar."""
    for m in g["moduller"]:
        if ara in m["yol"].lower() or ara in m["gorev"].lower():
            print(f"{m['yol']}\n    {m['gorev']}\n    kaynak: {m['kaynak']}")


#: Elle biriken bölümler. Graf `.gitignore`'da (satır 99) ve tazeleyici
#: bunları ÜRETEMEZ — kaynakları komut koşmak / belge okumaktır. Yani taze
#: bir klonda (her uzak oturum) ikisi de boş gelir.
ELLE_BIRIKEN = {
    "sayilar": ("sayı kütüğü", ".claude/skills/knowledge-graph/SKILL.md"),
    "komutlar": ("komut envanteri", ".claude/skills/knowledge-graph/SKILL.md"),
}


def _bos_mu(g: dict, bolum: str) -> bool:
    """Bölüm boşsa bunu AÇIKÇA söyler ve True döner.

    **Neden var.** Bu iki fonksiyon boş bölümde döngüye hiç girmiyordu, yani
    hiçbir şey basmıyordu — ve "kütük bu klonda yok" ile "böyle bir sayı
    kayıtlı değil" çıktı olarak AYNI görünüyordu. `CLAUDE.md` "sayı sorulunca
    taramadan önce kütüğe bak" diyor; kütük boşken o kural sessizce hiçbir şey
    yapmıyordu. Sessizlik bir cevap değildir: boşluk ADIYLA söylenir.
    """
    if g.get(bolum):
        return False
    ad, kaynak = ELLE_BIRIKEN[bolum]
    print(f"{ad} BOŞ — bu klonda hiç girdi yok (graf git dışı, elle birikir).")
    print("  Bu, 'böyle bir kayıt yok' DEĞİLDİR: kütüğün kendisi gelmemiştir.")
    print("  Sonuç: aranan şey ÖLÇÜLMEDEN kullanılamaz — komutu koş, sonra")
    print(f"  kütüğe yaz. Kural: {kaynak}")
    return True


def sayi(g: dict, ara: str) -> None:
    """Değerde veya açıklamada geçen sayı kütüğü girdilerini basar."""
    if _bos_mu(g, "sayilar"):
        return
    for s in g["sayilar"]:
        if ara in s["deger"] or ara in s["ne"].lower():
            print(f"{s['deger']} — {s['ne']}")
            print(f"    ureten : {s['ureten']}")
            print(f"    olculdu: {s['olculdu']}")
            for y in s["anildigi_yerler"]:
                print(f"    anilir : {y}")


def komut(g: dict, ara: str) -> None:
    """Komut metninde veya açıklamasında geçen komutları basar."""
    if _bos_mu(g, "komutlar"):
        return
    for k in g["komutlar"]:
        if ara in k["komut"].lower() or ara in k["ne_yapar"].lower():
            print(f"{k['komut']}\n    {k['ne_yapar']}\n    kaynak: {k['kaynak']}")


def kapi(g: dict, ara: str) -> None:
    """Adında veya tuttuğu iddiada geçen bekçileri basar."""
    for k in g["kapilar"]:
        if ara in k["ad"].lower() or ara in k["tuttugu_iddia"].lower():
            print(f"{k['ad']}\n    {k['tuttugu_iddia']}\n    kaynak: {k['kaynak']}")


def boru(g: dict, ara: str) -> None:
    """Yolunda veya ürettiği dosyalarda geçen boru hatlarını basar."""
    for b in g["boru_hatlari"]:
        if ara in b["yol"].lower() or any(ara in u.lower() for u in b["uretir"]):
            print(f"{b['yol']}  ->  {', '.join(b['uretir'])}")
            print(f"    yeniden uret: {b['yeniden_uret']}   ({b['kaynak']})")


def tazelik(g: dict) -> None:
    """Kayıtlı hash hâlâ tutuyor mu — bayatlığı görünür kılan tek denetim."""
    bayat = []
    for bolum in ("moduller", "kapilar", "boru_hatlari"):
        for gd in g[bolum]:
            p = pathlib.Path(gd["yol"])
            if not p.exists():
                bayat.append((bolum, gd["yol"], "DOSYA YOK"))
                continue
            h = subprocess.run(["git", "hash-object", gd["yol"]],
                               capture_output=True, text=True).stdout.strip()
            if h != gd.get("hash"):
                bayat.append((bolum, gd["yol"], "DEGISTI"))
    simdi = subprocess.run(["git", "rev-parse", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
    print(f"HEAD kaydi: {g['git']['head'][:8]}  ·  simdi: {simdi[:8]}")
    print(f"bayat girdi: {len(bayat)}")
    for b in bayat:
        print("  ", *b)
    if bayat:
        print("\nBayat girdi SILINIR ya da YENIDEN OLCULUR, duzeltilmis sayilmaz.")


def main() -> None:
    """Alt komutu seçip çalıştırır."""
    if len(sys.argv) < 2:
        sys.exit(__doc__ + "\nkullanim: graf_sorgu.py "
                 "{ozet|modul|komut|sayi|kapi|boru|tazelik} [arama]")
    g = yukle()
    islem, arg = sys.argv[1], (sys.argv[2].lower() if len(sys.argv) > 2 else "")
    if islem == "ozet":
        ozet(g)
    elif islem == "tazelik":
        tazelik(g)
    elif islem in ("modul", "sayi", "kapi", "boru", "komut"):
        # Arama terimi bos ise bolumun TAMAMI listelenir: "" her metinde
        # gecer, yani filtre kendiliginden acilir.
        {"modul": modul, "sayi": sayi, "kapi": kapi,
         "boru": boru, "komut": komut}[islem](g, arg)
    else:
        sys.exit(f"bilinmeyen islem: {islem}")


if __name__ == "__main__":
    main()
