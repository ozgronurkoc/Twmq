"use client";

import * as React from "react";
import { Eraser } from "lucide-react";

import {
  arsiveYaz,
  arsivdenSil,
  getArsivKaydi,
  getArsivListesi,
  getBenzer,
  getLigEnvanteri,
  getMeta,
} from "@/lib/api";
import { hataMetni, iptalMi } from "@/lib/istek";
import {
  bosKupon,
  kuponOzeti,
  kuponuYereldenOku,
  kayittanSatirlar,
  kuponuYereleYaz,
  oranSayilari,
  yereliTemizle,
  type KuponSatiri,
} from "@/lib/kupon";
import { kuponBedeli, kuponKur } from "@/lib/kupon-kur";
import {
  analizOzeti,
  analizdenKayit,
  analizeHazir,
  bosAnaliz,
  evreniOku,
  kayittanAnaliz,
  sorguIzi,
  taninmayanLigler,
  VARSAYILAN_ANALIZ,
  type AnalizAyari,
  type SatirAnalizi,
} from "@/lib/kupon-analiz";
import {
  CIZGILER,
  MAC_SAYISI,
  type ArsivOzeti,
  type BenzerResponse,
  type LigEnvanteriSatiri,
  type Cizgi,
  type Sembol,
} from "@/lib/types";
import { yuzde } from "@/lib/utils";
import { Badge, Button, Callout, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { KuponIzgarasi } from "@/components/kupon/izgara";
import { AnalizAyarlari } from "@/components/kupon/ayarlar";
import { AnalizTablosu, TabloAciklamasi } from "@/components/kupon/analiz-tablosu";
import { KuponArsivi } from "@/components/kupon/kupon-arsivi";
import {
  KuponAciklamasi,
  KuponMuhasebesi,
  KuponTablosu,
} from "@/components/kupon/kupon-tablosu";

/**
 * Kupon kurucu — **1. aşama: giriş**.
 *
 * Bu sayfanin tamamlanmis hali su zinciri kuracak:
 *
 *   elle 15 satir  →  satir basina `/api/benzer` sorgusu (tum ligler)
 *                  →  olasilik  →  isaret secimi  →  kupon
 *
 * Su an yalnizca ILK halka var ve bu bilerek boyle: girdinin sekli
 * (hangi alanlar, hangi dogrulama, neyin kalici oldugu) sonraki halkalarin
 * hepsini belirliyor. Once o sekil elle denenir, sonra uzerine sorgu
 * baglanir.
 *
 * ─── Neden `/oran-analizi`nin bir kopyasi degil ───────────────────────────
 *
 * `/oran-analizi` TEK macin sorgu aracidir ve oyle kalmali: orada soru
 * "bu fiyatta ne oldu", cevabin yaninda lig kirilimi ve maclarin kendisi
 * durur. Burada soru "bu 15 macla hangi kupon" — yani girdi bir tablo,
 * cikti bir plan. Ayni motoru cagiracaklar ama ayni ekran degiller.
 *
 * ─── Neden hicbir sey otomatik doldurulmuyor ──────────────────────────────
 *
 * Depo 5. haftanin maclarini ve Pinnacle oranlarini zaten tasiyor
 * (`backend/data/super_toto/2026_27/hafta_05.json`). Yine de bu tablo bos
 * aciliyor: girilecek oranlar iddaa bulteninden gelecek ve o fiyat
 * Pinnacle'inkiyle ayni degil. Hazir doldurulmus bir tablo, kullanicinin
 * kendi bulteni yerine baska bir bultenle calistigini gizlerdi.
 */
export default function KuponSayfasi() {
  const [satirlar, setSatirlar] = React.useState<KuponSatiri[]>(bosKupon);
  // Yerel kayit ANCAK okunduktan sonra yazilir: ilk render'daki bos tablo
  // depodaki dolu tabloyu ezmesin.
  const [okundu, setOkundu] = React.useState(false);
  const [ayar, setAyar] = React.useState<AnalizAyari>(VARSAYILAN_ANALIZ);
  const [sonuclar, setSonuclar] = React.useState<SatirAnalizi[]>(() =>
    bosAnaliz(MAC_SAYISI),
  );
  const [kosuyor, setKosuyor] = React.useState(false);
  /**
   * Ekrandaki sonucun ait oldugu sorgu. Girdi ya da ayar degisince bu iz
   * tutmaz ve sayfa "sonuc bayat" der — eski karneyi yeni oranin cevabi
   * gibi gostermek, sessizce yanlis kupon kurdurur.
   */
  const [kosanIz, setKosanIz] = React.useState<string | null>(null);
  const iptalci = React.useRef<AbortController | null>(null);

  // ─── Arsiv ─────────────────────────────────────────────────────────────
  const [ad, setAd] = React.useState("");
  /** Hafta ETIKETI; 0 = bos birakildi. Kimlik degil (bkz. kupon-arsivi). */
  const [hafta, setHafta] = React.useState(0);
  const [not, setNot] = React.useState("");
  const [kayitlar, setKayitlar] = React.useState<ArsivOzeti[]>([]);
  /** Ekrandaki kayit hangi numaradan acildi; `null` = henuz kaydedilmedi. */
  const [acikNo, setAcikNo] = React.useState<number | null>(null);
  /**
   * Kosulan analizin evreni — damganin yarisi ve UYDURULAMAZ: hangi
   * buyuklukteki korpusta olculdugunu ancak cevabin kendisi soyler.
   * Arsivden acilan kayitta kaydin kendi damgasindan gelir.
   */
  const [evren, setEvren] = React.useState<number | null>(null);
  /** Arsivden acilan analizin damgasi; canli kosumda `null`. */
  const [analizDamgasi, setAnalizDamgasi] = React.useState<string | null>(null);
  const [arsivKosuyor, setArsivKosuyor] = React.useState(false);
  const [arsivHata, setArsivHata] = React.useState<string | null>(null);
  const [kaydedildi, setKaydedildi] = React.useState<string | null>(null);

  /**
   * Kolon bedeli ve haftalik tavan SUNUCUDAN gelir, burada sabit yok
   * (`getiri.KOLON_BEDELI` ve `backtest.VARSAYILAN_BUTCE_TL`). Okunamazsa
   * kupon yine kurulur — yalnizca para satiri "—" kalir.
   */
  const [kolonBedeli, setKolonBedeli] = React.useState<number | null>(null);
  const [haftalikTavan, setHaftalikTavan] = React.useState<number | null>(null);
  /**
   * Korpusun lig envanteri. `null` = henuz okunmadi ve o haldeyken lig
   * DOGRULAMASI YAPILMAZ: olmayan bir listeye gore satir suclanamaz.
   * Cizgiye bagli (acilis evreni kapanistan kucuk), o yuzden cizgi
   * degisince yeniden okunur.
   */
  const [ligler, setLigler] = React.useState<LigEnvanteriSatiri[] | null>(null);

  React.useEffect(() => {
    let birakildi = false;
    getMeta()
      .then((m) => {
        if (birakildi) return;
        setKolonBedeli(m.kolon_bedeli_tl ?? null);
        setHaftalikTavan(m.backtest?.butce_default_tl ?? null);
      })
      .catch(() => {
        /* para satiri "—" kalir; kupon bundan bagimsiz kurulur */
      });
    return () => {
      birakildi = true;
    };
  }, []);

  React.useEffect(() => {
    const kontrol = new AbortController();
    getLigEnvanteri(ayar.cizgi, kontrol.signal)
      .then((e) => setLigler(e.ligler))
      .catch(() => {
        /* envanter okunamazsa lig dogrulamasi YAPILMAZ, sayfa calisir */
      });
    return () => kontrol.abort();
  }, [ayar.cizgi]);

  const listeyiTazele = React.useCallback(async () => {
    try {
      const liste = await getArsivListesi();
      setKayitlar(liste.kayitlar);
      return liste.kayitlar;
    } catch (e) {
      // Liste okunamamasi SAYFAYI dusurmez: tablo ve analiz arsivden
      // bagimsiz calisir. Hata gorunur durur, sessizce yutulmaz.
      setArsivHata(hataMetni(e, "Arşiv listesi okunamadı"));
      return [];
    }
  }, []);

  React.useEffect(() => {
    void listeyiTazele();
  }, [listeyiTazele]);

  React.useEffect(() => {
    const kayit = kuponuYereldenOku();
    if (kayit) setSatirlar(kayit);
    setOkundu(true);
  }, []);

  React.useEffect(() => {
    if (!okundu) return;
    kuponuYereleYaz(satirlar);
  }, [satirlar, okundu]);

  // Sayfadan cikilirken ucan sorgular birakilmaz.
  React.useEffect(() => () => iptalci.current?.abort(), []);

  function yaz(mac: number, alan: string, deger: string) {
    setSatirlar((onceki) =>
      onceki.map((satir, i) => {
        if (i !== mac) return satir;
        if (alan === "lig" || alan === "ev" || alan === "dep") {
          return { ...satir, [alan]: deger };
        }
        return { ...satir, oran: { ...satir.oran, [alan as Sembol]: deger } };
      }),
    );
  }

  function temizle() {
    iptalci.current?.abort();
    setSatirlar(bosKupon());
    setSonuclar(bosAnaliz(MAC_SAYISI));
    setKosanIz(null);
    setKosuyor(false);
    setAcikNo(null);
    setKaydedildi(null);
    setEvren(null);
    setAnalizDamgasi(null);
    yereliTemizle();
  }

  /**
   * 15 satiri AYNI ayarla arar.
   *
   * ─── Neden 15 ayri istek, neden toplu bir uc degil ──────────────────────
   *
   * `/api/benzer` zaten var, onbellekli (`lru_cache`) ve tek maclik sorgusu
   * `/oran-analizi` ile BIREBIR ayni — yani buradaki cevap orada acilanla
   * ayni cevap olmak zorunda ve ayni ucu cagirmak bunu tanim geregi saglar.
   * Toplu bir uc, ayrisabilecek ikinci bir yol acardi. Olculmeden eklenmez:
   * once bu halin suresi olculur.
   *
   * ─── Neden satir satir yaziliyor ────────────────────────────────────────
   *
   * `Promise.all` toplu beklenip tek seferde yazilsaydi ekran 15 sorgu
   * boyunca olu dururdu. Her cevap geldigi anda kendi satirina yaziliyor;
   * tablo doldukca doluyor.
   */
  async function analizEt() {
    if (!analizeHazir(satirlar, ayar)) return;
    iptalci.current?.abort();
    const kontrol = new AbortController();
    iptalci.current = kontrol;

    const iz = sorguIzi(satirlar, ayar);
    setKosuyor(true);
    setKosanIz(iz);
    setSonuclar(satirlar.map(() => ({ durum: "kosuyor", veri: null, hata: null })));

    const yazSatir = (i: number, sonuc: SatirAnalizi) =>
      setSonuclar((onceki) => onceki.map((s, j) => (j === i ? sonuc : s)));

    // Evren cevabin KENDISINDEN okunur, sabit yazilmaz: korpus buyudukce
    // degisir ve kaydin damgasinin yarisi odur.
    const hamCevaplar: (BenzerResponse | null)[] = Array(satirlar.length).fill(null);

    await Promise.all(
      satirlar.map(async (satir, i) => {
        try {
          const veri = await getBenzer(
            oranSayilari(satir),
            {
              cizgi: ayar.cizgi,
              arindirma: ayar.arindirma,
              en_az: ayar.enAz,
              // Kapsam `tum` iken lig suzgeci HIC gonderilmez; `kendi`
              // iken satirin kendi kodu gider. Kod bos ya da taninmiyorsa
              // buraya hic gelinmez (`analizeHazir` engelliyor).
              ...(ayar.kapsam === "kendi" && satir.lig.trim()
                ? { lig: satir.lig.trim().toUpperCase() }
                : {}),
              ...(ayar.tarih ? { tarih: ayar.tarih } : {}),
            },
            kontrol.signal,
          );
          if (kontrol.signal.aborted) return;
          hamCevaplar[i] = veri;
          yazSatir(i, { durum: "bitti", veri, hata: null });
        } catch (e) {
          // Iptal bir hata DEGILDIR (`lib/istek` doktrini): durum hic
          // guncellenmez, cunku yerine yeni bir kosum gecmistir.
          if (iptalMi(e, kontrol.signal)) return;
          yazSatir(i, {
            durum: "hata",
            veri: null,
            hata: hataMetni(e, "Sorgu başarısız"),
          });
        }
      }),
    );

    if (!kontrol.signal.aborted) {
      setKosuyor(false);
      setEvren(evreniOku(hamCevaplar));
      // Canli kosum kaydin damgasini TASIMAZ: damga yazilirken atilir.
      setAnalizDamgasi(null);
    }
  }

  /**
   * Kuponu arsive yazar — ZINCIRIN TAMAMIYLA.
   *
   * Gonderilen sey girdi · ayar · analiz · kupon. Analiz de gidiyor ve bu
   * ILK SURUMDEKI KARARIN TERSI: orada karne bilerek atiliyordu ("turetilmis
   * veri bayatlar"). Teshis dogruydu, care yanlisti — kupon o analizden
   * cikiyor, analiz atilirsa kayit kendi kararinin gerekcesini kaybeder.
   * Bayatlamanin caresi atmak degil DAMGALAMAK: `analiz.olculdu` ve
   * `analiz.evren` kayitla birlikte gidiyor (`spor_toto/kupon_arsivi.py`).
   *
   * `yeniOlarak` ise numara GONDERILMEZ ve sunucu yeni bir kupon acar.
   * Ayrim burada, cunku "kaydet" ile "yeni kupon olarak kaydet" iki ayri
   * niyet ve ikisini de bir dugmenin tahmin etmesi gerekmiyor.
   */
  async function arsiveKaydet(yeniOlarak = false) {
    setArsivKosuyor(true);
    setArsivHata(null);
    try {
      const kayit = await arsiveYaz({
        ad,
        no: yeniOlarak ? null : acikNo,
        // 0 "bos birakildi" demek; sunucu `null` bekliyor.
        hafta: hafta > 0 ? hafta : null,
        not,
        ayar: {
          cizgi: ayar.cizgi,
          arindirma: ayar.arindirma,
          en_az: ayar.enAz,
          tarih: ayar.tarih,
          kapsam: ayar.kapsam,
        },
        satirlar: satirlar.map((s) => ({
          lig: s.lig,
          ev: s.ev,
          dep: s.dep,
          oran: { ...s.oran },
        })),
        // Bayat bir analiz KAYDEDILMEZ: ekrandaki karne su anki girdiye ait
        // degilse onu kuponun gerekcesi diye yazmak, kaydi yalanci yapar.
        analiz: bayat ? null : analizdenKayit(sonuclar, evren),
        // Kupon, ekrandaki analizden kurulan isaretler. Bayat analizden
        // kupon kurulmadigi icin bu alan da o durumda `null` gider: kaydin
        // "neden bu isaretler" zinciri yalanci olmamali.
        kupon: kuponGecerli && kupon ? { isaretler: kupon.satirlar.map((x) => x.semboller) } : null,
      });
      setAcikNo(kayit.no);
      setAd(kayit.ad);
      setKaydedildi(kayit.guncellendi.slice(11, 16));
      if (kayit.analiz) setAnalizDamgasi(kayit.analiz.olculdu);
      await listeyiTazele();
    } catch (e) {
      setArsivHata(hataMetni(e, "Kaydedilemedi"));
    } finally {
      setArsivKosuyor(false);
    }
  }

  /**
   * Kayitli bir kuponu ekrana yukler — DORDUNU birden.
   *
   * Girdi, ayar, analiz ve (kurulunca) kupon geri gelir. Analiz kaydin
   * kendi damgasiyla gelir ve ekranda o damga gorunur: bugunun korpusunda
   * ayni sorgu baska bir cevap verebilir ve bunu gizlemek, kaydi bugunun
   * cevabi gibi okutmak olurdu.
   */
  async function arsivdenAc(no: number) {
    setArsivKosuyor(true);
    setArsivHata(null);
    try {
      const kayit = await getArsivKaydi(no);
      iptalci.current?.abort();
      const yeniAyar: AnalizAyari = {
        cizgi: (CIZGILER as readonly string[]).includes(kayit.ayar.cizgi)
          ? (kayit.ayar.cizgi as Cizgi)
          : VARSAYILAN_ANALIZ.cizgi,
        arindirma: kayit.ayar.arindirma as AnalizAyari["arindirma"],
        enAz: kayit.ayar.en_az,
        tarih: kayit.ayar.tarih ?? "",
        // Eski kayitlarda alan yoktu; `tum` sunucunun da varsayilani.
        kapsam: kayit.ayar.kapsam === "kendi" ? "kendi" : "tum",
      };
      const yeniSatirlar = kayittanSatirlar(kayit.satirlar);
      setSatirlar(yeniSatirlar);
      setAyar(yeniAyar);
      setAd(kayit.ad);
      setNot(kayit.not ?? "");
      setHafta(kayit.hafta ?? 0);
      setAcikNo(kayit.no);
      setKaydedildi(null);
      setKosuyor(false);

      setSonuclar(kayittanAnaliz(kayit.analiz));
      setEvren(kayit.analiz?.evren ?? null);
      setAnalizDamgasi(kayit.analiz?.olculdu ?? null);
      // Iz, kaydin KENDI girdisi ve ayariyla kurulur: acilan analiz bu
      // ikisine aittir ve sayfa onu "bayat" diye isaretlememeli. Analiz
      // yoksa iz de yok — sonuc bolumu hic acilmaz.
      setKosanIz(kayit.analiz ? sorguIzi(yeniSatirlar, yeniAyar) : null);
    } catch (e) {
      setArsivHata(hataMetni(e, "Kayıt açılamadı"));
    } finally {
      setArsivKosuyor(false);
    }
  }

  async function arsivdenKaldir(no: number) {
    setArsivKosuyor(true);
    setArsivHata(null);
    try {
      await arsivdenSil(no);
      // Acik kayit silindiyse ekrandaki tablo artik bir KAYDA ait degil;
      // "uzerine yaz" dugmesi olmayan bir numarayi gostermemeli.
      if (acikNo === no) setAcikNo(null);
      await listeyiTazele();
    } catch (e) {
      setArsivHata(hataMetni(e, "Silinemedi"));
    } finally {
      setArsivKosuyor(false);
    }
  }

  const ozet = kuponOzeti(satirlar);
  const analiz = analizOzeti(sonuclar);
  const bilinenKodlar = React.useMemo(
    () => (ligler ? new Set(ligler.map((l) => l.lig.toUpperCase())) : null),
    [ligler],
  );
  const taninmayan = taninmayanLigler(satirlar, ayar, bilinenKodlar);
  const hazir = analizeHazir(satirlar, ayar, bilinenKodlar);
  const suankiIz = sorguIzi(satirlar, ayar);
  const bayat = kosanIz != null && kosanIz !== suankiIz;
  const sonucVar = kosanIz != null;
  const doluMu = satirlar.some(
    (s) => s.lig || s.ev || s.dep || s.oran["1"] || s.oran["0"] || s.oran["2"],
  );

  /**
   * Kupon, ekrandaki analizden KURULUR — ayri bir sorgu atilmaz.
   *
   * Bayat bir analizden kupon kurulmaz: ekrandaki karne su anki girdiye
   * ait degilse ondan cikan isaretler de degildir. Ayni gerekce kaydetmede
   * de gecerli (`arsiveKaydet` bayat analizi yazmiyor).
   */
  const kupon = React.useMemo(
    () => (sonucVar && !bayat && analiz.biten > 0 ? kuponKur(sonuclar) : null),
    [sonucVar, bayat, analiz.biten, sonuclar],
  );
  const kuponGecerli = !!kupon && kupon.eksik.length === 0;
  const bedel = kupon ? kuponBedeli(kupon.kolon, kolonBedeli) : null;

  return (
    <div className="mx-auto w-full max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Kupon Kurucu</h1>
        <p className="mt-1 max-w-[68ch] text-[13px] leading-relaxed text-muted-foreground">
          Haftanın 15 maçını ve elinizdeki bültenin 1 / 0 / 2 oranlarını buraya
          yazın. Bu tablo zincirin <strong>ilk halkası</strong>: sonraki
          aşamada her satır kendi oranıyla tüm liglerin korpusunda aranacak,
          çıkan karneden olasılık üretilecek ve işaretler seçilecek.
        </p>
      </div>

      <Card>
        <CardHeader
          title="Maçlar ve oranlar"
          hint="Tab satır boyunca, ok tuşları ve Enter sütun boyunca ilerler — bülten sütun sütun okunur."
          action={
            <Button tip="ghost" boyut="sm" onClick={temizle} disabled={!doluMu}>
              <Eraser size={14} />
              Tabloyu temizle
            </Button>
          }
        />
        <CardBody className="space-y-4">
          <KuponIzgarasi satirlar={satirlar} onChange={yaz} />

          <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
            <Badge ton={ozet.adliMac === MAC_SAYISI ? "success" : "neutral"}>
              {ozet.adliMac}/{MAC_SAYISI} maç adı
            </Badge>
            <Badge ton={ozet.sorguyaHazir ? "success" : "neutral"}>
              {ozet.oranliMac}/{MAC_SAYISI} oran tam
            </Badge>
            {ozet.ortalamaMarj != null ? (
              <Badge ton={ozet.ortalamaMarj > 0.12 ? "warning" : "neutral"}>
                ortalama marj {yuzde(ozet.ortalamaMarj)}
              </Badge>
            ) : null}
            {doluMu ? (
              <span className="text-[11.5px] text-muted-foreground">
                Tablo tarayıcıya kaydedildi — yenileme kaybettirmez.
              </span>
            ) : null}
          </div>
        </CardBody>
      </Card>

      {ozet.bozukSatirlar.length ? (
        <Callout ton="danger" baslik="Okunamayan oran">
          {ozet.bozukSatirlar.map((i) => i + 1).join(", ")}. satırda 1,00&apos;den
          büyük bir sayı olmayan hücre var. Oran her zaman ondalık yazılır;
          virgül otomatik noktaya çevrilir.
        </Callout>
      ) : null}

      {ozet.eksikOranlar.length ? (
        <Callout ton="warning" baslik="Oranı yarım kalan satır">
          {ozet.eksikOranlar.map((i) => i + 1).join(", ")}. satırda veri var ama
          üç oranın hepsi girilmemiş. Arama <strong>olasılık uzayında</strong>
          {" "}yapılır; bunun için üç oran birden gerekir — ikisi marjı
          belirlemeye yetmez.
        </Callout>
      ) : null}

      <Card>
        <CardHeader
          title="Kupon arşivi"
          hint={
            acikNo
              ? `Ekranda #${acikNo} açık — kaydet üstüne yazar, "yeni kupon olarak kaydet" ayrı bir deneme açar.`
              : "Bir kupon = maçlar + oranlar + analiz + işaretler. Kayıt sunucuda dosya olarak durur, git'e girebilir."
          }
        />
        <CardBody>
          <KuponArsivi
            ad={ad}
            onAdChange={(v) => {
              setAd(v);
              setKaydedildi(null);
            }}
            hafta={hafta}
            onHaftaChange={(v) => {
              setHafta(v);
              setKaydedildi(null);
            }}
            not={not}
            onNotChange={(v) => {
              setNot(v);
              setKaydedildi(null);
            }}
            kayitlar={kayitlar}
            acikNo={acikNo}
            kosuyor={arsivKosuyor}
            hata={arsivHata}
            onKaydet={() => arsiveKaydet(false)}
            onYeniOlarakKaydet={() => arsiveKaydet(true)}
            onAc={arsivdenAc}
            onSil={arsivdenKaldir}
            kaydedildi={kaydedildi}
            analizVar={!bayat && analiz.biten > 0}
            kuponVar={kuponGecerli}
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Analiz ayarları"
          hint={
            ayar.kapsam === "kendi"
              ? "15 satırın tamamı bu ayarla, HER MAÇ KENDİ LİGİNDE aranır."
              : "15 satırın tamamı bu ayarla, tüm liglerin korpusunda aranır — lig süzgeci yok."
          }
        />
        <CardBody>
          <AnalizAyarlari
            ayar={ayar}
            onChange={setAyar}
            onAnaliz={analizEt}
            hazir={hazir}
            kosuyor={kosuyor}
            ortalamaMarj={ozet.ortalamaMarj}
            bayat={bayat}
            ligler={ligler}
            taninmayan={taninmayan}
          />
        </CardBody>
      </Card>

      {sonucVar ? (
        <Card>
          <CardHeader
            title={ayar.kapsam === "kendi" ? "Karne — maçın kendi liginde" : "Karne — tüm ligler"}
            hint={
              kosuyor
                ? `${analiz.biten + analiz.hatali}/${MAC_SAYISI} satır tamamlandı…`
                : [
                    `${ayar.cizgi === "acilis" ? "Açılış" : "Kapanış"} çizgisi`,
                    `${ayar.arindirma} arındırma`,
                    ayar.tarih ? `${ayar.tarih} öncesi` : null,
                    // Arsivden acilan analiz KENDI gununun cevabidir; bugunun
                    // korpusunda ayni sorgu baska sayi verebilir ve bunu
                    // gizlemek kaydi bugunun cevabi gibi okutmak olurdu.
                    analizDamgasi
                      ? `kayıttan: ${analizDamgasi.slice(0, 10)} ölçüldü${evren ? `, ${evren.toLocaleString("tr-TR")} maçlık evren` : ""}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
            }
          />
          <CardBody className="space-y-4">
            <AnalizTablosu satirlar={satirlar} sonuclar={sonuclar} ayar={ayar} />
            <div className="space-y-3 border-t border-line pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge ton={analiz.hatali ? "danger" : "neutral"}>
                  {analiz.biten}/{MAC_SAYISI} satır
                  {analiz.hatali ? ` · ${analiz.hatali} hata` : ""}
                </Badge>
                <Badge ton={analiz.sapan.length ? "primary" : "neutral"}>
                  {analiz.sapan.length} satırda piyasa aralık dışında
                </Badge>
                {analiz.azOrnek.length ? (
                  <Badge ton="warning">
                    {analiz.azOrnek.length} satırda az örneklem
                  </Badge>
                ) : null}
                {analiz.tavanaDayanan.length ? (
                  <Badge ton="warning">
                    {analiz.tavanaDayanan.length} satırda yarıçap tavanda
                  </Badge>
                ) : null}
              </div>
              <TabloAciklamasi sapanVar={analiz.sapan.length > 0} />
            </div>
          </CardBody>
        </Card>
      ) : null}

      {kupon ? (
        <Card>
          <CardHeader
            title="Kupon"
            hint="Her maçta karnenin en yüksek iki sembolü işaretlenir — kural bu, seçim elle değiştirilmiyor."
          />
          <CardBody className="space-y-4">
            <KuponMuhasebesi
              kupon={kupon}
              bedelTl={bedel}
              haftalikTavanTl={haftalikTavan}
            />
            {bedel != null && haftalikTavan != null && bedel > haftalikTavan ? (
              <Callout ton="warning" baslik="Bedel haftalık tavanı aşıyor">
                Kural her maça iki sembol verdiği için kolon sayısı{" "}
                <strong>girdiden bağımsız olarak</strong> 2¹⁵ çıkıyor:{" "}
                {(bedel / haftalikTavan).toFixed(2)}× tavan. Aşımı kapatmanın
                tek yolu bazı maçları <strong>banko</strong> (tek sembol)
                yapmaktır — hangi maçların bankolaşacağı henüz karara
                bağlanmadı.
              </Callout>
            ) : null}
            <KuponTablosu satirlar={satirlar} kupon={kupon} />
            <div className="border-t border-line pt-4">
              <KuponAciklamasi kupon={kupon} />
            </div>
          </CardBody>
        </Card>
      ) : null}

      <Callout ton={sonucVar && analiz.tamam ? "success" : "neutral"} baslik="Sıradaki aşama">
        {kuponGecerli ? (
          <>
            Kupon kuruldu ve arşive kaydedilebilir. Açık kalan tek soru{" "}
            <strong>bütçe</strong>: kural her maça iki sembol verdiği için
            kolon sayısı sabit 2¹⁵ ve bu haftalık tavanın üstünde. Bazı
            maçları bankoya indirmenin kuralı henüz karara bağlanmadı.
          </>
        ) : sonucVar && analiz.tamam ? (
          <>
            Karne çıktı ama kupon kurulamadı — işaretsiz kalan satır var.
          </>
        ) : ozet.sorguyaHazir ? (
          <>
            15 satırın da oranı tam. Üstteki ayarlarla{" "}
            <strong>tüm liglerin korpusunda</strong> aratabilirsiniz.
          </>
        ) : (
          <>
            Tabloyu doldurun. Sorgu, <strong>15 satırın da</strong> oranı tam
            olduğunda kurulabilir — eksik satır kuponun o maçını körleştirir.
          </>
        )}
      </Callout>
    </div>
  );
}
