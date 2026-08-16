"use client";

import * as React from "react";
import { Loader2, Play } from "lucide-react";

import { getMeta, solve } from "@/lib/api";
import { kaplamaAltSiniri } from "@/lib/kume-ici";
import {
  adresiTemizle,
  kurulumuCoz,
  kurulumuKodla,
  varsayilanKurulum,
  VARSAYILAN_ENG,
  VARSAYILAN_MACLAR,
  yereldenOku,
  yereleYaz,
  yereliTemizle,
  type Kurulum,
} from "@/lib/kurulum";
import {
  devirIsaretliMi,
  haftaDevriOku,
  haftaDevriTemizle,
  type HaftaDevri,
} from "@/lib/transfer";
import {
  MAC_SAYISI,
  type MetaResponse,
  type ModeId,
  type ProbRow,
  type Sembol,
  type SolveRequest,
  type SolveResult,
} from "@/lib/types";
import { cn, normalize, sayi, sure, uniformProb } from "@/lib/utils";
import {
  Badge,
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  SectionTitle,
  Stat,
} from "@/components/ui/primitives";
import {
  Collapsible,
  NumberField,
  Select,
  SliderField,
  Switch,
} from "@/components/ui/controls";
import { Tabs, TabPanel, type TabItem } from "@/components/ui/tabs";
import { KumeIciKart } from "@/components/formul/kume-ici-kart";
import { KurulumBar } from "@/components/formul/kurulum-bar";
import { MatchGrid } from "@/components/formul/match-grid";
import { ProbGrid } from "@/components/formul/prob-grid";
import { DagilimPanel, KuponPanel, OzetPanel } from "@/components/formul/panels-core";
import { FirePanel } from "@/components/formul/panels-fire";
import {
  BayesPanel,
  BosPanel,
  HataButcesiPanel,
  HataFrekansPanel,
  LogPanel,
  OlasilikPanel,
} from "@/components/formul/panels-analiz";

const HAMMING_BLOK = 7;

/**
 * Birlestirilen sekmelerin icindeki dikis. Sekme sayisi 9'dan 5'e inince
 * bir sekmede birden fazla konu bulunuyor; okurun nerede konu degistigini
 * gormesi gerekir, yoksa birlestirme sadece uzun bir liste olur.
 */
function BolumBasligi({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 pt-1">
      <span className="text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {children}
      </span>
      <span className="h-px flex-1 bg-line" />
    </div>
  );
}

export default function FormulPage() {
  const [meta, setMeta] = React.useState<MetaResponse | null>(null);
  const [matches, setMatches] = React.useState<Sembol[][]>(VARSAYILAN_MACLAR);
  const [mode, setMode] = React.useState<ModeId>("fix16");
  const [variant, setVariant] = React.useState(0);
  const [budget, setBudget] = React.useState(32);
  const [planCount, setPlanCount] = React.useState(5);
  const [planApply, setPlanApply] = React.useState(1);
  const [kati, setKati] = React.useState(false);

  const [probsAcik, setProbsAcik] = React.useState(false);
  const [probs, setProbs] = React.useState<ProbRow[]>(() =>
    VARSAYILAN_MACLAR.map((s) => uniformProb(s)),
  );
  const [useBayes, setUseBayes] = React.useState(false);
  const [preset, setPreset] = React.useState<string>("dengeli");
  const [elleAyar, setElleAyar] = React.useState(false);
  const [prior, setPrior] = React.useState(1);
  const [evidence, setEvidence] = React.useState(10);
  const [mcSamples, setMcSamples] = React.useState(80000);
  const [fireMax, setFireMax] = React.useState(2);

  const [eng, setEng] = React.useState({ ...VARSAYILAN_ENG });

  const [sonuc, setSonuc] = React.useState<SolveResult | null>(null);
  /**
   * Ekrandaki sonucu ureten kurulumun parmak izi. Kurulum kodlamasi zaten
   * bunun icin bicilmis kaftan: modun ETKILEMEDIGI alanlari disarida
   * birakir, yani fix16'dayken butceyi degistirmek sonucu bayatlatmaz.
   */
  const [uretilenParmak, setUretilenParmak] = React.useState<string | null>(null);
  const [logMetin, setLogMetin] = React.useState("");
  const [hata, setHata] = React.useState<string | null>(null);
  const [calisiyor, setCalisiyor] = React.useState(false);
  const [gecen, setGecen] = React.useState(0);
  const [sekme, setSekme] = React.useState("sonuc");
  const [devir, setDevir] = React.useState<HaftaDevri | null>(null);
  const [baglantiNotu, setBaglantiNotu] = React.useState<{
    atlanan: string[];
    olasilikVar: boolean;
  } | null>(null);
  const iptalRef = React.useRef<AbortController | null>(null);

  // Kurulum geri yuklendi mi. Iki yerde belirleyici: (a) /api/meta gec
  // gelip geri yuklenen degerleri EZMESIN, (b) geri yukleme bitmeden yerel
  // depoya varsayilanlar yazilmasin.
  const geriYuklendiRef = React.useRef(false);
  // Yerel depoya yazma kapisi. Bilerek ref DEGIL state: ref olsaydi kayit
  // etkisi, geri yukleme henuz islenmemis ayni commit'te varsayilanlari
  // yazmaya baslar ve o yazimi yalnizca geciktirmenin iptali durdururdu.
  // State olunca kapi ancak geri yuklenmis degerlerle birlikte acilir.
  const [kayitAcik, setKayitAcik] = React.useState(false);

  const kurulum: Kurulum = React.useMemo(
    () => ({
      matches, probsAcik, probs, mode, variant, budget, planCount, planApply,
      kati, fireMax, useBayes, preset, elleAyar, prior, evidence, mcSamples, eng,
    }),
    [
      matches, probsAcik, probs, mode, variant, budget, planCount, planApply,
      kati, fireMax, useBayes, preset, elleAyar, prior, evidence, mcSamples, eng,
    ],
  );

  const uygula = React.useCallback((k: Kurulum) => {
    setMatches(k.matches.map((r) => [...r]));
    setProbs(k.probs.map((r) => ({ ...r })));
    setProbsAcik(k.probsAcik);
    setMode(k.mode);
    setVariant(k.variant);
    setBudget(k.budget);
    setPlanCount(k.planCount);
    setPlanApply(k.planApply);
    setKati(k.kati);
    setFireMax(k.fireMax);
    setUseBayes(k.useBayes);
    setPreset(k.preset);
    setElleAyar(k.elleAyar);
    setPrior(k.prior);
    setEvidence(k.evidence);
    setMcSamples(k.mcSamples);
    setEng({ ...k.eng });
  }, []);

  // Kurulumun geri yuklenmesi. Oncelik: URL > yerel depo. URL'de kurulum
  // varsa yerel kayit OKUNMAZ — paylasilan baglantiyi acan kisi kendi eski
  // kurulumunun kalintisini degil, gonderilen kurulumu gormeli.
  //
  // Devir paketi (asagida) bundan SONRA calisir ve yalnizca olasiliklarin
  // uzerine yazar; hafta detayindan gelen bir kullanicinin isaretleri
  // korunur.
  React.useEffect(() => {
    const cozum = kurulumuCoz(window.location.search);
    if (cozum) {
      uygula(cozum.kurulum);
      setBaglantiNotu({
        atlanan: cozum.atlanan,
        olasilikVar: cozum.kurulum.probsAcik,
      });
      geriYuklendiRef.current = true;
    } else {
      const yerel = yereldenOku();
      if (yerel) {
        uygula(yerel);
        geriYuklendiRef.current = true;
      }
    }
    setKayitAcik(true);
  }, [uygula]);

  // Hafta detayindaki "formule gonder" dugmesinden gelen paket. Isaret
  // URL'de (`?hafta=51`), paket sessionStorage'da ve ikisi de TUKETILMEZ:
  // App Router gecisinde sayfa iki kez baglaniyor, ikisi de ayni paketi
  // okuyup ayni degerleri yaziyor. Bkz. lib/transfer.ts.
  React.useEffect(() => {
    if (!devirIsaretliMi()) return;
    const paket = haftaDevriOku();
    if (!paket) return;
    setDevir(paket);
    setProbs(paket.probs.map((r) => ({ ...r })));
    setProbsAcik(true);
  }, []);

  // Kurulumu yerel depoya yaz. Olasilik kutularinda her tusa basista
  // yazmamak icin geciktirilir.
  React.useEffect(() => {
    if (!kayitAcik) return;
    const id = window.setTimeout(() => yereleYaz(kurulum), 400);
    return () => window.clearTimeout(id);
  }, [kurulum, kayitAcik]);

  // /api/meta: modlar, preset'ler, sinirlar — hicbiri sabit kodlanmaz.
  React.useEffect(() => {
    const ac = new AbortController();
    getMeta(ac.signal)
      .then((m) => {
        setMeta(m);
        // Sunucunun varsayilanlari YALNIZCA geri yuklenen bir kurulum
        // yokken uygulanir. Aksi halde gec gelen meta, kullanicinin
        // kaydettigi motor ayarlarini ve MC ornek sayisini sessizce ezerdi.
        if (geriYuklendiRef.current) return;
        setEng((e) => ({ ...e, ...m.engine_defaults }));
        setMcSamples(m.limits?.mc_samples?.default ?? 80000);
      })
      .catch(() => {
        /* meta alinamazsa arayuz calisir, sadece aciklamalar eksik olur */
      });
    return () => ac.abort();
  }, []);

  const sifirla = React.useCallback(() => {
    yereliTemizle();
    haftaDevriTemizle();
    // Adres de temizlenir: aksi halde yenileme, az once silinen kurulumu
    // baglantidan geri getirirdi.
    adresiTemizle();
    setDevir(null);
    setBaglantiNotu(null);
    setSonuc(null);
    setUretilenParmak(null);
    setLogMetin("");
    setHata(null);
    uygula(varsayilanKurulum());
  }, [uygula]);

  // Gecen sure sayaci — uzun suren istekler icin bekleme anlatisi.
  React.useEffect(() => {
    if (!calisiyor) return;
    const t0 = performance.now();
    setGecen(0);
    const id = window.setInterval(() => setGecen(performance.now() - t0), 100);
    return () => window.clearInterval(id);
  }, [calisiyor]);

  // Secimler degisince olasilik satirlarini hizada tut.
  React.useEffect(() => {
    setProbs((p) => matches.map((sel, i) => p[i] ?? uniformProb(sel)));
  }, [matches]);

  const canli = React.useMemo(() => {
    let banko = 0;
    let cifte = 0;
    let uclu = 0;
    for (const satir of matches) {
      const n = satir.length || 1;
      if (n === 1) banko++;
      else if (n === 2) cifte++;
      else uclu++;
    }
    return { banko, cifte, uclu, ...kaplamaAltSiniri(matches) };
  }, [matches]);

  const modInfo = meta?.modes.find((m) => m.id === mode);
  const butceGerekli =
    modInfo?.needs_budget ?? (mode === "butce" || mode === "maxcov");

  /**
   * Uretmeden once soylenebilecek bedel. Uc AYRI durum var ve tek bir
   * sayiya indirilemezler:
   *
   *   fix16   kesin — blok 2^7 noktayi 16 satira indirir, yani uzay/8.
   *   butce   tavan — odeyecegin en fazla kendi girdigin butcedir.
   *   digeri  aralik — motor kac kolon uretecegini arama sonunda bilir.
   *
   * Onceki surum ucunu de tek formulle veriyordu ve fix16 disinda UZAYI
   * yaziyordu: `auto` modunda ayni kupon icin "256 kolon" diyordu, motor
   * 32 uretiyordu (olculdu). Sekiz kat abarti, hem de odenecek tutari
   * soyleyen en gorunur yerde.
   */
  const bedel = React.useMemo(() => {
    if (mode === "fix16" && canli.cifte >= HAMMING_BLOK) {
      return { tip: "kesin" as const, deger: Math.round(canli.uzay / 8) };
    }
    if (butceGerekli) return { tip: "tavan" as const, deger: budget };
    return { tip: "aralik" as const, alt: canli.altSinir, ust: canli.uzay };
  }, [mode, butceGerekli, budget, canli]);
  const scipyEksik = Boolean(modInfo?.needs_scipy && meta?.has_scipy === false);
  const fix16Yetersiz = mode === "fix16" && canli.cifte < HAMMING_BLOK;

  const calistir = React.useCallback(
    async (planUygula?: number) => {
      iptalRef.current?.abort();
      const ac = new AbortController();
      iptalRef.current = ac;
      setCalisiyor(true);
      setHata(null);

      // Parmak izi istek KURULURKEN alinir, cevap donunce degil: arada
      // kullanici girdiyi degistirmisse sonuc zaten o degisiklige ait
      // olmayacak ve bayat isaretlenmesi gerekir.
      const parmak = kurulumuKodla(
        planUygula === undefined ? kurulum : { ...kurulum, planApply: planUygula },
      );

      const govde: SolveRequest = {
        matches,
        mode,
        variant,
        kati,
        fire_max: fireMax,
        ...(butceGerekli ? { budget } : {}),
        ...(mode === "butce"
          ? { plan_count: planCount, plan_apply: planUygula ?? planApply }
          : {}),
        ...(probsAcik
          ? {
              probs: probs.map((p) => normalize(p)),
              mc_samples: mcSamples,
              use_bayes: useBayes,
              ...(useBayes && !elleAyar ? { bayes_preset: preset } : {}),
              ...(useBayes && elleAyar
                ? { prior_strength: prior, evidence_strength: evidence }
                : {}),
            }
          : {}),
        ...eng,
      };

      try {
        const cevap = await solve(govde, ac.signal);
        setLogMetin(cevap.run_log_text || "");
        if (!cevap.ok || !cevap.result) {
          setHata(cevap.error || "Bilinmeyen hata");
        } else {
          setSonuc(cevap.result);
          setUretilenParmak(parmak);
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setHata(e instanceof Error ? e.message : String(e));
      } finally {
        if (!ac.signal.aborted) setCalisiyor(false);
      }
    },
    [
      matches, mode, variant, kati, fireMax, butceGerekli, budget, planCount, planApply,
      probsAcik, probs, mcSamples, useBayes, elleAyar, preset, prior, evidence, eng,
      kurulum,
    ],
  );

  // Ekrandaki sonuc hala girdiyi mi anlatiyor. Sonuc SILINMEZ — eski sonuc
  // hala okunabilir bir bilgidir, yalnizca artik neyi anlattigi soylenir.
  const bayat =
    sonuc !== null && uretilenParmak !== null && uretilenParmak !== kurulumuKodla(kurulum);

  /*
    Sekmeler SORUYA gore bolunur, motor blogua gore degil.
    Onceki dizilim backend modullerinin birebir yansimasiydi (Ozet,
    Kupon, Dagilim, Olasilik, Bayes, Markov, Hata frekansi, Fire, Log) ve
    kullanicinin dort sorusundan ikisi ucer-dorder sekmeye dagiliyordu:
    "ne kadar riskli" Olasilik+Markov+Dagilim'a, "hangi maci degistireyim"
    Hata frekansi+Fire+Markov'a.
  */
  const sekmeler: TabItem[] = [
    { id: "sonuc", label: "Ne aldım" },
    { id: "kupon", label: "Ne yazacağım", badge: sonuc ? sonuc.satir_sayisi : undefined },
    { id: "risk", label: "Ne kadar riskli", enabled: !!sonuc?.advanced },
    {
      id: "zayif",
      label: "Zayıf halkalar",
      enabled: !!(sonuc?.error_freq || sonuc?.fire),
    },
    { id: "log", label: "Log", enabled: !!logMetin },
  ];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[32px] italic leading-tight">Formül üret</h1>
        <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
          Seçtiğin ihtimal kümeleri içinde doğru sonuç varsa, oynanan kolonlardan
          en az biri en fazla 1 maç hatalı olur — yani <strong>14-garanti</strong>.
          Bu araç maç sonucu <strong>tahmin etmez</strong>; tahminin doğruysa onu
          en az kuponla garantiye alır.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
        {/*
          ── Girdi ────────────────────────────────────────────
          `min-w-0` sart: izgara ogesinin varsayilan `min-width:auto`'su
          icerigin min-content genisligine kilitlenir. Olasilik izgarasi
          `min-w-[420px]` tasiyor ve kendi `overflow-x-auto` sarmalayicisi
          bunu icerde tutamiyor — telefonda (390 px) TUM sol kolonu 462 px'e
          itip sayfayi yatay kaydiriyordu, olasilik girisi acikken.
        */}
        <div className="min-w-0 space-y-4">
          <KurulumBar kurulum={kurulum} onSifirla={sifirla} disabled={calisiyor} />

          {baglantiNotu ? (
            <Callout ton="primary" baslik="Kurulum bağlantıdan yüklendi">
              <p>
                Maç işaretleri ve motor ayarları adresteki bağlantıdan geldi.
                {baglantiNotu.atlanan.length ? (
                  <>
                    {" "}
                    Bağlantıdaki <strong>{baglantiNotu.atlanan.join(", ")}</strong>{" "}
                    okunamadı ve varsayılana düşürüldü — uydurulmadı, aşağıdan
                    kontrol et.
                  </>
                ) : null}
                {baglantiNotu.olasilikVar ? (
                  <>
                    {" "}
                    Olasılıklar bağlantıda <strong>binde bir</strong> çözünürlükle
                    ve <strong>1&apos;e normalize edilmiş</strong> taşınır; gönderen
                    ham ağırlık girdiyse (5/3/2) burada oranı korunmuş halini
                    (0.5/0.3/0.2) görürsün.
                  </>
                ) : null}
              </p>
              <button
                type="button"
                onClick={() => setBaglantiNotu(null)}
                className="mt-2 text-[12px] underline underline-offset-2 hover:no-underline"
              >
                Bu notu kapat
              </button>
            </Callout>
          ) : null}

          <Card>
            <CardHeader
              title="Maç seçimleri"
              hint="Her maç için en az bir sembol. Semboller kupon düzeninde."
            />
            <CardBody>
              <MatchGrid matches={matches} onChange={setMatches} disabled={calisiyor} />
            </CardBody>
          </Card>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat etiket="Banko" deger={canli.banko} />
            <Stat
              etiket="Çifte"
              deger={canli.cifte}
              ton={fix16Yetersiz ? "danger" : "neutral"}
            />
            <Stat etiket="Üçlü" deger={canli.uclu} />
            <Stat etiket="Uzay" deger={sayi(canli.uzay)} />
          </div>

          <KumeIciKart
            matches={matches}
            probs={probs}
            acik={probsAcik}
            onAc={() => setProbsAcik(true)}
            onEsitle={() =>
              setProbs(matches.map(() => ({ "1": 1 / 3, "0": 1 / 3, "2": 1 / 3 })))
            }
          />

          {fix16Yetersiz ? (
            <Callout
              ton="danger"
              baslik={`Sabit 16 satır en az ${HAMMING_BLOK} çifte ister`}
            >
              Şu an {canli.cifte} çifte var. Bir maçı daha çifte yap ya da{" "}
              <strong>Otomatik</strong> moda geç — o mod eldeki en iyi bloğu kendi
              seçer (satır sayısı 16 olmayabilir).
            </Callout>
          ) : null}

          <Card>
            <CardHeader title="Motor" hint={modInfo?.aciklama} />
            <CardBody className="space-y-4">
              <Select
                label="Mod"
                value={mode}
                onChange={(v) => setMode(v as ModeId)}
                options={
                  meta?.modes.map((m) => ({ value: m.id, label: m.label })) ?? [
                    { value: "fix16" as ModeId, label: "Sabit 16 satır" },
                  ]
                }
              />

              {modInfo && !modInfo.garanti ? (
                <Callout ton="danger" baslik="Bu mod 14-garanti VERMEZ">
                  Sabit bütçeyle mümkün olan en geniş kapsamayı arar. Kapsanmayan
                  noktalar için hiçbir güvence yoktur.
                </Callout>
              ) : null}

              {scipyEksik ? (
                <Callout ton="warning" baslik="scipy kurulu değil">
                  Bu mod ILP gerektirir ve şu an kullanılamaz.
                </Callout>
              ) : null}

              <div className="grid grid-cols-2 gap-3">
                <NumberField
                  label="Varyant"
                  value={variant}
                  onChange={setVariant}
                  min={0}
                  hint="Aynı garantiyi veren farklı 16 satır"
                />
                {butceGerekli ? (
                  <NumberField
                    label="Bütçe"
                    value={budget}
                    onChange={setBudget}
                    min={1}
                    suffix="kolon"
                  />
                ) : null}
              </div>

              {mode === "butce" ? (
                <div className="grid grid-cols-2 gap-3">
                  <NumberField
                    label="Plan sayısı"
                    value={planCount}
                    onChange={setPlanCount}
                    min={1}
                    max={50}
                  />
                  <NumberField
                    label="Uygulanacak plan"
                    value={planApply}
                    onChange={setPlanApply}
                    min={1}
                    max={planCount}
                  />
                </div>
              ) : null}

              <Select
                label="Fire analizi (seçim dışı)"
                value={String(fireMax)}
                onChange={(v) => setFireMax(Number(v))}
                options={[
                  { value: "2", label: "1 ve 2 maç dışarı çıkarsa" },
                  { value: "1", label: "Yalnızca 1 maç dışarı çıkarsa" },
                  { value: "0", label: "Kapalı" },
                ]}
                hint="14-garantinin geçerli OLMADIĞI bölgeyi ölçer. Büyük kuponlarda pahalıdır; sınır aşılırsa atlanır."
              />

              <Switch
                checked={kati}
                onChange={setKati}
                label="Katı giriş doğrulaması"
                hint={`${MAC_SAYISI} maç dışındaki girdileri uyarı değil hata say`}
              />
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Olasılık"
              hint="Kendi 1/0/2 tahminlerini gir — exact olasılık, Monte Carlo, Bayes ve Markov panelleri ancak bununla dolar."
            />
            <CardBody className="space-y-4">
              <Switch
                checked={probsAcik}
                onChange={setProbsAcik}
                label="Olasılık girişini kullan"
                hint="Kapalıyken yalnızca kombinatoryal sonuç hesaplanır"
              />

              {devir ? (
                <Callout ton="primary" baslik={`${devir.week}. hafta yüklendi`}>
                  <p>
                    15 maçın olasılığı {devir.note} dolduruldu.{" "}
                    {devir.missing.length
                      ? `Oranı bulunamayan ${devir.missing.join(", ")}. maç eşit (1/3) bırakıldı — ` +
                        "uydurulmadı."
                      : "Tüm maçların oranı vardı."}{" "}
                    <strong>İşaretler taşınmadı:</strong> hangi maça banko, hangisine çifte
                    koyacağın senin kararın — bu araç maç sonucu tahmin etmez.
                  </p>
                  {devir.labels.some(Boolean) ? (
                    <ol className="tnum mt-2 grid gap-x-4 gap-y-0.5 text-[11.5px] sm:grid-cols-2">
                      {devir.labels.map((ad, i) => (
                        <li key={i} className="truncate">
                          <span className="opacity-60">{i + 1}.</span> {ad || "—"}
                        </li>
                      ))}
                    </ol>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => {
                      // Paketi de sil: aksi halde sayfa yeniden baglandiginda
                      // kapatilan not geri gelirdi.
                      haftaDevriTemizle();
                      setDevir(null);
                    }}
                    className="mt-2 text-[12px] underline underline-offset-2 hover:no-underline"
                  >
                    Bu notu kapat
                  </button>
                </Callout>
              ) : null}

              {probsAcik ? (
                <>
                  <ProbGrid
                    probs={probs}
                    selections={matches}
                    onChange={setProbs}
                    disabled={calisiyor}
                  />

                  <SliderField
                    label="Monte Carlo örnek sayısı"
                    value={mcSamples}
                    onChange={setMcSamples}
                    min={meta?.limits?.mc_samples?.min ?? 1000}
                    max={meta?.limits?.mc_samples?.max ?? 200000}
                    step={1000}
                    format={(v) => sayi(v)}
                    hint="Daha fazla örnek = daha dar güven aralığı, daha uzun süre"
                  />

                  <div className="space-y-3 rounded-xl border border-line p-4">
                    <Switch
                      checked={useBayes}
                      onChange={setUseBayes}
                      label="Bayes (Dirichlet) güncellemesi"
                      hint="Seçim kümene dayalı prior ile tahminlerini yumuşatır"
                    />
                    {useBayes ? (
                      <>
                        <Switch
                          checked={elleAyar}
                          onChange={setElleAyar}
                          label="α / n değerlerini elle gir"
                          hint="Kapalıyken hazır preset kullanılır (CLI ile aynı değerler)"
                        />
                        {elleAyar ? (
                          <div className="grid grid-cols-2 gap-3">
                            <NumberField
                              label="Prior α"
                              value={prior}
                              onChange={setPrior}
                              min={0}
                              step={0.5}
                            />
                            <NumberField
                              label="Evidence n"
                              value={evidence}
                              onChange={setEvidence}
                              min={0}
                              step={1}
                            />
                          </div>
                        ) : (
                          <Select
                            label="Preset"
                            value={preset}
                            onChange={setPreset}
                            options={
                              meta?.bayes_presets.map((p) => ({
                                value: p.id,
                                label: `${p.id} — α ${p.prior_strength} / n ${p.evidence_strength}`,
                              })) ?? [{ value: "dengeli", label: "dengeli" }]
                            }
                          />
                        )}
                      </>
                    ) : null}
                  </div>
                </>
              ) : null}
            </CardBody>
          </Card>

          <Collapsible
            baslik="Motor ayarları"
            hint="Sezgisel arama ve ILP parametreleri — CLI ile aynı"
          >
            <div className="grid grid-cols-2 gap-3">
              <NumberField
                label="trials"
                value={eng.trials}
                min={1}
                max={50}
                onChange={(v) => setEng((e) => ({ ...e, trials: v }))}
              />
              <NumberField
                label="ls_iters"
                value={eng.ls_iters}
                min={100}
                max={500000}
                step={1000}
                onChange={(v) => setEng((e) => ({ ...e, ls_iters: v }))}
              />
              <NumberField
                label="seed"
                value={eng.seed}
                min={0}
                onChange={(v) => setEng((e) => ({ ...e, seed: v }))}
              />
              <NumberField
                label="time_limit"
                value={eng.time_limit}
                min={1}
                max={300}
                suffix="sn"
                onChange={(v) => setEng((e) => ({ ...e, time_limit: v }))}
              />
              <NumberField
                label="block_limit"
                value={eng.block_limit}
                min={2}
                max={6561}
                onChange={(v) => setEng((e) => ({ ...e, block_limit: v }))}
              />
              <NumberField
                label="exact_limit"
                value={eng.exact_limit}
                min={2}
                max={4096}
                onChange={(v) => setEng((e) => ({ ...e, exact_limit: v }))}
              />
            </div>
          </Collapsible>

          {/*
            Yapiskan buton icerigin uzerinde durur; arkasina cam zemin
            konmazsa altindaki "tahmini bedel" satiri izgaranin uzerine
            binip okunmaz oluyor.
          */}
          <div className="sticky bottom-3 z-20 -mx-1 rounded-2xl border border-line bg-background/80 p-3 shadow-card backdrop-blur-xl">
            <Button
              boyut="lg"
              className="w-full"
              onClick={() => void calistir()}
              disabled={calisiyor || fix16Yetersiz || scipyEksik}
            >
              {calisiyor ? (
                <>
                  <Loader2 size={17} className="animate-spin" />
                  Hesaplanıyor… {sure(gecen)}
                </>
              ) : (
                <>
                  <Play size={16} />
                  Formülü üret
                </>
              )}
            </Button>
            <p className="mt-2 text-center text-[11px] leading-relaxed text-muted-foreground">
              {bedel.tip === "kesin" ? (
                <>
                  Bedel: <strong>{sayi(bedel.deger)} kolon</strong> · 16 satır
                </>
              ) : null}
              {bedel.tip === "tavan" ? (
                <>
                  Bedel: <strong>en çok {sayi(bedel.deger)} kolon</strong> —
                  girdiğin bütçe
                </>
              ) : null}
              {bedel.tip === "aralik" ? (
                <>
                  Bedel: <strong>{sayi(bedel.alt)}–{sayi(bedel.ust)} kolon</strong>{" "}
                  · alt sınır küre-kaplama, üst sınır tam sistem; kesin sayıyı
                  motor belirler
                </>
              ) : null}
              {" · ödeyeceğin tutar kolon sayısıdır"}
            </p>
          </div>
        </div>

        {/* ── Sonuç ──────────────────────────────────────────── */}
        <div className="min-w-0 space-y-4">
          {hata ? (
            <Callout ton="danger" baslik="Motor hata verdi">
              {hata}
            </Callout>
          ) : null}

          {calisiyor ? (
            <Card>
              <CardBody className="flex items-center gap-3">
                <Loader2 size={18} className="animate-spin text-primary" />
                <div className="min-w-0">
                  <div className="text-[13.5px] font-medium">
                    {modInfo?.label ?? mode} çalışıyor — {sure(gecen)}
                  </div>
                  <div className="text-[11.5px] text-muted-foreground">
                    {gecen > 6000
                      ? "Büyük uzaylarda bu normal. Adım süreleri Log sekmesinde."
                      : "Kaplama üretiliyor…"}
                  </div>
                </div>
              </CardBody>
            </Card>
          ) : null}

          {!sonuc && !calisiyor && !hata ? (
            <Card>
              <CardBody className="py-16 text-center">
                <SectionTitle>Henüz formül üretilmedi</SectionTitle>
                <p className="mx-auto max-w-md text-[12.5px] leading-relaxed text-muted-foreground">
                  Soldan maçlarını işaretle ve <strong>Formülü üret</strong>&apos;e
                  bas. Olasılık girişini açarsan Bayes, Monte Carlo ve Markov
                  panelleri de dolar.
                </p>
              </CardBody>
            </Card>
          ) : null}

          {sonuc ? (
            <div
              className={cn(
                "space-y-4 transition-opacity duration-300",
                // Yeni sonuc gelene kadar eskisi ekranda kalir, sadece soluklasir
                calisiyor && "pointer-events-none opacity-40",
              )}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge ton="primary">{sonuc.baslik}</Badge>
                {sonuc.mode ? <Badge>{sonuc.mode}</Badge> : null}
                {!sonuc.has_scipy ? <Badge ton="warning">scipy yok</Badge> : null}
              </div>

              {bayat ? (
                <Callout ton="warning" baslik="Bu sonuç girdinin eski hâline ait">
                  <p>
                    Sonuç üretildikten sonra soldaki kurulumu değiştirdin.
                    Aşağıdaki kupon, bedel ve olasılıklar <strong>eski</strong>
                    {" "}girdiyi anlatıyor — yeni hâlini görmek için yeniden üret.
                  </p>
                  <Button
                    tip="outline"
                    boyut="sm"
                    className="mt-2.5"
                    onClick={() => void calistir()}
                    disabled={calisiyor || fix16Yetersiz || scipyEksik}
                  >
                    <Play size={13} />
                    Yeniden üret
                  </Button>
                </Callout>
              ) : null}

              <Tabs items={sekmeler} value={sekme} onChange={setSekme} />

              {/* Ne aldım — bedel, garanti ve kapsamanın geometrisi */}
              <TabPanel id="sonuc" active={sekme === "sonuc"}>
                <div className="space-y-4">
                  <OzetPanel
                    r={sonuc}
                    onPlanSec={
                      sonuc.butce_planlari
                        ? (p) => {
                            setPlanApply(p.index);
                            void calistir(p.index);
                          }
                        : undefined
                    }
                  />
                  <BolumBasligi>Kapsamanın geometrisi</BolumBasligi>
                  <DagilimPanel r={sonuc} />
                </div>
              </TabPanel>

              <TabPanel id="kupon" active={sekme === "kupon"}>
                <KuponPanel r={sonuc} />
              </TabPanel>

              {/* Ne kadar riskli — hepsi SENİN tahminlerine bağlı olanlar */}
              <TabPanel id="risk" active={sekme === "risk"}>
                {sonuc.advanced ? (
                  <div className="space-y-4">
                    <OlasilikPanel r={sonuc} />
                    {sonuc.markov ? (
                      <>
                        <BolumBasligi>Hata bütçesi</BolumBasligi>
                        <HataButcesiPanel r={sonuc} />
                      </>
                    ) : null}
                    {sonuc.bayes ? (
                      <>
                        <BolumBasligi>Bayes güncellemesi</BolumBasligi>
                        <BayesPanel r={sonuc} />
                      </>
                    ) : null}
                  </div>
                ) : (
                  <BosPanel baslik="Olasılık verisi yok">
                    Soldaki <strong>Olasılık girişini kullan</strong> anahtarını aç ve
                    maç bazlı tahminlerini gir. Bu sekmedeki her şey senin
                    tahminlerine bağlıdır; kombinatoryal 14-garanti onlardan
                    bağımsızdır ve <strong>Ne aldım</strong> sekmesinde durur.
                  </BosPanel>
                )}
              </TabPanel>

              {/* Zayıf halkalar — hangi maçı değiştirmeliyim */}
              <TabPanel id="zayif" active={sekme === "zayif"}>
                {sonuc.error_freq || sonuc.fire ? (
                  <div className="space-y-4">
                    {sonuc.error_freq ? <HataFrekansPanel r={sonuc} /> : null}
                    {sonuc.fire ? (
                      <>
                        <BolumBasligi>Seçim dışına çıkarsa (fire)</BolumBasligi>
                        <FirePanel r={sonuc} />
                      </>
                    ) : null}
                  </div>
                ) : (
                  <BosPanel baslik="Zayıf halka analizi çalışmadı">
                    Hata frekansı için uzay fazla büyük olabilir; fire analizi
                    ise Motor kartından açılır.
                  </BosPanel>
                )}
              </TabPanel>

              <TabPanel id="log" active={sekme === "log"}>
                <LogPanel metin={logMetin} />
              </TabPanel>
            </div>
          ) : null}

          {!sonuc && logMetin ? <LogPanel metin={logMetin} /> : null}
        </div>
      </div>

      <Callout ton="neutral" baslik="Sorumlu oynayın">
        Bu araç kazanma olasılığını <strong>artırmaz</strong>. Yalnızca belirli bir
        garantiyi daha az kuponla elde etmeni sağlar. Olasılık, Monte Carlo, Bayes
        ve Markov çıktıları beklenen-değer veya kâr hesabı değildir; ikramiye
        havuzu ve kolon bedeli hesaba katılmaz.
      </Callout>
    </div>
  );
}
