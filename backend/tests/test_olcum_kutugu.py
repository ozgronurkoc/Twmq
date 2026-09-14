"""Ölçüm kütüğünün kendisinin bekçileri (`.claude/olcum_kutugu.json`).

**Neden var.** Kütük deponun "hangi sayı hangi komuttan çıktı, hangi belgede
anılıyor" defteri ve `CLAUDE.md` onu bir kanıt zinciri olarak kullanıyor:
*"bir sayı nereden geliyor, bayat mı"* sorusunun cevabı orada. Ama defterin
kendisinin hiçbir bekçisi yoktu ve üç ayrı yoldan sessizce çürüyebiliyordu:

1. **Alıntı çürümesi.** Kütük "bu sayı README §1.1'de anılıyor" der, belge
   değişir, kütük eskir. `.claude/graf_uret.py::sayilar_denetle` bunu zaten
   ölçüyordu — ama yalnızca **bildiriyordu**: oturum açılışında bir uyarı
   satırı, kalite kapısında hiçbir şey. Uyarı okunmazsa yoktur.
2. **Üreten çürümesi.** Kütükteki `ureten` komutu silinmiş bir modülü
   çağırır hâle gelir. Ölçüldüğünde bir örnek vardı: kaplama sökülünce
   `spor_toto.sistem` gitti ve onu çağıran kayıt kütükte kaldı.
3. **Bekçisizlik.** Bir sayı hiçbir testin tutmadığı hâlde kütükte "ölçülmüş"
   diye durur. 2026-09-07'de ölçüldü: **140 sayının 38'i** böyleydi ve bu,
   `graf_sorgu.py` `bekci` alanını basmaya başlayana kadar görünmüyordu.

Buradaki testler o üç yolu da kapatır. Ölçümü **yeniden koşmazlar** — o
komutlar dakikalar sürer ve kapının işi değildir; tuttukları şey defterin
kendi iç tutarlılığıdır.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
DEPO = KOK.parent
KUTUK = DEPO / ".claude" / "olcum_kutugu.json"

#: Bir girdinin taşımak zorunda olduğu alanlar.
ZORUNLU = ("ne", "deger", "ureten", "olculdu", "anildigi_yerler")

#: `komutlar` bölümünün zorunlu alanları. Ayrı bir tuple, çünkü bölüm ayrı
#: bir şey ölçüyor: bir sayının künyesi değil bir **komutun ne yaptığı**.
#:
#: BU LISTE BIR COKMEDEN SONRA YAZILDI. Şema kapısı yalnızca `sayilar`a
#: bakıyordu; `komutlar`a `ne_yapar` yerine `ne` alanıyla bir girdi
#: eklenince kapı yeşil kaldı ve kusur `graf_sorgu.py komut <terim>`
#: çağrısında `KeyError: 'ne_yapar'` ile **çökerek** ortaya çıktı. Yani
#: defterin bir bölümü bekçisizdi ve tek belirtisi bir aracın patlamasıydı.
ZORUNLU_KOMUT = ("komut", "ne_yapar", "kaynak")


def _kutuk() -> dict:
    if not KUTUK.exists():
        pytest.skip("olcum_kutugu.json yok (git disi klon)")
    return json.loads(KUTUK.read_text(encoding="utf-8"))


def _graf_uret():
    """`.claude/graf_uret.py`yi modül olarak yükler.

    Testin kendi kopyasını yazmak yerine üreteciyi çağırmak şart: iki
    denetim mantığı sessizce ayrışırsa bekçi, denetçinin görmediğini
    tutmaya başlar ve ikisi de doğru sanılır.
    """
    yol = DEPO / ".claude" / "graf_uret.py"
    if not yol.exists():
        pytest.skip(".claude/graf_uret.py yok")
    spec = importlib.util.spec_from_file_location("_graf_uret", yol)
    modul = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modul)
    return modul


def test_kutukteki_her_sayi_anildigi_yerde_GERCEKTEN_geciyor():
    """`anildigi_yerler` bir iddiadır ve doğrulanabilir.

    Bu, `graf_uret.sayilar_denetle`nin **kapıya bağlanmış** hâli. O fonksiyon
    bulguyu yazmaz, bildirir — çünkü yeniden ölçmek komut koşmayı gerektirir
    ve bu insanın kararıdır. Ama *bildirmek* bir kapı değildir: uyarı
    oturum açılışında akıp gider. Test onu kırmızıya çevirir.

    Düşerse yapılacak şey sayıyı belgeye geri yapıştırmak DEĞİLDİR: ya ölçüm
    değişmiştir (komutu koş, kütüğü güncelle) ya da belge yeniden yazılmıştır
    (`anildigi_yerler`i düzelt). İkisi de elle karardır.
    """
    gu = _graf_uret()
    supheli = gu.sayilar_denetle(_kutuk())
    assert not supheli, (
        "kutukteki sayilar anildiklari yerde bulunamadi:\n" +
        "\n".join(f"  {d} -> {y} ({sebep})" for d, y, sebep in supheli))


def test_kutukteki_ureten_komutlarinin_modulleri_VAR():
    """`ureten` çalıştırılabilir olmalı — en azından modülleri durmalı.

    Komutun tamamını koşmak pahalı (bazıları 20 dakika), ama içinde geçen
    `spor_toto.<modul>` adlarını doğrulamak bedavadır ve gerçek bir çürümeyi
    yakalar: kaplama sökülünce `spor_toto.sistem` silindi ve onu çağıran
    kayıt kütükte kaldı, yani "bu sayıyı şu komutla yeniden üret" diyen
    künye artık üretmiyordu.
    """
    sys.path.insert(0, str(KOK))
    try:
        eksik: list[str] = []
        for s in _kutuk().get("sayilar", []):
            adlar = set(re.findall(r"spor_toto\.([a-z_][a-z_0-9]*)", s["ureten"]))
            adlar |= set(re.findall(r"from spor_toto import ([a-z_][a-z_0-9]*)",
                                    s["ureten"]))
            for ad in sorted(adlar):
                if ad in {"py", "json"}:
                    continue
                if importlib.util.find_spec(f"spor_toto.{ad}") is None:
                    eksik.append(f"  {s['deger']!r}: spor_toto.{ad} YOK  ({s['ne'][:50]})")
        assert not eksik, "kutukteki ureten komutlari olmayan modul cagiriyor:\n" + "\n".join(eksik)
    finally:
        sys.path.remove(str(KOK))


def test_kutukteki_her_sayinin_BEKCISI_ya_da_GEREKCESI_var():
    """Her sayı ya bir testin tuttuğu ya da niçin tutulmadığı yazılan olmalı.

    **Bu bekçi bir denetimin sonucudur.** `graf_sorgu.py` `bekci` alanını
    basmaya başladığında görünen ilk şey 140 sayının **38'inin** bekçisiz
    olduğuydu — ve bekçisizlik sessizdi, çünkü sorgu o alanı hiç
    göstermiyordu.

    Boş bırakmak yerine `bekcisiz_gerekce` yazmak zorunlu: bir sayının
    tutulmaması meşru olabilir (hiçbir belgede anılmıyorsa güdülecek iddia
    yoktur) ama bu bir **karar** olmalı, unutmanın sonucu değil. Doktrin
    aynı: belirsiz veri atılır ya da işaretlenir, uydurulmaz.
    """
    bos = [f"  {s['deger']!r} — {s['ne'][:60]}"
           for s in _kutuk().get("sayilar", [])
           if not s.get("bekci") and not s.get("bekcisiz_gerekce")]
    assert not bos, (
        f"{len(bos)} sayinin ne bekcisi ne de bekcisizlik gerekcesi var:\n"
        + "\n".join(bos))


def test_kutuk_girdilerinin_semasi_TAM():
    """Künye eksik bir ölçüm, ölçülmemişten daha kötüdür: doğrulanamaz."""
    hata: list[str] = []
    for s in _kutuk().get("sayilar", []):
        for alan in ZORUNLU:
            if alan not in s:
                hata.append(f"  {s.get('deger', '?')!r}: '{alan}' alani yok")
        if not str(s.get("olculdu", "")).strip():
            hata.append(f"  {s.get('deger', '?')!r}: 'olculdu' bos")
    assert not hata, "kutuk semasi bozuk:\n" + "\n".join(hata)


def test_kutuk_KOMUT_girdilerinin_semasi_TAM():
    """`komutlar` bölümü de şemaya uymalı — bu kapı bir çökmeden sonra var.

    Üstteki test yalnızca `sayilar`a bakıyordu. `komutlar`a alan adı yanlış
    (`ne`, `ne_yapar` değil) bir girdi girince kapı yeşil kaldı ve kusur
    `python3 .claude/graf_sorgu.py komut <terim>` çağrısında `KeyError` ile
    çıktı. Bir aracın patlaması bir bekçi değildir: yalnızca o yolu
    yürüyen görür, ve bu depoda o yolu grafa güvenerek başlayan her oturum
    yürüyor.

    Alanların **boş olmaması** da sınanıyor: `graf_sorgu.komut` üçünü de
    basıyor, yani boş bir alan sorguyu sessizce yarım bırakırdı.
    """
    hata: list[str] = []
    for k in _kutuk().get("komutlar", []):
        ad = k.get("komut", "?")
        for alan in ZORUNLU_KOMUT:
            if alan not in k:
                hata.append(f"  {ad!r}: '{alan}' alani yok")
            elif not str(k[alan]).strip():
                hata.append(f"  {ad!r}: '{alan}' bos")
        fazla = set(k) - set(ZORUNLU_KOMUT)
        if fazla:
            hata.append(f"  {ad!r}: taninmayan alan {sorted(fazla)}")
    assert not hata, "kutuk komut semasi bozuk:\n" + "\n".join(hata)


def test_bekci_alani_GERCEK_bir_teste_isaret_ediyor():
    """`bekci` bir dosya::test yolu olmalı ve o dosya durmalı.

    Var olmayan bir teste işaret eden künye, bekçisizlikten daha zararlıdır:
    sorgu "bekcisi var" der ve okuyan iddiayı tutulmuş sanır.
    """
    hata: list[str] = []
    for s in _kutuk().get("sayilar", []):
        bekci = s.get("bekci")
        if not bekci:
            continue
        for parca in re.split(r"\s*(?:\|\||,)\s*", bekci):
            dosya = parca.split("::")[0].strip()
            if not dosya.endswith(".py"):
                continue
            if not (DEPO / dosya).exists():
                hata.append(f"  {s['deger']!r}: bekci dosyasi yok -> {dosya}")
    assert not hata, "bekci alani olmayan dosyayi gosteriyor:\n" + "\n".join(hata)


def test_kutuk_KANONIK_bicimde_yazilmis():
    """Kütük, kendi yazıcısının ürettiği baytların aynısı olmalı.

    **Bu bekçi bir gürültüden sonra yazıldı.** Kütüğe elle girdi eklerken
    `json.dumps(..., indent=2)` kullanıldı; oysa deponun kendi yazıcısı
    (`.claude/graf_uret.py::kutuk_yaz`) `indent=1` yazıyor. Sonuç: bir
    sonraki oturum açılışında kanca dosyayı kanonik biçime geri çevirdi ve
    **5.116 satırlık** bir boşluk farkı, hiç ilgisi olmayan bir işlemeye
    düştü. Ne veri bozuldu ne bir sayı değişti — ama o işlemenin gerçek
    değişikliği (dört satır) 2.500 satırlık gürültünün içinde kayboldu.

    Kütük elle de düzenlenebilir, düzenlenmeli de; bu test biçimi
    dayatmıyor, yalnızca **yazıcının kendi biçimini** dayatıyor. Düşerse
    yapılacak şey tek satır:

        python3 -c "import importlib.util as u, json, pathlib; \
        s=u.spec_from_file_location('g','.claude/graf_uret.py'); \
        m=u.module_from_spec(s); s.loader.exec_module(m); \
        m.kutuk_yaz(json.loads(pathlib.Path('.claude/olcum_kutugu.json').read_text()))"
    """
    yol = DEPO / ".claude" / "graf_uret.py"
    if not KUTUK.exists() or not yol.exists():
        pytest.skip("kutuk ya da uretici yok")
    gu = _graf_uret()
    beklenen = json.dumps(
        {"sayilar": _kutuk().get("sayilar", []),
         "komutlar": _kutuk().get("komutlar", [])},
        ensure_ascii=False, indent=1) + "\n"
    assert KUTUK.read_text(encoding="utf-8") == beklenen, (
        "kutuk kendi yazicisinin bicimine uymuyor — bir sonraki oturum acilisi "
        "onu yeniden yazacak ve fark ilgisiz bir islemeye dusecek. "
        f"(yazici: {gu.kutuk_yaz.__module__}.kutuk_yaz, indent=1)")
