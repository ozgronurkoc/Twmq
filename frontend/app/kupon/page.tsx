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
  CIZGI_ADI,
  CIZGI_SIRASI,
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
import { SEKILLER, sekilliKuponKur } from "@/lib/kupon-sekil";
import {
  analizOzeti,
  analizdenKayit,
  bosAnaliz,
  evreniOku,
  hazirCizgiler,
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
import { sayi, yuzde } from "@/lib/utils";
import { Badge, Button, Callout, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { KuponIzgarasi } from "@/components/kupon/izgara";
import { AnalizAyarlari } from "@/components/kupon/ayarlar";
import { AnalizTablosu, TabloAciklamasi } from "@/components/kupon/analiz-tablosu";
import { KuponArsivi } from "@/components/kupon/kupon-arsivi";
import {
  SekilAciklamasi,
  SekilliKuponlar,
  type KuponGirdisi,
} from "@/components/kupon/sekilli-kuponlar";
import {
  KuponAciklamasi,
  KuponMuhasebesi,
  KuponTablosu,
} from "@/components/kupon/kupon-tablosu";

/**
 * Kupon kurucu.
 *
 * Zincir:
 *
 *   elle 15 satir, ACILIS ve KAPANIS orani
 *     -> her cizgi kendi orani ve kendi korpus cizgisiyle araniyor
 *     -> cizgi basina karne
 *     -> isaret secimi  ->  kuponlar
 *
 * ─── Neden iki cizgi, neden dort kupon ────────────────────────────────────
 *
 * Sahibinin istegi: *"acilis ve kapanis oranlarini verdigimde 6 banko 9
 * uclu ve 5 banko 5 cift 5 uclu seklinde 2 ayri kupon olusacak. (Acilis
 * kendi icinde 2 kupon, kapanis kendi icinde 2 kupon olacak.)"*
 *
 * Yani sayfa artik iki fiyat okuyor ve alti kupon gosteriyor: cizgi basina
 * bir IKILI kupon (her maca en yuksek iki sembol — onceki kural, oldugu
 * gibi duruyor) ve iki SEKILLI kupon (`lib/kupon-sekil.ts`).
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

/** Cizgi basina tutulan bir deger — analiz durumunun tamami boyle tutulur. */
type CizgiBasina<T> = Record<Cizgi, T>;

function cizgiBasina<T>(uret: (c: Cizgi) => T): CizgiBasina<T> {
  return { acilis: uret("acilis"), kapanis: uret("kapanis") };
}

export default function KuponSayfasi() {
  const [satirlar, setSatirlar] = React.useState<KuponSatiri[]>(bosKupon);
  // Yerel kayit ANCAK okunduktan sonra yazilir: ilk render'daki bos tablo
  // depodaki dolu tabloyu ezmesin.
  const [okundu, setOkundu] = React.useState(false);
  const [ayar, setAyar] = React.useState<AnalizAyari>(VARSAYILAN_ANALIZ);
  /**
   * Cizgi basina karne. Iki cizgi AYRI sorgudur (ayri fiyat, ayri korpus
   * cizgisi) ve tek bir dizide tutulsalardi ekranda cizgi degistirmek
   * otekinin cevabini silerdi.
   */
  const [sonuclar, setSonuclar] = React.useState<CizgiBasina<SatirAnalizi[]>>(() =>
    cizgiBasina(() => bosAnaliz(MAC_SAYISI)),
  );
  const [kosuyor, setKosuyor] = React.useState(false);
  /**
   * Ekrandaki sonucun ait oldugu sorgu. Girdi ya da ayar degisince bu iz
   * tutmaz ve sayfa "sonuc bayat" der — eski karneyi yeni oranin cevabi
   * gibi gostermek, sessizce yanlis kupon kurdurur.
   */
  const [kosanIz, setKosanIz] = React.useState<CizgiBasina<string | null>>(() =>
    cizgiBasina(() => null),
  );
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
  const [evren, setEvren] = React.useState<CizgiBasina<number | null>>(() =>
    cizgiBasina(() => null),
  );
  /** Arsivden acilan analizin damgasi; canli kosumda `null`. */
  const [analizDamgasi, setAnalizDamgasi] = React.useState<CizgiBasina<string | null>>(
    () => cizgiBasina(() => null),
  );
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

  function yazKimlik(mac: number, alan: "lig" | "ev" | "dep", deger: string) {
    setSatirlar((onceki) =>
      onceki.map((satir, i) => (i === mac ? { ...satir, [alan]: deger } : satir)),
    );
  }

  function yazOran(mac: number, cizgi: Cizgi, sembol: Sembol, deger: string) {
    setSatirlar((onceki) =>
      onceki.map((satir, i) =>
        i === mac
          ? {
              ...satir,
              oran: { ...satir.oran, [cizgi]: { ...satir.oran[cizgi], [sembol]: deger } },
            }
          : satir,
      ),
    );
  }

  function temizle() {
    iptalci.current?.abort();
    setSatirlar(bosKupon());
    setSonuclar(cizgiBasina(() => bosAnaliz(MAC_SAYISI)));
    setKosanIz(cizgiBasina(() => null));
    setKosuyor(false);
    setAcikNo(null);
    setKaydedildi(null);
    setEvren(cizgiBasina(() => null));
    setAnalizDamgasi(cizgiBasina(() => null));
    yereliTemizle();
  }

  /**
   * Orani TAM olan her cizgiyi, 15 satirin tamamiyla arar.
   *
   * ─── Neden 15 ayri istek, neden toplu bir uc degil ──────────────────────
   *
   * `/api/benzer` zaten var, onbellekli (`lru_cache`) ve tek maclik sorgusu
   * `/oran-analizi` ile BIREBIR ayni — yani buradaki cevap orada acilanla
   * ayni cevap olmak zorunda ve ayni ucu cagirmak bunu tanim geregi saglar.
   * Toplu bir uc, ayrisabilecek ikinci bir yol acardi. Olculmeden eklenmez:
   * once bu halin suresi olculur.
   *
   * ─── Neden iki cizgi TEK dugmede ────────────────────────────────────────
   *
   * Ayri dugmeler olsaydi, dort kuponun ikisi bir oranin, ikisi baska bir
   * anin cevabindan cikabilirdi. Kosum hazir olan HER cizgiyi birlikte
   * tazeler; bir cizginin orani yarimsa o cizgi atlanir ve kuponlari
   * kurulmaz.
   *
   * ─── Neden satir satir yaziliyor ────────────────────────────────────────
   *
   * `Promise.all` toplu beklenip tek seferde yazilsaydi ekran sorgular
   * boyunca olu dururdu. Her cevap geldigi anda kendi satirina yaziliyor;
   * tablo doldukca doluyor.
   */
  async function analizEt() {
    const cizgiler = hazirCizgiler(satirlar, ayar, bilinenKodlar);
    if (!cizgiler.length) return;
    iptalci.current?.abort();
    const kontrol = new AbortController();
    iptalci.current = kontrol;

    setKosuyor(true);
    setKosanIz((onceki) => {
      const yeni = { ...onceki };
      cizgiler.forEach((c) => {
        yeni[c] = sorguIzi(satirlar, ayar, c);
      });
      return yeni;
    });
    setSonuclar((onceki) => {
      const yeni = { ...onceki };
      cizgiler.forEach((c) => {
        yeni[c] = satirlar.map(() => ({ durum: "kosuyor", veri: null, hata: null }));
      });
      return yeni;
    });

    const yazSatir = (c: Cizgi, i: number, sonuc: SatirAnalizi) =>
      setSonuclar((onceki) => ({
        ...onceki,
        [c]: onceki[c].map((s, j) => (j === i ? sonuc : s)),
      }));

    // Evren cevabin KENDISINDEN okunur, sabit yazilmaz: korpus buyudukce
    // degisir ve kaydin damgasinin yarisi odur.
    const hamCevaplar = cizgiBasina<(BenzerResponse | null)[]>(() =>
      Array(satirlar.length).fill(null),
    );

    await Promise.all(
      cizgiler.flatMap((c) =>
        satirlar.map(async (satir, i) => {
          try {
            const veri = await getBenzer(
              oranSayilari(satir, c),
              {
                cizgi: c,
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
            hamCevaplar[c][i] = veri;
            yazSatir(c, i, { durum: "bitti", veri, hata: null });
          } catch (e) {
            // Iptal bir hata DEGILDIR (`lib/istek` doktrini): durum hic
            // guncellenmez, cunku yerine yeni bir kosum gecmistir.
            if (iptalMi(e, kontrol.signal)) return;
            yazSatir(c, i, {
              durum: "hata",
              veri: null,
              hata: hataMetni(e, "Sorgu başarısız"),
            });
          }
        }),
      ),
    );

    if (!kontrol.signal.aborted) {
      setKosuyor(false);
      setEvren((onceki) => {
        const yeni = { ...onceki };
        cizgiler.forEach((c) => {
          yeni[c] = evreniOku(hamCevaplar[c]);
        });
        return yeni;
      });
      // Canli kosum kaydin damgasini TASIMAZ: damga yazilirken atilir.
      setAnalizDamgasi((onceki) => {
        const yeni = { ...onceki };
        cizgiler.forEach((c) => {
          yeni[c] = null;
        });
        return yeni;
      });
    }
  }

  const bilinenKodlar = React.useMemo(
    () => (ligler ? new Set(ligler.map((l) => l.lig.toUpperCase())) : null),
    [ligler],
  );
  const ozetler = React.useMemo(
    () => cizgiBasina((c) => kuponOzeti(satirlar, c)),
    [satirlar],
  );
  const taninmayan = taninmayanLigler(satirlar, ayar, bilinenKodlar);
  const hazirlar = hazirCizgiler(satirlar, ayar, bilinenKodlar);
  const hazir = hazirlar.length > 0;
  /** Ekrandaki cizgi — karne tablosu ve ikili kupon bunu okur. */
  const cizgi = ayar.cizgi;
  const bayatlar = React.useMemo(
    () =>
      cizgiBasina(
        (c) => kosanIz[c] != null && kosanIz[c] !== sorguIzi(satirlar, ayar, c),
      ),
    [kosanIz, satirlar, ayar],
  );
  const analizler = React.useMemo(
    () => cizgiBasina((c) => analizOzeti(sonuclar[c])),
    [sonuclar],
  );
  const analiz = analizler[cizgi];
  const bayat = bayatlar[cizgi];
  const sonucVar = kosanIz[cizgi] != null;
  const doluMu = satirlar.some(
    (s) =>
      s.lig ||
      s.ev ||
      s.dep ||
      CIZGILER.some((c) => s.oran[c]["1"] || s.oran[c]["0"] || s.oran[c]["2"]),
  );

  /**
   * Kupon, ekrandaki analizden KURULUR — ayri bir sorgu atilmaz.
   *
   * Bayat bir analizden kupon kurulmaz: ekrandaki karne su anki girdiye
   * ait degilse ondan cikan isaretler de degildir. Ayni gerekce kaydetmede
   * de gecerli (`arsiveKaydet` bayat analizi yazmiyor).
   */
  const kupon = React.useMemo(
    () => (sonucVar && !bayat && analiz.biten > 0 ? kuponKur(sonuclar[cizgi]) : null),
    [sonucVar, bayat, analiz.biten, sonuclar, cizgi],
  );
  const kuponGecerli = !!kupon && kupon.eksik.length === 0;
  const bedel = kupon ? kuponBedeli(kupon.kolon, kolonBedeli) : null;

  /** Karnesi TAZE olan cizgiler — sekilli kuponlar yalnizca bunlardan cikar. */
  const tazeCizgiler = React.useMemo(
    () =>
      CIZGI_SIRASI.filter(
        (c) => kosanIz[c] != null && !bayatlar[c] && analizler[c].biten > 0,
      ),
    [kosanIz, bayatlar, analizler],
  );

  /**
   * Dort kupon: her taze cizgi icin iki sekil.
   *
   * Sira ekranda okunacak sira: once acilisin iki sekli, sonra kapanisin.
   * Sahibinin cumlesindeki gruplama bu ("acilis kendi icinde 2 kupon,
   * kapanis kendi icinde 2 kupon").
   */
  const sekilliler = React.useMemo<KuponGirdisi[]>(
    () =>
      tazeCizgiler.flatMap((c) =>
        SEKILLER.map((sekil) => ({
          cizgi: c,
          kupon: sekilliKuponKur(sonuclar[c], sekil),
          damga: analizDamgasi[c],
        })),
      ),
    [tazeCizgiler, sonuclar, analizDamgasi],
  );

  /**
   * Kuponu arsive yazar — ZINCIRIN TAMAMIYLA.
   *
   * Gonderilen sey girdi · ayar · analizler · kuponlar. Analiz de gidiyor ve
   * bu ILK SURUMDEKI KARARIN TERSI: orada karne bilerek atiliyordu
   * ("turetilmis veri bayatlar"). Teshis dogruydu, care yanlisti — kupon o
   * analizden cikiyor, analiz atilirsa kayit kendi kararinin gerekcesini
   * kaybeder. Bayatlamanin caresi atmak degil DAMGALAMAK: `analiz.olculdu`
   * ve `analiz.evren` kayitla birlikte gidiyor (`spor_toto/kupon_arsivi.py`).
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
          oran: { acilis: { ...s.oran.acilis }, kapanis: { ...s.oran.kapanis } },
        })),
        // Bayat bir analiz KAYDEDILMEZ: ekrandaki karne su anki girdiye ait
        // degilse onu kuponun gerekcesi diye yazmak, kaydi yalanci yapar.
        analizler: Object.fromEntries(
          CIZGILER.map((c) => [
            c,
            bayatlar[c] ? null : analizdenKayit(sonuclar[c], evren[c]),
          ]),
        ),
        // Ikili kupon, ekrandaki cizginin kuponu. Bayat analizden kupon
        // kurulmadigi icin bu alan o durumda `null` gider.
        kupon:
          kuponGecerli && kupon
            ? { isaretler: kupon.satirlar.map((x) => x.semboller) }
            : null,
        // Sekilli kuponlar yalnizca TAZE cizgilerden ve yalnizca eksiksiz
        // olanlar. Isaretsiz satiri olan bir kupon sunucuda zaten reddedilir.
        sekilli: sekilliler
          .filter((g) => g.kupon.eksik.length === 0)
          .map((g) => ({
            cizgi: g.cizgi,
            sekil: g.kupon.sekil.anahtar,
            isaretler: g.kupon.satirlar.map((x) => x.semboller),
          })),
      });
      setAcikNo(kayit.no);
      setAd(kayit.ad);
      setKaydedildi(kayit.guncellendi.slice(11, 16));
      setAnalizDamgasi(
        cizgiBasina((c) => kayit.analizler?.[c]?.olculdu ?? null),
      );
      await listeyiTazele();
    } catch (e) {
      setArsivHata(hataMetni(e, "Kaydedilemedi"));
    } finally {
      setArsivKosuyor(false);
    }
  }

  /**
   * Kayitli bir kuponu ekrana yukler — ZINCIRIN tamamiyla.
   *
   * Girdi, ayar, iki cizginin karnesi ve (kurulunca) kupon geri gelir.
   * Analiz kaydin kendi damgasiyla gelir ve ekranda o damga gorunur:
   * bugunun korpusunda ayni sorgu baska bir cevap verebilir ve bunu
   * gizlemek, kaydi bugunun cevabi gibi okutmak olurdu.
   *
   * Sekilli kuponlar kayittan CIZILMEZ, karneden yeniden kurulur: kayit
   * onlari tasiyor (denetim icin) ama ekranda gosterilen sey her zaman
   * ekrandaki karnenin sonucu olmali — ikisi ayrisirsa hangisinin dogru
   * oldugu sorusu dogar.
   */
  async function arsivdenAc(no: number) {
    setArsivKosuyor(true);
    setArsivHata(null);
    try {
      const kayit = await getArsivKaydi(no);
      iptalci.current?.abort();
      const kayitCizgisi: Cizgi = (CIZGILER as readonly string[]).includes(kayit.ayar.cizgi)
        ? (kayit.ayar.cizgi as Cizgi)
        : VARSAYILAN_ANALIZ.cizgi;
      const yeniAyar: AnalizAyari = {
        cizgi: kayitCizgisi,
        arindirma: kayit.ayar.arindirma as AnalizAyari["arindirma"],
        enAz: kayit.ayar.en_az,
        tarih: kayit.ayar.tarih ?? "",
        // Eski kayitlarda alan yoktu; `tum` sunucunun da varsayilani.
        kapsam: kayit.ayar.kapsam === "kendi" ? "kendi" : "tum",
      };
      const yeniSatirlar = kayittanSatirlar(kayit.satirlar, kayitCizgisi);
      setSatirlar(yeniSatirlar);
      setAyar(yeniAyar);
      setAd(kayit.ad);
      setNot(kayit.not ?? "");
      setHafta(kayit.hafta ?? 0);
      setAcikNo(kayit.no);
      setKaydedildi(null);
      setKosuyor(false);

      const kayitli = cizgiBasina((c) => kayit.analizler?.[c] ?? null);
      setSonuclar(cizgiBasina((c) => kayittanAnaliz(kayitli[c])));
      setEvren(cizgiBasina((c) => kayitli[c]?.evren ?? null));
      setAnalizDamgasi(cizgiBasina((c) => kayitli[c]?.olculdu ?? null));
      // Iz, kaydin KENDI girdisi ve ayariyla kurulur: acilan analiz bu
      // ikisine aittir ve sayfa onu "bayat" diye isaretlememeli. Analizi
      // olmayan cizginin izi de yok — o cizginin sonucu hic acilmaz.
      setKosanIz(
        cizgiBasina((c) => (kayitli[c] ? sorguIzi(yeniSatirlar, yeniAyar, c) : null)),
      );
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

  const bozukSatirlar = CIZGI_SIRASI.flatMap((c) =>
    ozetler[c].bozukSatirlar.map((i) => ({ cizgi: c, satir: i })),
  );
  const eksikOranlar = CIZGI_SIRASI.flatMap((c) =>
    ozetler[c].eksikOranlar.map((i) => ({ cizgi: c, satir: i })),
  );

  return (
    <div className="mx-auto w-full max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Kupon Kurucu</h1>
        <p className="mt-1 max-w-[68ch] text-[13px] leading-relaxed text-muted-foreground">
          Haftanın 15 maçını ve elinizdeki bültenin <strong>açılış</strong> ile{" "}
          <strong>kapanış</strong> 1 / 0 / 2 oranlarını buraya yazın. Her satır
          kendi oranıyla korpusun aynı çizgisinde aranır, çıkan karneden
          olasılık üretilir ve işaretler seçilir. Her çizgi kendi içinde{" "}
          <strong>iki şekilli kupon</strong> verir: 6 banko + 9 üçlü ve 5 banko
          + 5 çift + 5 üçlü.
        </p>
      </div>

      <Card>
        <CardHeader
          title="Maçlar ve oranlar"
          hint="Tab satır boyunca, ok tuşları ve Enter sütun boyunca ilerler — bülten sütun sütun okunur. Bir çizgi boş bırakılabilir; o çizginin kuponları kurulmaz."
          action={
            <Button tip="ghost" boyut="sm" onClick={temizle} disabled={!doluMu}>
              <Eraser size={14} />
              Tabloyu temizle
            </Button>
          }
        />
        <CardBody className="space-y-4">
          <KuponIzgarasi satirlar={satirlar} onKimlik={yazKimlik} onOran={yazOran} />

          <div className="space-y-2 border-t border-line pt-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge ton={ozetler.kapanis.adliMac === MAC_SAYISI ? "success" : "neutral"}>
                {ozetler.kapanis.adliMac}/{MAC_SAYISI} maç adı
              </Badge>
              {CIZGI_SIRASI.map((c) => (
                <React.Fragment key={c}>
                  <Badge ton={ozetler[c].sorguyaHazir ? "success" : "neutral"}>
                    {CIZGI_ADI[c]} {ozetler[c].oranliMac}/{MAC_SAYISI} oran tam
                  </Badge>
                  {ozetler[c].ortalamaMarj != null ? (
                    <Badge ton={ozetler[c].ortalamaMarj! > 0.12 ? "warning" : "neutral"}>
                      {CIZGI_ADI[c].toLocaleLowerCase("tr")} marj{" "}
                      {yuzde(ozetler[c].ortalamaMarj!)}
                    </Badge>
                  ) : null}
                </React.Fragment>
              ))}
            </div>
            {doluMu ? (
              <p className="text-[11.5px] text-muted-foreground">
                Tablo tarayıcıya kaydedildi — yenileme kaybettirmez.
              </p>
            ) : null}
          </div>
        </CardBody>
      </Card>

      {bozukSatirlar.length ? (
        <Callout ton="danger" baslik="Okunamayan oran">
          {bozukSatirlar
            .map((x) => `${x.satir + 1}. satır (${CIZGI_ADI[x.cizgi].toLocaleLowerCase("tr")})`)
            .join(", ")}{" "}
          — 1,00&apos;den büyük bir sayı olmayan hücre var. Oran her zaman
          ondalık yazılır; virgül otomatik noktaya çevrilir.
        </Callout>
      ) : null}

      {eksikOranlar.length ? (
        <Callout ton="warning" baslik="Oranı yarım kalan satır">
          {eksikOranlar
            .map((x) => `${x.satir + 1}. satır (${CIZGI_ADI[x.cizgi].toLocaleLowerCase("tr")})`)
            .join(", ")}{" "}
          — veri var ama üç oranın hepsi girilmemiş. Arama{" "}
          <strong>olasılık uzayında</strong> yapılır; bunun için üç oran birden
          gerekir — ikisi marjı belirlemeye yetmez. Bir çizgiyi tamamen boş
          bırakmak ise bir eksiklik değildir: o çizgi atlanır.
        </Callout>
      ) : null}

      <Card>
        <CardHeader
          title="Kupon arşivi"
          hint={
            acikNo
              ? `Ekranda #${acikNo} açık — kaydet üstüne yazar, "yeni kupon olarak kaydet" ayrı bir deneme açar.`
              : "Bir kupon = maçlar + iki çizginin oranı + karneler + işaretler. Kayıt sunucuda dosya olarak durur, git'e girebilir."
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
            analizVar={tazeCizgiler.length > 0}
            kuponVar={kuponGecerli || sekilliler.some((g) => g.kupon.eksik.length === 0)}
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Analiz ayarları"
          hint={
            hazirlar.length
              ? `${hazirlar.map((c) => CIZGI_ADI[c]).join(" ve ")} bu ayarla` +
                (ayar.kapsam === "kendi"
                  ? ", HER MAÇ KENDİ LİGİNDE aranır."
                  : ", tüm liglerin korpusunda aranır — lig süzgeci yok.")
              : "Bir çizginin 15 satırının da oranı tam olunca analiz koşulabilir."
          }
        />
        <CardBody>
          <AnalizAyarlari
            ayar={ayar}
            onChange={setAyar}
            onAnaliz={analizEt}
            hazir={hazir}
            kosuyor={kosuyor}
            ortalamaMarj={ozetler[cizgi].ortalamaMarj}
            bayat={bayat}
            ligler={ligler}
            taninmayan={taninmayan}
          />
        </CardBody>
      </Card>

      {sekilliler.length ? (
        <Card>
          <CardHeader
            title="Şekilli kuponlar"
            hint={
              `${sekilliler.length} kupon — ` +
              tazeCizgiler.map((c) => CIZGI_ADI[c]).join(" ve ") +
              ", her biri 6 banko + 9 üçlü ve 5 banko + 5 çift + 5 üçlü."
            }
          />
          <CardBody className="space-y-4">
            <SekilliKuponlar
              satirlar={satirlar}
              kuponlar={sekilliler}
              kolonBedeliTl={kolonBedeli}
              haftalikTavanTl={haftalikTavan}
            />
            <div className="border-t border-line pt-4">
              <SekilAciklamasi kuponlar={sekilliler} />
            </div>
          </CardBody>
        </Card>
      ) : null}

      {sonucVar ? (
        <Card>
          <CardHeader
            title={
              `Karne — ${CIZGI_ADI[cizgi].toLocaleLowerCase("tr")}, ` +
              (ayar.kapsam === "kendi" ? "maçın kendi liginde" : "tüm ligler")
            }
            hint={
              kosuyor
                ? `${analiz.biten + analiz.hatali}/${MAC_SAYISI} satır tamamlandı…`
                : [
                    `${CIZGI_ADI[cizgi]} çizgisi`,
                    `${ayar.arindirma} arındırma`,
                    ayar.tarih ? `${ayar.tarih} öncesi` : null,
                    // Arsivden acilan analiz KENDI gununun cevabidir; bugunun
                    // korpusunda ayni sorgu baska sayi verebilir ve bunu
                    // gizlemek kaydi bugunun cevabi gibi okutmak olurdu.
                    analizDamgasi[cizgi]
                      ? `kayıttan: ${analizDamgasi[cizgi]!.slice(0, 10)} ölçüldü${evren[cizgi] ? `, ${sayi(evren[cizgi]!)} maçlık evren` : ""}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
            }
          />
          <CardBody className="space-y-4">
            <AnalizTablosu
              satirlar={satirlar}
              sonuclar={sonuclar[cizgi]}
              ayar={ayar}
              cizgi={cizgi}
            />
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
            title={`İkili kupon — ${CIZGI_ADI[cizgi].toLocaleLowerCase("tr")}`}
            hint="Her maçta karnenin en yüksek iki sembolü işaretlenir — derinlik dağıtılmaz, herkes çifte."
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
                {(bedel / haftalikTavan).toFixed(2)}× tavan. Derinliği maça göre
                dağıtan <strong>şekilli kuponlar</strong> bu sorunu kuralın
                kendisinde çözüyor — 3⁹ = {sayi(3 ** 9)} ve 2⁵·3⁵ ={" "}
                {sayi(2 ** 5 * 3 ** 5)} kolon.
              </Callout>
            ) : null}
            <KuponTablosu satirlar={satirlar} kupon={kupon} />
            <div className="border-t border-line pt-4">
              <KuponAciklamasi kupon={kupon} />
            </div>
          </CardBody>
        </Card>
      ) : null}

      <Callout
        ton={sekilliler.length ? "success" : "neutral"}
        baslik="Sıradaki aşama"
      >
        {sekilliler.length ? (
          <>
            {sekilliler.length} kupon kuruldu ve arşive kaydedilebilir.
            {tazeCizgiler.length === 1 ? (
              <>
                {" "}
                Yalnızca{" "}
                <strong>{CIZGI_ADI[tazeCizgiler[0]!].toLocaleLowerCase("tr")}</strong>{" "}
                çizgisi koşuldu; öteki çizginin 15 oranı da girilirse iki kupon
                daha çıkar.
              </>
            ) : null}
          </>
        ) : hazir ? (
          <>
            {hazirlar.map((c) => CIZGI_ADI[c]).join(" ve ")} için 15 satırın da
            oranı tam. Üstteki ayarlarla aratın; karne çıkınca kuponlar
            kendiliğinden kurulur.
          </>
        ) : (
          <>
            Tabloyu doldurun. Bir çizginin sorgusu,{" "}
            <strong>o çizginin 15 satırının da</strong> oranı tam olduğunda
            kurulabilir — eksik satır kuponun o maçını körleştirir.
          </>
        )}
      </Callout>
    </div>
  );
}
