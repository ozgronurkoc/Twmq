"""Tarihsel istatistik katmanı — türetilmiş sayıların iç tutarlılığı."""

import pytest

from spor_toto.history import (
    MATCH_COUNT,
    SYMBOLS,
    _max_run,
    _runs,
    count_distribution,
    extreme_weeks,
    history_analytics,
    history_summary,
    history_week,
    history_week_detail,
    history_weeks,
    normalized_weeks,
    position_stats,
    recent_form,
    streak_stats,
    transition_stats,
)

WEEKS = normalized_weeks()


def test_weeks_sirali_ve_tam():
    numbers = [w["week"] for w in WEEKS]
    assert numbers == sorted(numbers)
    assert numbers, "veri dosyasi bos"
    for w in WEEKS:
        assert set(w["results"]) <= set(SYMBOLS)
        assert len(w["results"]) == MATCH_COUNT
        assert w["n1"] + w["n0"] + w["n2"] == MATCH_COUNT


def test_sayimlar_results_dizisinden_turetilir():
    for w in WEEKS:
        assert w["counts"] == {s: w["results"].count(s) for s in SYMBOLS}
        assert (w["n1"], w["n0"], w["n2"]) == (w["counts"]["1"], w["counts"]["0"], w["counts"]["2"])


def test_totals_haftalarla_uyumlu():
    s = history_summary()
    weeks = history_weeks()
    for sym in SYMBOLS:
        assert s["totals"][sym] == sum(w["counts"][sym] for w in weeks)
    assert sum(s["totals"][sym] for sym in SYMBOLS) == s["meta"]["matches"]
    assert s["meta"]["weeks"] == len(weeks)
    assert round(sum(s["totals"][f"pct_{sym}"] for sym in SYMBOLS), 2) == 100.0


def test_weekly_avg_ve_bands():
    s = history_summary()
    weeks = history_weeks()
    for sym in SYMBOLS:
        vals = [w["counts"][sym] for w in weeks]
        b = s["bands"][sym]
        assert b["min"] == min(vals) and b["max"] == max(vals)
        assert b["avg"] == pytest.approx(sum(vals) / len(vals), abs=1e-4)
        assert s["weekly_avg"][sym] == pytest.approx(b["avg"], abs=1e-4)
        assert b["above_n"] + b["below_n"] == len(vals)
        assert b["above_gap"] >= 0 and b["below_gap"] >= 0


def test_last_dilimi_son_haftalari_verir():
    tam = history_weeks()
    dilim = history_weeks(5)
    assert len(dilim) == 5
    assert [w["week"] for w in dilim] == [w["week"] for w in tam[-5:]]
    s = history_summary(5)
    assert s["meta"]["weeks"] == 5
    assert s["meta"]["sliced"] is True
    assert s["meta"]["matches"] == 5 * MATCH_COUNT
    assert history_summary()["meta"]["sliced"] is False


def test_last_hafta_sayisindan_buyukse_tum_sezon():
    assert len(history_weeks(10_000)) == len(history_weeks())


def test_veri_seti_temiz():
    """Yayindaki veri seti kendi denetiminden gecmeli.

    Bu test bir regresyon bekcisidir: veri yeniden uretilirken sira ya da
    sayim bozulursa (build_history.py kaynagi yanlis okursa) burada patlar.
    """
    dq = history_summary()["data_quality"]
    assert dq["source"] == "matches"
    assert dq["weeks_total"] == dq["weeks_with_matches"] == len(WEEKS)
    assert dq["count_conflicts"] == []
    assert dq["match_conflicts"] == []
    assert dq["weeks_without_matches"] == []
    assert dq["incomplete_weeks"] == []
    assert dq["duplicate_results"] == []
    assert dq["ok"] is True


def test_data_quality_catismalari_raporlar():
    dq = history_summary()["data_quality"]
    for c in dq["count_conflicts"]:
        assert c["reported"] != c["derived"]
        assert sum(c["derived"].values()) == MATCH_COUNT
    for d in dq["duplicate_results"]:
        assert len(d["weeks"]) > 1


def test_mac_listesi_diziyi_uretir():
    for w in WEEKS:
        assert len(w["matches"]) == MATCH_COUNT
        assert [m["no"] for m in w["matches"]] == list(range(1, MATCH_COUNT + 1))
        # Kod skorun kendisinden turer; dizi de maclarin sirasindan.
        for m in w["matches"]:
            beklenen = "1" if m["hg"] > m["ag"] else "0" if m["hg"] == m["ag"] else "2"
            assert m["code"] == beklenen
            assert m["home"] and m["away"]
            assert m["kickoff"][:4].isdigit()
        assert "".join(m["code"] for m in w["matches"]) == w["results"]
        assert w["matches_match_results"] is True


def test_ayni_hafta_icinde_takim_tekrar_etmez():
    for w in WEEKS:
        takimlar = [t for m in w["matches"] for t in (m["home"], m["away"])]
        assert len(set(takimlar)) == len(takimlar), f"{w['week']}. haftada tekrar eden takim"


def test_position_stats_her_maca_tum_haftalari_dagitir():
    pos = position_stats(WEEKS)
    assert [p["pos"] for p in pos] == list(range(1, MATCH_COUNT + 1))
    for p in pos:
        assert sum(p["counts"].values()) == len(WEEKS) == p["n"]
        assert sum(p["pct"].values()) == pytest.approx(100.0, abs=0.05)
        assert p["top"] in SYMBOLS
    # sütun toplamları sezon toplamına eşit
    for sym in SYMBOLS:
        assert sum(p["counts"][sym] for p in pos) == sum(w["counts"][sym] for w in WEEKS)


def test_transition_stats_toplamlari():
    t = transition_stats(WEEKS)
    assert t["n"] == len(WEEKS) * (MATCH_COUNT - 1)
    assert sum(sum(row.values()) for row in t["counts"].values()) == t["n"]
    for a in SYMBOLS:
        if t["row_totals"][a]:
            assert sum(t["pct"][a].values()) == pytest.approx(100.0, abs=0.05)
    assert 0 <= t["repeat_pct"] <= 100


def test_count_distribution_hafta_sayisini_korur():
    dist = count_distribution(WEEKS)
    for sym in SYMBOLS:
        assert sum(b["weeks"] for b in dist[sym]) == len(WEEKS)
        # k * hafta toplamı = sezon toplamı
        assert sum(b["count"] * b["weeks"] for b in dist[sym]) == sum(
            w["counts"][sym] for w in WEEKS
        )
        assert [b["count"] for b in dist[sym]] == list(range(len(dist[sym])))


def test_runs_ve_streak():
    assert _runs("110") == [
        {"symbol": "1", "start": 1, "length": 2},
        {"symbol": "0", "start": 3, "length": 1},
    ]
    assert _runs("") == []
    assert _max_run("100011")["length"] == 3
    assert _max_run("")["length"] == 0

    st = streak_stats(WEEKS)
    for sym in SYMBOLS:
        best = st["by_symbol"][sym]
        if best["length"]:
            hafta = next(w for w in WEEKS if w["week"] == best["week"])
            assert sym * best["length"] in hafta["results"]
    assert st["top"] == sorted(st["top"], key=lambda r: (-r["length"], r["week"], r["start"]))
    assert st["avg_week_max"] >= 1


def test_extremes_ve_recent():
    ex = extreme_weeks(WEEKS)
    for sym in SYMBOLS:
        vals = [w["counts"][sym] for w in WEEKS]
        assert ex[sym]["max"]["value"] == max(vals)
        assert ex[sym]["min"]["value"] == min(vals)

    rec = recent_form(WEEKS, window=6)
    assert rec["window"] == 6
    assert rec["weeks"] == [w["week"] for w in WEEKS[-6:]]
    for sym in SYMBOLS:
        assert rec["avg"][sym] == pytest.approx(
            sum(w["counts"][sym] for w in WEEKS[-6:]) / 6, abs=1e-2
        )


def test_bos_veride_cokmez():
    assert position_stats([])[0]["n"] == 0
    assert transition_stats([])["n"] == 0
    assert count_distribution([]) == {s: [{"count": 0, "weeks": 0, "pct": 0.0}] for s in SYMBOLS}
    assert streak_stats([])["by_symbol"]["1"]["length"] == 0
    assert extreme_weeks([])["1"]["max"] is None
    assert recent_form([])["window"] == 0


def test_analytics_bloklari():
    a = history_analytics()
    assert set(a) == {"positions", "transitions", "distribution", "streaks", "extremes", "recent"}
    assert len(a["positions"]) == MATCH_COUNT
    a5 = history_analytics(5)
    assert a5["transitions"]["n"] == 5 * (MATCH_COUNT - 1)


def test_week_detail():
    hafta = WEEKS[1]["week"]
    d = history_week_detail(hafta)
    assert d is not None
    assert d["week"] == hafta
    assert d["prev_week"] == WEEKS[0]["week"]
    assert d["next_week"] == WEEKS[2]["week"]
    assert [c["symbol"] for c in d["cells"]] == list(d["results"])
    assert [c["pos"] for c in d["cells"]] == list(range(1, MATCH_COUNT + 1))
    assert "".join(r["symbol"] * r["length"] for r in d["runs"]) == d["results"]
    for sym in SYMBOLS:
        assert d["delta_vs_avg"][sym] == pytest.approx(
            d["counts"][sym] - d["season_avg"][sym], abs=1e-2
        )
        assert 1 <= d["rank"][sym]["rank"] <= d["rank"][sym]["of"] == len(WEEKS)
    assert len(d["position_stats"]) == MATCH_COUNT

    assert history_week_detail(WEEKS[0]["week"])["prev_week"] is None
    assert history_week_detail(WEEKS[-1]["week"])["next_week"] is None
    assert history_week_detail(99_999) is None
    assert history_week(99_999) is None
    assert history_week(hafta)["results"] == d["results"]


def test_rank_en_yuksek_haftayi_birinci_yapar():
    for sym in SYMBOLS:
        hi = max(WEEKS, key=lambda w: (w["counts"][sym], -w["week"]))
        assert history_week_detail(hi["week"])["rank"][sym]["rank"] == 1


# ─── sezon seçimi ─────────────────────────────────────────────────────────────
#
# §6G dört sezonluk bir kupon seti getirdi. Sezonlar **birleştirilmiyor,
# seçiliyor**: `week` bu modülde birincil anahtar gibi davranıyor (sıralama,
# `history_week_detail` araması, oranın `(week, no)` haritası) ve dört sezonu
# tek listeye koymak dördünü birden bozardı.

def test_varsayilan_sezon_DEGISMEDI():
    """En önemli çıpa: `?sezon` verilmezse bugünkü kayıt okunur.

    27 değişmez, `test_fiyatlar` ve `test_api_stats` bu sayılara bağlı.
    """
    m = history_summary()["meta"]
    assert m["weeks"] == 41
    assert m["matches"] == 615
    assert m["sezon_secimi"] is None


def test_sezon_listesi_varsayilani_ICERMEZ():
    """`sezonlar()` bir SEÇİM listesidir; varsayılan bir seçim değildir.

    `2025_26` listede olabilir ama o, varsayılanın aynı sezonu ikinci kez
    okumasıdır (31 hafta ↔ 41 hafta) — ikisi karıştırılmamalı.
    """
    from spor_toto.history import sezonlar

    liste = sezonlar()
    assert liste, "hiç sezon bulunamadı"
    assert all("_" in s for s in liste)
    varsayilan = history_summary()["meta"]
    for s in liste:
        secili = history_summary(sezon=s)["meta"]
        if s == "2025_26":
            assert secili["weeks"] != varsayilan["weeks"], (
                "aynı sezonun iki kaydı aynı hafta sayısını veriyorsa "
                "ayrım kaybolmuş demektir")


def test_secilen_sezon_kendi_haftalarini_dondurur():
    from spor_toto.history import sezonlar

    for s in sezonlar():
        weeks = history_weeks(sezon=s)
        ozet = history_summary(sezon=s)["meta"]
        assert len(weeks) == ozet["weeks"]
        assert ozet["sezon_secimi"] == s
        assert all(len(w["results"]) == MATCH_COUNT for w in weeks)


def test_bilinmeyen_sezon_bos_doner_hata_ile():
    """Sessizce varsayılana düşmez — istenmeyen sezonun sayıları gösterilmez."""
    ozet = history_summary(sezon="yok_boyle")
    assert ozet["meta"]["weeks"] == 0
    assert ozet["error"]


def test_hafta_detayi_secilen_sezonun_ICINDE_siralanir():
    """`rank` ve komşular sezon içinde kalmalı; sezonlar karışmamalı."""
    from spor_toto.history import history_week_detail, sezonlar

    s = sezonlar()[0]
    weeks = history_weeks(sezon=s)
    d = history_week_detail(weeks[0]["week"], sezon=s)
    assert d is not None
    assert d["prev_week"] is None
    assert d["rank"]["1"]["of"] == len(weeks)


def test_onbellek_sezonlar_arasi_karismaz():
    """`load_history` önbelleği sezona anahtarlı olmalı (eskiden maxsize=1)."""
    from spor_toto.history import sezonlar

    s = sezonlar()[0]
    a = history_summary()["meta"]["weeks"]
    history_summary(sezon=s)
    b = history_summary()["meta"]["weeks"]
    assert a == b == 41, "sezon seçimi varsayılanın önbelleğini düşürdü"


# ─── birleşik kesit (`?sezon=hepsi`) ─────────────────────────────────────────

def test_birlesik_kesit_ayni_sezonu_IKI_KEZ_saymaz():
    """Birleşimin tek gerçek tehlikesi budur: 2025/26'nın iki kaydı var.

    `st_history_2025_26.json` (41 hafta, üçüncü parti payload) ile
    `data/st_history/2025_26.json` (31 hafta, bültenden) **aynı sezonun iki
    okumasıdır** (§6G.5) ve ortak 31 haftanın 30'u birebir aynı dizidir.
    İkisini birden birleşime koymak o 31 haftayı iki kez saymak olurdu —
    yüzdeler kaymaz ama n şişer ve hiçbir yerde yazmaz.

    Kesit bu yüzden `evaluate.OLCUM_SEZONLARI`den türüyor: o demet aynı
    gerekçeyle `2025_26`yi zaten dışarıda bırakıyor.
    """
    from spor_toto.evaluate import OLCUM_SEZONLARI
    from spor_toto.history import birlesik_kesit

    kesit = birlesik_kesit()
    assert kesit[0] is None, "varsayilan kayit birlesimde olmali"
    assert "2025_26" not in kesit, (
        "2025/26'nin ikinci okumasi birlesime girdi: ayni haftalar iki kez sayilir")
    assert tuple(kesit[1:]) == tuple(OLCUM_SEZONLARI), (
        "kesit ikinci bir listeden kuruluyor — `OLCUM_SEZONLARI` ile ayrisabilir")


def test_birlesik_hafta_sayisi_parcalarin_TOPLAMI():
    """Birleşim ne kaybeder ne uydurur: hafta sayısı parçaların toplamıdır."""
    from spor_toto.history import (
        TUM_SEZONLAR,
        birlesik_kesit,
        history_summary,
        normalized_weeks,
    )

    parcalar = {s: len(normalized_weeks(sezon=s)) for s in birlesik_kesit()}
    birlesik = normalized_weeks(sezon=TUM_SEZONLAR)
    assert len(birlesik) == sum(parcalar.values())
    meta = history_summary(sezon=TUM_SEZONLAR)["meta"]
    assert meta["weeks"] == len(birlesik)
    assert meta["matches"] == len(birlesik) * MATCH_COUNT
    # Künye de aynı toplamı vermeli — arayüz bu dökümü basıyor.
    assert sum(d["weeks"] for d in meta["birlesim"]) == meta["weeks"]
    assert sum(d["matches"] for d in meta["birlesim"]) == meta["matches"]


def test_birlesik_hafta_anahtarlari_BENZERSIZ():
    """Hafta NUMARASI kimlik değil; anahtar kimliktir.

    Dört kaydın dördünde de 12. hafta var. Arayüzün bağlantıları, oranın
    haftalık Brier'i ve kopya denetimi anahtara bakar; anahtar benzersiz
    olmazsa üçü birden sessizce yanlış satıra bağlanır.
    """
    from spor_toto.history import TUM_SEZONLAR, normalized_weeks

    weeks = normalized_weeks(sezon=TUM_SEZONLAR)
    anahtarlar = [w["anahtar"] for w in weeks]
    assert len(set(anahtarlar)) == len(anahtarlar)
    # Numaralar ise TEKRAR EDER — testin dayandığı gerçek bu.
    assert len({w["week"] for w in weeks}) < len(weeks)
    for w in weeks:
        assert w["anahtar"] == f"{w['sezon'] or 'varsayilan'}-{w['week']}"


def test_birlesik_kesit_KRONOLOJIK_sirali():
    """Sıra hafta numarasından değil tarihten gelir.

    Numaraya göre sıralamak dört kaydı iç içe geçirirdi (dördünde de 2.
    hafta var) ve "son 12 hafta" dilimi dört sezondan derlenmiş rastgele
    bir kümeye dönerdi.
    """
    from spor_toto.history import TUM_SEZONLAR, normalized_weeks

    tarihler = [w["close_date"] for w in normalized_weeks(sezon=TUM_SEZONLAR)]
    assert tarihler == sorted(tarihler)


def test_birlesik_dilim_kesitin_SONUNDAN_alinir():
    """`?last=N` birleşimde de "en son N hafta"dır — sezon başına değil."""
    from spor_toto.history import TUM_SEZONLAR, normalized_weeks

    tam = normalized_weeks(sezon=TUM_SEZONLAR)
    dilim = normalized_weeks(6, sezon=TUM_SEZONLAR)
    assert len(dilim) == 6
    assert [w["anahtar"] for w in dilim] == [w["anahtar"] for w in tam[-6:]]


def test_birlesik_meta_hafta_ARALIGI_yazmaz():
    """"2–51. haftalar" birleşimde yanlıştır; künye onu hiç yazmaz.

    `week_from`/`week_to` `None` gelir ve bu bir boşluk değil bir cevaptır:
    arayüz o rozeti basmaz, yerine sezon dökümünü gösterir.
    """
    from spor_toto.history import TUM_SEZONLAR, history_summary

    meta = history_summary(sezon=TUM_SEZONLAR)["meta"]
    assert meta["week_from"] is None and meta["week_to"] is None
    assert meta["origin"] == "birlesik kesit"
    assert meta["sezon_secimi"] == TUM_SEZONLAR
    # Tek kayıtta aralık yerinde durmalı — bu test onu da tutar.
    tek = history_summary()["meta"]
    assert tek["week_from"] == 2 and tek["week_to"] == 51


def test_birlesik_kesitte_TEK_HAFTA_sorgusu_reddedilir():
    """"12. hafta" birleşimde dört kaydın dördünde de var: seçmeyiz.

    Doktrin 4: belirsiz veri sessizce bir tarafa yazılmaz. Uç bunu 400 ile
    bildirir, motor `ValueError` ile.
    """
    from spor_toto.history import TUM_SEZONLAR, history_week, history_week_detail

    with pytest.raises(ValueError):
        history_week(12, sezon=TUM_SEZONLAR)
    with pytest.raises(ValueError):
        history_week_detail(12, sezon=TUM_SEZONLAR)


def test_kopya_dizi_denetimi_SEZONA_gore_yapilir():
    """Aynı dizi iki FARKLI sezonda kusur değildir; aynı sezonda kusurdur.

    §7.4'ün v1 vakası bir sezonun kendi içinde tekrar eden dizilerdi ve
    denetim onu yakalamak için var. Sezonsuz gruplama birleşik kesitte
    "2022/23 hf 21 ile 2024/25 hf 30 aynı" gibi anlamsız bir çakışma
    raporlardı — iki bağımsız kuponun aynı diziyi vermesi olağandır.

    Gerçek veride bugün hiç çakışma yok (ölçüldü), yani bu kural ancak
    sentetik satırla sınanabilir.
    """
    from spor_toto.history import _data_quality

    def satir(sezon, week, results):
        return {
            "week": week, "sezon": sezon,
            "anahtar": f"{sezon or 'varsayilan'}-{week}",
            "close_date": "2024-01-01", "results": results,
            "counts": {s: results.count(s) for s in SYMBOLS},
            "consistent": True, "complete": len(results) == MATCH_COUNT,
            "reported_counts": None, "matches": [], "matches_match_results": False,
        }

    dizi = "1" * MATCH_COUNT
    farkli_sezon = _data_quality([satir("2022_23", 3, dizi), satir("2023_24", 9, dizi)])
    assert farkli_sezon["duplicate_results"] == [], (
        "iki ayri sezonun ayni dizisi kopya sayildi")

    ayni_sezon = _data_quality([satir("2022_23", 3, dizi), satir("2022_23", 9, dizi)])
    assert [d["weeks"] for d in ayni_sezon["duplicate_results"]] == [[3, 9]]
    assert ayni_sezon["duplicate_results"][0]["sezon"] == "2022_23"


def test_kusur_listeleri_haftayi_SEZONUYLA_anar():
    """Kusur raporu birleşik kesitte belirsiz olamaz.

    Listeler düz hafta numarasıydı; "12. hafta eksik" cümlesi birleşimde
    dört kaydın dördünü birden gösterebilirdi.
    """
    from spor_toto.history import _data_quality

    eksik = {
        "week": 7, "sezon": "2023_24", "anahtar": "2023_24-7",
        "close_date": "2024-01-01", "results": "1" * (MATCH_COUNT - 1),
        "counts": {"1": MATCH_COUNT - 1, "0": 0, "2": 0},
        "consistent": True, "complete": False, "reported_counts": None,
        "matches": [], "matches_match_results": False,
    }
    dq = _data_quality([eksik])
    assert dq["incomplete_weeks"] == [
        {"week": 7, "sezon": "2023_24", "anahtar": "2023_24-7"}]
    assert dq["weeks_without_matches"] == [
        {"week": 7, "sezon": "2023_24", "anahtar": "2023_24-7"}]


def test_kayit_secenekleri_AYNI_etiketi_kokenle_ayirir():
    """2025/26'nın iki kaydı seçicide ayırt edilebilmeli.

    Kullanıcının ilk sorduğu soru buydu: biri 41 hafta diyor, öteki 31 —
    hangisi hangisi? Ayıran şey sezon anahtarı değil **köken**: anahtarı
    ("2025_26") buraya yazmak, aynı çakışma üçüncü bir sezonda çıktığında
    sessizce yanlış olurdu.
    """
    from spor_toto.history import TUM_SEZONLAR, kayit_secenekleri

    kayitlar = kayit_secenekleri()
    assert kayitlar[0]["deger"] == TUM_SEZONLAR, "ilk secenek birlesik kesit olmali"
    etiketler = [k["etiket"] for k in kayitlar]
    assert len(set(etiketler)) == len(etiketler), f"etiket cakismasi: {etiketler}"

    ikili = [k for k in kayitlar if k["etiket"].startswith("2025/26")]
    assert len(ikili) == 2, "2025/26'nin iki kaydi da secilebilir olmali"
    assert {k["weeks"] for k in ikili} == {31, 41}
    # Birleşime yalnızca biri girer ve hangisi olduğu seçicide okunur.
    assert [k["birlesimde"] for k in sorted(ikili, key=lambda k: k["weeks"])] == [False, True]
