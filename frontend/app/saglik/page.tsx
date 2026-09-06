"use client";

import * as React from "react";
import { Check, Copy, ListFilter, RefreshCw } from "lucide-react";

import {
  denetleKupon,
  getHealth,
  getHealthChecks,
  getHealthHistory,
} from "@/lib/api";
import { useIstek } from "@/lib/istek";
import { hataMetni, iptalMi } from "@/lib/istek";
import type {
  HealthHistoryResponse,
  HealthReport,
  KuponDenetimSonuc,
} from "@/lib/types";
import { cn, panoyaKopyala, sure } from "@/lib/utils";
import { adreseYaz, adrestenOku } from "@/lib/adres";
import {
  Badge,
  Button,
  Callout,
  Card,
  CardBody,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";
import {
  DURUM_METNI,
  DURUM_TONU,
  DurumIkonu,
  type GecmisKaydi,
  GecmisSeridi,
  KategoriKarti,
  KontrolEnvanteri,
  KuponDenetimi,
  OrtamKarti,
  SunucuGecmisi,
  durumu,
  goreliZaman,
  kategoriAnkraji,
} from "@/components/saglik/parts";

/** Otomatik yenileme aralıkları (saniye; 0 = kapalı). */
const ARALIKLAR = [0, 15, 60, 300] as const;
const ARALIK_ETIKET: Record<number, string> = {
  0: "Kapalı",
  15: "15 sn",
  60: "1 dk",
  300: "5 dk",
};

const GECMIS_SINIRI = 8;

/** Sekme başlığı: sayfa arka planda açık tutulmak için var (§7.15). */
const BASLIK = "Sistem sağlığı";
const BASLIK_ISARETI: Record<string, string> = {
  saglikli: "",
  kisitli: "⚠ ",
  bozuk: "✗ ",
};

/** `?only=` adresten okunur; düşen bir kategorinin bağlantısı paylaşılabilir
 * olsun ve yenilemede kaybolmasın diye (§7.14). */
const adrestekiOnly = () => adrestenOku("only");
const adresiGuncelle = (only: string | null) => adreseYaz("only", only);

export default function SaglikPage() {
  const [rapor, setRapor] = React.useState<HealthReport | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = React.useState(true);
  const [gecmis, setGecmis] = React.useState<GecmisKaydi[]>([]);
  const [aralik, setAralik] = React.useState<number>(0);
  const [yalnizDusenler, setYalnizDusenler] = React.useState(false);
  const [kopyalandi, setKopyalandi] = React.useState(false);

  // Gorelı zaman ("14 sn once") yalnizca mount sonrasi hesaplanir; sunucuda
  // hesaplanirsa hydration uyusmazligi olur.
  const [simdi, setSimdi] = React.useState<number | null>(null);
  React.useEffect(() => {
    setSimdi(Date.now());
    const t = setInterval(() => setSimdi(Date.now()), 10_000);
    return () => clearInterval(t);
  }, []);

  // Sunucu tarafi gecmis: oturum icinden farkli olarak sekme kapansa da
  // kalir ve "ne zamandan beri kirmizi?" sorusunu cevaplar.
  const [sunucuGecmisi, setSunucuGecmisi] =
    React.useState<HealthHistoryResponse | null>(null);

  // Kullanicinin kendi kuponu — kayitli rapordan AYRI katman.
  const [kuponPicks, setKuponPicks] = React.useState("");
  const [kuponSonuc, setKuponSonuc] = React.useState<KuponDenetimSonuc | null>(null);
  const [kuponHata, setKuponHata] = React.useState<string | null>(null);
  const [kuponCalisiyor, setKuponCalisiyor] = React.useState(false);

  const sayacRef = React.useRef(0);
  // Ucan istek. Her yeni cagri oncekini iptal eder: kismi bir kosu ile arka
  // plandaki tam kosu carpisirsa cevaplar GELIS sirasina gore yazilirdi ve
  // ekranda gonderim sirasi degil, sansin sirasi kalirdi.
  const istekRef = React.useRef<AbortController | null>(null);

  const gecmiseYaz = React.useCallback((kayit: Omit<GecmisKaydi, "id">) => {
    setGecmis((onceki) =>
      [{ id: ++sayacRef.current, ...kayit }, ...onceki].slice(0, GECMIS_SINIRI),
    );
  }, []);

  // Kayitli kontrol envanteri. Rapordan BAGIMSIZ cekilir ve bu kasitli:
  // "bu sistem neyi denetliyor" sorusunun cevabi olcum kosmadan, servis
  // dususke bile okunabilmeli.
  const {
    veri: envanter,
    hata: envanterHatasi,
    yukleniyor: envanterYukleniyor,
  } = useIstek((signal) => getHealthChecks(signal), [], {
    varsayilanHata: "Kontrol envanteri alınamadı",
  });

  /**
   * Bu yukleyici bilerek `lib/istek.useIstek` KULLANMAZ. O kanca bildirimsel
   * bir veri cekme icindir: bagimlilik degisir, istek kosar. Burasi ise
   * parametreli bir EYLEM — `only`/`fresh` ile cagrilir, basariyi da
   * basarisizligi da gecmis seridine yazar, adres cubugunu gunceller ve
   * ardina ikinci bir istek zincirler. Kancaya zorlamak ikisini de
   * bozardi; paylasilan sey ortak olan tek sey oldu: iptal kurali.
   */
  const yukle = React.useCallback(
    async (only?: string | null, opt: { fresh?: boolean } = {}) => {
      istekRef.current?.abort();
      const ac = new AbortController();
      istekRef.current = ac;

      setYukleniyor(true);
      setHata(null);
      try {
        const r = await getHealth(only, ac.signal, opt.fresh);
        setRapor(r);
        adresiGuncelle(r.summary.kismi ? (r.summary.only ?? null) : null);
        // Sunucu gecmisi rapordan SONRA cekilir: az onceki kosu da icinde
        // olsun. Basarisizligi raporu gostermeyi engellemez — gecmis bir
        // konfor, rapor ise sayfanin kendisidir.
        if (!r.summary.kismi) {
          getHealthHistory(50, ac.signal)
            .then(setSunucuGecmisi)
            .catch(() => undefined);
        }
        gecmiseYaz({
          zaman: r.timestamp,
          ok: r.ok,
          degraded: r.degraded,
          passed: r.passed,
          total: r.total,
          duration_ms: r.duration_ms,
          kismi: Boolean(r.summary.kismi),
          onbellekten: Boolean(r.summary.onbellek?.cached),
        });
      } catch (e) {
        // Iptal deyimi `lib/istek`ten: depoda uc ayri surumu vardi.
        if (iptalMi(e, ac.signal)) return;
        const mesaj = hataMetni(e, "Sağlık raporu alınamadı");
        setHata(mesaj);
        // Ulasilamayan bir kosu da bir kayittir — hatta zaman cizelgesinde
        // en cok gormek isteyecegin olay tam odur. Sessizce dusurmek,
        // gecmisi "yalnizca iyi gunlerin" kaydina cevirirdi.
        gecmiseYaz({
          zaman: new Date().toISOString(),
          ok: false,
          degraded: false,
          passed: 0,
          total: 0,
          duration_ms: 0,
          kismi: false,
          onbellekten: false,
          hata: mesaj,
        });
      } finally {
        if (istekRef.current === ac) {
          istekRef.current = null;
          setYukleniyor(false);
        }
      }
    },
    [gecmiseYaz],
  );

  // Ilk kosu adresteki `?only=` ile baslar: paylasilan bir baglanti dogrudan
  // o kapsami acar.
  React.useEffect(() => {
    void yukle(adrestekiOnly());
    return () => istekRef.current?.abort();
  }, [yukle]);

  // Otomatik yenileme her zaman TAM raporu calistirir: kismi bir kosuyu
  // arka planda tekrarlamak yaniltici olurdu.
  //
  // Sekme gizliyken duraklar (§7.8): arka plandaki bir sekme saatlerce
  // kosup gecmis seridini anlamsiz kayitlarla doldururdu. Sekme geri
  // geldiginde bir kez kosar, boylece ekrandaki rapor bayat kalmaz.
  React.useEffect(() => {
    if (!aralik) return;

    let t: ReturnType<typeof setInterval> | null = null;
    const durdur = () => {
      if (t) clearInterval(t);
      t = null;
    };
    const basla = () => {
      durdur();
      t = setInterval(() => void yukle(null), aralik * 1000);
    };

    const gorunurlukDegisti = () => {
      if (document.visibilityState === "visible") {
        void yukle(null);
        basla();
      } else {
        durdur();
      }
    };

    if (document.visibilityState === "visible") basla();
    document.addEventListener("visibilitychange", gorunurlukDegisti);
    return () => {
      durdur();
      document.removeEventListener("visibilitychange", gorunurlukDegisti);
    };
  }, [aralik, yukle]);

  const durum = rapor ? durumu(rapor) : null;

  // Sekme basligi durumu tasir: alarm altyapisi gerektirmeyen en yakin
  // "haber verme". Sayfa arka planda acik tutulmak icin var.
  // Ayrilirken UYGULAMA basligi geri konur. Once temizlik `BASLIK`
  // ("Sistem sagligi") yaziyordu: bu sayfadan cikan kullanici
  // /istatistik'te de /tahmin'de de sekmede "Sistem sagligi" goruyordu.
  //
  // Yakalama AYRI ve ONCE gelen bir etki: React etkileri bildirim
  // sirasinda kosar, yani burasi asagidaki set'ten once calisir ve
  // bozulmamis basligi alir. Tek etkide `const onceki = document.title`
  // yeterli olmazdi — etki [durum, hata] ile yeniden kostugunda `onceki`
  // bu sayfanin kendi basligina donerdi.
  const uygulamaBasligi = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (uygulamaBasligi.current === null) uygulamaBasligi.current = document.title;
    return () => {
      if (uygulamaBasligi.current !== null) document.title = uygulamaBasligi.current;
    };
  }, []);

  React.useEffect(() => {
    document.title = hata
      ? `✗ ${BASLIK}`
      : `${durum ? BASLIK_ISARETI[durum] : ""}${BASLIK}`;
  }, [durum, hata]);

  const kuponuDenetle = React.useCallback(async () => {
    const picks = kuponPicks.trim();
    if (!picks) return;
    setKuponCalisiyor(true);
    setKuponHata(null);
    try {
      setKuponSonuc(await denetleKupon({ picks }));
    } catch (e) {
      setKuponSonuc(null);
      setKuponHata(e instanceof Error ? e.message : String(e));
    } finally {
      setKuponCalisiyor(false);
    }
  }, [kuponPicks]);

  // Kutu bos baslamasin: rapordaki ornek kupon, denemek icin hazir bir
  // baslangictir ve "hangi bicimde yazacagim?" sorusunu da cevaplar.
  React.useEffect(() => {
    if (!kuponPicks && rapor?.summary.ornek_kupon) {
      setKuponPicks(rapor.summary.ornek_kupon);
    }
  }, [rapor, kuponPicks]);

  const kopyala = React.useCallback(async () => {
    if (!rapor) return;
    try {
      await panoyaKopyala(JSON.stringify(rapor, null, 2));
      setKopyalandi(true);
      setTimeout(() => setKopyalandi(false), 1800);
    } catch {
      /* pano yoksa sessizce gec */
    }
  }, [rapor]);

  const ton = durum ? DURUM_TONU[durum] : "neutral";
  const dusenler = React.useMemo(
    () => (rapor ? rapor.checks.filter((c) => !c.ok) : []),
    [rapor],
  );
  const enUzunMs = React.useMemo(
    () => (rapor ? Math.max(...rapor.checks.map((c) => c.duration_ms), 0) : 0),
    [rapor],
  );
  const yavaslar = React.useMemo(
    () => (rapor ? rapor.checks.filter((c) => c.ok && c.yavas).map((c) => c.name) : []),
    [rapor],
  );

  // Filtre yalnizca GORUNURLUGU degistirir; kontroller her zaman calisir.
  const gorunenChecks = React.useMemo(
    () =>
      rapor
        ? yalnizDusenler
          ? rapor.checks.filter((c) => !c.ok)
          : rapor.checks
        : [],
    [rapor, yalnizDusenler],
  );

  const onbellek = rapor?.summary.onbellek;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-[30px] italic leading-tight">
            Sistem sağlığı
          </h1>
          <p className="mt-1 max-w-2xl text-[13.5px] leading-relaxed text-muted-foreground">
            Motorun değişmezleri (invariant). Bunlar testten farklıdır: çalışan
            sürümün kolon üretimini, olasılık hattını ve veri katmanını gerçekten
            koruduğunu her çağrıda yeniden doğrular.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div
            role="group"
            aria-label="Otomatik yenileme aralığı"
            className="flex items-center gap-1 rounded-xl border border-line bg-elevated p-1"
          >
            <span className="px-1.5 text-[11px] text-muted-foreground">Oto</span>
            {ARALIKLAR.map((a) => (
              <button
                key={a}
                type="button"
                aria-pressed={aralik === a}
                onClick={() => setAralik(a)}
                className={cn(
                  "rounded-lg px-2 py-1 text-[11.5px] font-medium transition-colors duration-200",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60",
                  aralik === a
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted",
                )}
              >
                {ARALIK_ETIKET[a]}
              </button>
            ))}
          </div>

          <Button
            tip="outline"
            boyut="sm"
            onClick={() => void yukle(null, { fresh: true })}
            disabled={yukleniyor}
          >
            <RefreshCw size={14} className={cn(yukleniyor && "animate-spin")} />
            Yeniden çalıştır
          </Button>
        </div>
      </header>

      {hata ? (
        <Callout ton="danger" baslik="Sağlık raporu alınamadı">
          {hata}
        </Callout>
      ) : null}

      {yukleniyor && !rapor ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : null}

      {rapor && durum ? (
        <>
          <Card
            className={cn(
              "overflow-hidden",
              durum === "saglikli" && "border-success/30",
              durum === "kisitli" && "border-warning/40",
              durum === "bozuk" && "border-danger/40",
            )}
          >
            {/*
              Otomatik yenilemede HEALTHY -> UNHEALTHY gecisi ekran okuyucuya
              sessizdi; durum karti artik canli bolge.
            */}
            <CardBody
              aria-live="polite"
              aria-atomic="true"
              className="flex flex-wrap items-center gap-5"
            >
              <span
                className={cn(
                  "grid h-14 w-14 shrink-0 place-items-center rounded-2xl",
                  durum === "saglikli" && "bg-success-soft text-success",
                  durum === "kisitli" && "bg-warning-soft text-warning",
                  durum === "bozuk" && "bg-danger-soft text-danger",
                )}
              >
                <DurumIkonu durum={durum} />
              </span>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[19px] font-semibold tracking-tight">
                    {DURUM_METNI[durum]}
                  </span>
                  <Badge ton={ton}>
                    {rapor.passed}/{rapor.total} geçti
                  </Badge>
                  <Badge>v{rapor.version}</Badge>
                  <Badge>{sure(rapor.duration_ms)}</Badge>
                  <Badge ton={rapor.summary.has_scipy ? "primary" : "warning"}>
                    scipy {rapor.summary.has_scipy ? "var" : "yok"}
                  </Badge>
                  {onbellek?.cached ? (
                    <Badge
                      ton="neutral"
                      title={`Sunucudaki ${onbellek.ttl_s} sn'lik önbellekten geldi; ölçüm ${Math.round(
                        onbellek.yas_ms,
                      )} ms önce yapıldı. “Yeniden çalıştır” önbelleği atlar.`}
                    >
                      önbellekten
                    </Badge>
                  ) : null}
                </div>
                <p className="tnum mt-1 text-[12px] text-muted-foreground">
                  {goreliZaman(rapor.timestamp, simdi)}
                  {rapor.summary.ornek ? (
                    <>
                      {" · örnek "}
                      <span className="font-mono">
                        {rapor.summary.ornek.etiket ??
                          `${rapor.summary.ornek.host ?? "?"}#${rapor.summary.ornek.pid}`}
                      </span>
                    </>
                  ) : null}
                  {rapor.summary.slowest ? (
                    <>
                      {" · en yavaş: "}
                      <span className="font-mono">{rapor.summary.slowest.name}</span>{" "}
                      {sure(rapor.summary.slowest.duration_ms)}
                    </>
                  ) : null}
                </p>
              </div>

              <Button tip="ghost" boyut="sm" onClick={() => void kopyala()}>
                {kopyalandi ? <Check size={14} /> : <Copy size={14} />}
                {kopyalandi ? "Kopyalandı" : "JSON kopyala"}
              </Button>
            </CardBody>
          </Card>

          {rapor.summary.kismi ? (
            <Callout ton="primary" baslik="Kısmi çalıştırma">
              Bu rapor yalnızca{" "}
              <code className="font-mono">{rapor.summary.only}</code> kapsamını
              içeriyor — kayıtlı {rapor.summary.kayitli_kontrol} kontrolün{" "}
              {rapor.total} tanesi çalıştı.{" "}
              <button
                type="button"
                onClick={() => void yukle(null, { fresh: true })}
                className="font-semibold underline underline-offset-2"
              >
                Tam raporu çalıştır
              </button>
            </Callout>
          ) : null}

          {dusenler.length ? (
            <Callout
              ton={durum === "bozuk" ? "danger" : "warning"}
              baslik={`${dusenler.length} kontrol düştü`}
            >
              <ul className="space-y-1">
                {dusenler.map((c) => (
                  <li key={c.name}>
                    {/* Uzun rapordaki ilgili karta atlar: özetten teşhise
                        giden yol tek tık olmalı. */}
                    <a
                      href={`#${kategoriAnkraji(c.category)}`}
                      className="font-mono font-semibold underline decoration-dotted underline-offset-2"
                    >
                      {c.name}
                    </a>
                    {!c.critical ? " (bilgi) " : " "}— {c.aciklama}
                  </li>
                ))}
              </ul>
            </Callout>
          ) : null}

          {yavaslar.length ? (
            <Callout
              ton="warning"
              baslik={`${yavaslar.length} kontrol süre bütçesini aştı`}
            >
              Bu kontroller <strong>düşmedi</strong>; değişmezler hâlâ geçerli,
              yalnızca beklenenden pahalıya koştular:{" "}
              <span className="font-mono">{yavaslar.join(", ")}</span>. Performans
              gerilemesi de bir gerilemedir — ama servisi durdurmaz.
            </Callout>
          ) : null}

          {durum === "kisitli" && !yavaslar.length ? (
            <Callout ton="warning" baslik="Yetenek eksik, servis ayakta">
              Kritik değişmezlerin tamamı geçti; düşenler bilgi amaçlı
              kontroller. Motor çalışır, yalnızca bir yeteneği devre dışıdır.
            </Callout>
          ) : null}

          {rapor.summary.isinma ? (
            <Callout ton="primary" baslik="Bu, sürecin ilk koşusu">
              İlk rapor numpy/scipy ilk import&apos;unu ve veri setinin ilk
              okunmasını da üstlenir; süreleri sonraki koşularla
              karşılaştırmayın. Süre bütçeleri bu koşuda <strong>uygulanmaz</strong>,
              yoksa her soğuk başlangıç yanlış alarm üretirdi.
            </Callout>
          ) : null}

          {!rapor.summary.has_scipy ? (
            <Callout ton="warning" baslik="scipy kurulu değil">
              Araç çalışır, yalnızca kesin çözücü (ILP) devre dışıdır —{" "}
              <strong>exact</strong> modu kullanılamaz.
            </Callout>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat etiket="Geçen" deger={rapor.passed} ton="success" />
            <Stat
              etiket="Kalan"
              deger={rapor.failed}
              ton={rapor.failed ? "danger" : "neutral"}
            />
            {/* "Kategori" sayısı hiç değişmiyordu; yerine raporu asıl
                yavaşlatan kontrol — performans gerilemesi de bir gerilemedir. */}
            <Stat
              etiket="En yavaş kontrol"
              deger={
                <span className="break-all font-mono text-[15px]">
                  {rapor.summary.slowest?.name ?? "—"}
                </span>
              }
              alt={
                rapor.summary.slowest
                  ? sure(rapor.summary.slowest.duration_ms)
                  : undefined
              }
            />
            <Stat etiket="Toplam süre" deger={sure(rapor.duration_ms)} />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-[13px] font-semibold uppercase tracking-[0.09em] text-muted-foreground">
              Değişmezler
            </h2>
            <button
              type="button"
              aria-pressed={yalnizDusenler}
              disabled={!dusenler.length}
              onClick={() => setYalnizDusenler((v) => !v)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11.5px] font-medium",
                "transition-colors duration-200 ease-smooth",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60",
                "disabled:pointer-events-none disabled:opacity-40",
                yalnizDusenler
                  ? "border-danger/40 bg-danger-soft text-danger"
                  : "border-line-strong hover:bg-muted",
              )}
            >
              <ListFilter size={13} />
              {yalnizDusenler ? "Tümünü göster" : "Yalnızca düşenler"}
            </button>
          </div>

          <div className="space-y-4">
            {rapor.categories.map((kat) => (
              <KategoriKarti
                key={kat.id}
                kategori={kat}
                checks={gorunenChecks.filter((c) => c.category === kat.id)}
                enUzunMs={enUzunMs}
                calisiyor={yukleniyor}
                onCalistir={(id) => void yukle(id, { fresh: true })}
              />
            ))}
          </div>

          <GecmisSeridi gecmis={gecmis} simdi={simdi} />
          <SunucuGecmisi gecmis={sunucuGecmisi} simdi={simdi} />
          <KuponDenetimi
            sonuc={kuponSonuc}
            hata={kuponHata}
            calisiyor={kuponCalisiyor}
            picks={kuponPicks}
            onPicks={setKuponPicks}
            onCalistir={() => void kuponuDenetle()}
          />
          <KontrolEnvanteri
            envanter={envanter?.checks ?? null}
            hata={envanterHatasi}
            yukleniyor={envanterYukleniyor}
          />
          <OrtamKarti rapor={rapor} />
        </>
      ) : null}
    </div>
  );
}
