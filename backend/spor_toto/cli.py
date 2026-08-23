"""Komut satiri arayuzu."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from . import __version__
from .bayes import (
    STRENGTH_PRESETS,
    bayes_summary,
    bayes_update_matches,
    recommend_strengths,
)
from .core import (
    HAS_SCIPY,
    ORNEK_KUPON,
    Encoder,
    Fix16Hatasi,
    dogrula_kaplama,
    merge_rows,
    parse_picks,
    parse_probs,
    solve_by_blocks,
    solve_fix16,
)
from .engines import ButceSigmazHatasi, adaylar, en_iyi_aday, engine_params, run_butce, run_maxcov
from .report import CIZGI, INCE, basliklar, yazdir_ve_kaydet

#: Tek kaynak `core.ORNEK_KUPON`; ad burada korunuyor.
ORNEK = ORNEK_KUPON
BAYES_PRESET_CHOICES = tuple(STRENGTH_PRESETS.keys())


def _log(msg: str) -> None:
    print(f"   {msg}")


def _mc_kwargs(args) -> dict:
    """yazdir_ve_kaydet'e gecen istege bagli analiz ayarlari."""
    return {
        "mc_samples": getattr(args, "mc_samples", 0) or 0,
        "mc_seed": getattr(args, "seed", 42),
        # Fire analizi varsayilan olarak KAPALI (--mc-samples deseni):
        # gercekci kuponlarda pahali olabilir, kullanici acikca istemeli.
        "fire_max": (getattr(args, "fire_max", 2) if getattr(args, "fire", False) else 0),
    }


def _apply_bayes(enc: Encoder, args) -> None:
    """--bayes / --bayes-preset varsa evidence → Dirichlet posterior."""
    args.bayes_info = None
    use_bayes = bool(args.bayes or args.bayes_preset)
    if not use_bayes:
        return
    if args.parsed_probs is None:
        raise ValueError(
            "--bayes / --bayes-preset icin --probs zorunlu "
            "(evidence olmadan posterior uretilemez)"
        )

    if args.bayes_preset:
        preset = recommend_strengths(args.bayes_preset)
        prior_s = (
            float(args.prior_strength)
            if args.prior_strength is not None
            else float(preset["prior_strength"])
        )
        evid_s = (
            float(args.evidence_strength)
            if args.evidence_strength is not None
            else float(preset["evidence_strength"])
        )
        preset_name = args.bayes_preset
    else:
        prior_s = float(args.prior_strength) if args.prior_strength is not None else 1.0
        evid_s = (
            float(args.evidence_strength) if args.evidence_strength is not None else 10.0
        )
        preset_name = "manuel"

    updates = bayes_update_matches(
        enc.selections,
        args.parsed_probs,
        prior_strength=prior_s,
        evidence_strength=evid_s,
    )
    args.parsed_probs = [u["posterior"] for u in updates]  # type: ignore[misc]
    summary = bayes_summary(updates)
    args.bayes_info = [
        f"Bayes           : Dirichlet posterior (preset={preset_name})",
        "  Kaynak        : bayes_posterior",
        f"  Prior α       : {prior_s}  ·  Evidence n : {evid_s}",
        f"  Ort. KL       : {summary['mean_kl_prior_post']}  "
        f"({summary.get('mean_kl_label', '')})",
        "  NOT            : 14-garanti kombinatoryal; Bayes sadece olasilik "
        "agirliklarini gunceller.",
    ]
    top = summary.get("top_shifts") or []
    if top:
        args.bayes_info.append("  En buyuk KL kaymalari:")
        for item in top[:5]:
            mac = item.get("mac", "?")
            kl = item.get("kl", 0.0)
            lab = item.get("kl_label", "")
            args.bayes_info.append(f"    M{mac}: KL={kl:.4f}  ({lab})")


def _mod_fix16(enc: Encoder, args) -> None:
    cols, aciklama = solve_fix16(enc, variant=args.variant)
    _log(f"Sabit 16 satir: {aciklama} -> {len(cols)} kolon bedeli")
    notlar = [aciklama]
    if args.variant:
        notlar.append(f"Varyant {args.variant} (koset kaydirma + permutasyon)")

    if HAS_SCIPY and not args.no_compare:
        r = solve_by_blocks(enc, max_block_space=args.block_limit,
                            time_limit=min(args.time_limit, 10.0),
                            total_time_limit=args.compare_budget)
        if r and len(r[0]) < len(cols):
            notlar.append(
                f"NOT: --mode auto {len(r[0])} kolona iniyor "
                f"({len(cols) - len(r[0])} kolon daha ucuz), ama "
                f"{len(merge_rows(r[0]))} satir olurdu.")
        elif r:
            notlar.append("Genel motor daha iyisini bulamadi -> bu mod optimal.")

    yazdir_ve_kaydet(enc, cols, "Sabit 16 satir (Hamming(7,4) + ekstra tam sistem)",
                     args.output, notlar, probs=args.parsed_probs,
                     tam_liste=not args.kisa, **_mc_kwargs(args))


def _mod_butce(enc: Encoder, args) -> None:
    if args.budget is None:
        raise ValueError("--mode butce icin --budget gerekir.")
    print(f"BUTCE DANISMANI: en fazla {args.budget} kolon\n")

    try:
        mevcut, _ = solve_fix16(enc)
        print(f"Mevcut kuponun bedeli: {len(mevcut)} kolon")
        if len(mevcut) <= args.budget:
            print("Butcen zaten yetiyor, kismaya gerek yok.\n")
            _mod_fix16(enc, args)
            return
    except Fix16Hatasi:
        print("Mevcut kupon sabit 16 satir modu icin uygun degil "
              "(7 cifteden az).")

    # Plan uretimi, secim, yeniden kodlama ve cozum `engines.run_butce`ta.
    # Buradaki kopya ayni diziyi yuruyordu; CLI yalnizca SUNUM katmanidir.
    try:
        r = run_butce(enc, args.budget, args.parsed_probs,
                      plan_count=args.plan, plan_apply=args.plan_uygula,
                      variant=args.variant)
    except ButceSigmazHatasi:
        print(f"\n{args.budget} kolonluk butceye sigan bir plan bulunamadi.")
        print("Daha fazla maci bankoya cevirmen ya da butceyi artirman gerekiyor.")
        return

    planlar, idx = r["planlar"], r["secili_index"]
    print(f"\n{len(planlar)} plan bulundu (en az feda edenden siraliyla):\n")
    for i, pl in enumerate(planlar, 1):
        ek = f"  kume-ici olasilik %{100 * pl.p_kume_ici:.2f}" if pl.p_kume_ici else ""
        print(f"Plan {i}: {pl.bedel} kolon / {pl.satir} satir{ek}")
        for d in pl.degisiklikler:
            print(f"   - {d}")
        if not pl.degisiklikler:
            print("   - (degisiklik yok)")
        print()

    secili = planlar[idx]
    print(INCE)
    print(f"Plan {idx + 1} uygulaniyor (--plan-uygula ile degistirebilirsin).")
    print(INCE)
    _, aciklama = solve_fix16(r["enc"], variant=args.variant)
    yazdir_ve_kaydet(r["enc"], r["cols"],
                     f"Butce plani ({secili.bedel} kolon) - {aciklama}",
                     args.output,
                     [f"Uygulanan degisiklikler: {'; '.join(secili.degisiklikler) or 'yok'}"],
                     probs=args.parsed_probs, tam_liste=not args.kisa,
                     **_mc_kwargs(args))


def _mod_maxcov(enc: Encoder, args) -> None:
    if args.budget is None:
        raise ValueError("--mode maxcov icin --budget gerekir.")
    print(f"MAKSIMUM KAPSAMA MODU: {args.budget} kolon\n")
    tavan = min(enc.space_size(), args.budget * enc.ball_size())
    if args.budget < enc.lower_bound():
        print(f"   Teorik tavan: {args.budget} x {enc.ball_size()} = {tavan} nokta "
              f"= %{100 * tavan / enc.space_size():.1f}")
        print("   14-GARANTI IMKANSIZ (sayma argumani). Kapsama maksimize edilecek.\n")

    # Algoritma `engines.run_maxcov`ta (kesin cozucu -> acgozlu duse ->
    # kapsama yeniden sayimi). Buradaki kopya ayni isi yapiyordu ama farkli
    # varsayilanlarla. CLI yalnizca SUNUM katmanidir: notlar ASCII kalir
    # cunku terminal ciktisinin tamami boyle (bkz. report.py).
    r = run_maxcov(enc, args.budget, time_limit=args.time_limit, seed=args.seed)
    cols, kapsanan, kanit = r["cols"], r["kapsanan"], r["kanit"]
    if not kanit:
        print("   Kesin cozucu kanit uretmedi (zaman siniri ya da scipy yok).")

    notlar = [
        f"Kapsanan nokta: {kapsanan}/{enc.space_size()} "
        f"(%{100 * kapsanan / enc.space_size():.2f})",
        f"Optimallik: {'KANITLANDI' if kanit else 'kanitlanmadi (zaman siniri)'}",
        "DIKKAT: bu bir GARANTI DEGIL, olasiliktir.",
    ]
    yazdir_ve_kaydet(enc, cols, f"Maksimum kapsama - {args.budget} kolon",
                     args.output, notlar, probs=args.parsed_probs,
                     tam_liste=not args.kisa, **_mc_kwargs(args))


def _mod_genel(enc: Encoder, args) -> None:
    """auto / block / exact / heuristic — hepsi `engines.adaylar()` uzerinden.

    Motor dagitiminin CLI kopyasi buradaydi; API ve saglik katmani ayni isi
    `engines.py` icinde yapiyordu. Kopya kaldirildi: CLI artik yalnizca
    SUNUM katmanidir (hangi motorun kostugunu yazar, sonucu bicimler),
    hangi motorun kosacagina karar veren tek yer `engines.adaylar()`.
    """
    motorlar = {
        "auto": ("block", "exact", "heuristic"),
        "block": ("block",),
        "exact": ("exact",),
        "heuristic": ("heuristic",),
    }[args.mode]

    eng = engine_params(
        trials=args.trials, ls_iters=args.ls_iters, seed=args.seed,
        time_limit=args.time_limit, block_limit=args.block_limit,
        exact_limit=args.exact_limit,
        # CLI'de `auto` kanit icin beklemeye razidir: kullanici komutu
        # bilerek calistirmis ve karsisinda oturuyordur. Web'de ayni bekleme
        # istek yolunu tikar, orada `auto_ilp_limit` varsayilani (3 sn) gecerli.
        auto_ilp_limit=args.time_limit,
    )
    print(f"Motorlar calisiyor: {', '.join(motorlar)}...")
    liste = adaylar(enc, eng, motorlar=motorlar, log=_log,
                    ilp_zorunlu=(args.mode == "exact"))
    if not liste:
        raise RuntimeError(
            "Hicbir motor sonuc uretemedi. scipy kurulu mu? (pip install scipy)")

    en_iyi = en_iyi_aday(liste)
    cols, baslik = en_iyi.cols, en_iyi.baslik

    notlar: list[str] = []
    if len(cols) == enc.lower_bound():
        notlar.append("Alt sinira esit -> KANITLANMIS OPTIMAL")
    elif en_iyi.kanit:
        notlar.append("ILP optimalligi kanitladi -> KANITLANMIS OPTIMAL")
    _, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    if acik:
        notlar.append(f"HATA: {acik} nokta acik kaldi!")
    if len(liste) > 1:
        notlar.append("Denenen motorlar: " +
                      ", ".join(f"{a.baslik.split(' (')[0]}={len(a.cols)}"
                                for a in liste))

    yazdir_ve_kaydet(enc, cols, baslik, args.output, notlar,
                     probs=args.parsed_probs, tam_liste=not args.kisa,
                     **_mc_kwargs(args))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spor-toto",
        description="Spor Toto 14-garanti kaplama formulu ureticisi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Ornekler:
  spor-toto --picks "{ORNEK}"
  spor-toto --picks "{ORNEK}" --variant 3
  spor-toto --picks "{ORNEK}" --mode auto
  spor-toto --picks "{ORNEK}" --mode butce --budget 32
  spor-toto --picks "{ORNEK}" --mode maxcov --budget 16
  spor-toto --picks "{ORNEK}" --probs "1:1,0:1,2:1;..." --mc-samples 20000
  spor-toto --picks "{ORNEK}" --probs "..." --bayes-preset dengeli --mc-samples 10000
  spor-toto --picks "{ORNEK}" --probs "..." --bayes --prior-strength 2 --evidence-strength 20

--picks bicimi: 15 mac virgulle ayrilir, her macin secenekleri bitisik
yazilir. '1' banko ev sahibi, '10' cifte, '102' kapama (uclu).

--probs bicimi: maclar ';' ile ayrilir, her mac '1:0.5,0:0.3,2:0.2'.

--bayes-preset: zayif_prior | dengeli | guclu_prior | evidence_agir | sadece_prior
""")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--picks", type=str, default=ORNEK,
                   help="Mac tercihleri (varsayilan: ornek kupon)")
    p.add_argument("--probs", type=str, default=None,
                   help="Mac basina olasilik tahminleri (istege bagli)")
    p.add_argument("--mc-samples", type=int, default=0,
                   help="--probs ile Monte Carlo deneme sayisi (0=kapali)")
    p.add_argument("--fire", action="store_true",
                   help="Secim DISI fire analizi (1-fire / 2-fire). "
                        "14-garantinin gecerli OLMADIGI bolgeyi olcer.")
    p.add_argument("--fire-max", type=int, default=2, choices=[1, 2],
                   help="--fire ile kac maca kadar fire incelensin (varsayilan 2)")
    p.add_argument("--bayes", action="store_true",
                   help="--probs varsa Dirichlet Bayes guncellemesi uygula")
    p.add_argument(
        "--bayes-preset",
        choices=list(BAYES_PRESET_CHOICES),
        default=None,
        help=(
            "Bayes alpha/n kisa yolu: zayif_prior | dengeli | guclu_prior | "
            "evidence_agir | sadece_prior (ayrica --bayes acar)"
        ),
    )
    p.add_argument("--prior-strength", type=float, default=None,
                   help="Dirichlet prior alpha (preset/bayes yoksa 1.0)")
    p.add_argument("--evidence-strength", type=float, default=None,
                   help="Evidence n / guven (preset/bayes yoksa 10.0)")
    p.add_argument("--mode",
                   choices=["fix16", "auto", "exact", "block", "heuristic",
                            "butce", "maxcov"],
                   default="fix16",
                   help="fix16 (varsayilan): her zaman 16 satir, en az 7 cifte "
                        "zorunlu. auto: en ucuz cozum, satir sayisi degisken. "
                        "butce: hangi maci kismalisin. maxcov: sabit butceyle "
                        "maksimum kapsama (garanti yok).")
    p.add_argument("--variant", type=int, default=0,
                   help="Ayni garantiyi veren farkli bir 16 satir uretir")
    p.add_argument("--budget", type=int, default=None,
                   help="butce/maxcov modlari icin kolon butcesi")
    p.add_argument("--plan", type=int, default=5,
                   help="butce modunda gosterilecek plan sayisi")
    p.add_argument("--plan-uygula", type=int, default=1,
                   help="butce modunda hangi planin kuponu basilsin")
    p.add_argument("--block-limit", type=int, default=256,
                   help="Blok motorunda ILP ile cozulecek maksimum blok uzayi")
    p.add_argument("--exact-limit", type=int, default=512,
                   help="auto modda ILP denenecek maksimum uzay boyutu")
    p.add_argument("--time-limit", type=float, default=60.0,
                   help="ILP zaman siniri (saniye)")
    p.add_argument("--trials", type=int, default=5)
    p.add_argument("--ls-iters", type=int, default=30000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--kisa", action="store_true",
                   help="Kolonlarin acik listesini basma")
    p.add_argument("--compare-budget", type=float, default=10.0,
                   help="fix16 modunda karsilastirmaya ayrilan saniye")
    p.add_argument("--no-compare", action="store_true",
                   help="fix16 modunda auto ile karsilastirma yapma")
    p.add_argument("--kati", action="store_true",
                   help="15 mac disindaki girdileri hata say")
    p.add_argument("--output", type=str, default=None,
                   help="Sonucun yazilacagi dosya (varsayilan: yazma)")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    t0 = time.time()

    try:
        if args.mc_samples is not None and args.mc_samples < 0:
            raise ValueError(
                f"--mc-samples negatif olamaz (alindi: {args.mc_samples}). "
                f"0 = MC kapali, pozitif = deneme sayisi."
            )
        selections = parse_picks(args.picks)
        enc = Encoder(selections, kati=args.kati)
        args.parsed_probs = parse_probs(args.probs, selections) if args.probs else None
        _apply_bayes(enc, args)

        print(CIZGI)
        print(f"SPOR TOTO 14-GARANTI FORMUL URETICISI v{__version__}")
        print(CIZGI)
        for line in basliklar(enc):
            print(line)
        for u in enc.uyarilar:
            print(f"UYARI          : {u}")
        if not HAS_SCIPY:
            print("UYARI          : scipy bulunamadi; kesin cozucu devre disi "
                  "(pip install scipy)")
        if getattr(args, "bayes_info", None):
            for line in args.bayes_info:
                print(line)
        print(INCE)

        if args.mode == "fix16":
            _mod_fix16(enc, args)
        elif args.mode == "butce":
            _mod_butce(enc, args)
        elif args.mode == "maxcov":
            _mod_maxcov(enc, args)
        else:
            _mod_genel(enc, args)

    except (ValueError, RuntimeError) as e:
        print(f"\nHATA: {e}\n", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        print("\nIptal edildi.", file=sys.stderr)
        return 130

    print(f"\nSure: {time.time() - t0:.1f} sn")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
