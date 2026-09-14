"use client";

import * as React from "react";
import { Eraser } from "lucide-react";

import {
  arsiveYaz,
  arsivdenSil,
  getArsivKaydi,
  getArsivListesi,
  getBenzer,
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
import {
  analizOzeti,
  analizeHazir,
  bosAnaliz,
  sorguIzi,
  VARSAYILAN_ANALIZ,
  type AnalizAyari,
  type SatirAnalizi,
} from "@/lib/kupon-analiz";
import { CIZGILER, MAC_SAYISI, type ArsivOzeti, type Cizgi, type Sembol } from "@/lib/types";
import { yuzde } from "@/lib/utils";
import { Badge, Button, Callout, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { KuponIzgarasi } from "@/components/kupon/izgara";
import { AnalizAyarlari } from "@/components/kupon/ayarlar";
import { AnalizTablosu, TabloAciklamasi } from "@/components/kupon/analiz-tablosu";
import { ArsivCubugu } from "@/components/kupon/arsiv-cubugu";

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
  const [hafta, setHafta] = React.useState(1);
  const [not, setNot] = React.useState("");
  const [kayitlar, setKayitlar] = React.useState<ArsivOzeti[]>([]);
  /** Ekrandaki tablo hangi haftadan yuklendi; `null` = arsivden gelmedi. */
  const [yuklenen, setYuklenen] = React.useState<number | null>(null);
  const [arsivKosuyor, setArsivKosuyor] = React.useState(false);
  const [arsivHata, setArsivHata] = React.useState<string | null>(null);
  const [kaydedildi, setKaydedildi] = React.useState<string | null>(null);

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
    setYuklenen(null);
    setKaydedildi(null);
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

    await Promise.all(
      satirlar.map(async (satir, i) => {
        try {
          const veri = await getBenzer(
            oranSayilari(satir),
            {
              cizgi: ayar.cizgi,
              arindirma: ayar.arindirma,
              en_az: ayar.enAz,
              // Lig suzgeci BILEREK yok: aranan yer tum liglerin korpusu.
              ...(ayar.tarih ? { tarih: ayar.tarih } : {}),
            },
            kontrol.signal,
          );
          if (kontrol.signal.aborted) return;
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

    if (!kontrol.signal.aborted) setKosuyor(false);
  }

  /**
   * Haftayi arsive yazar.
   *
   * Tablo zaten her tus vurusunda tarayiciya yaziliyor; bu ondan BASKA bir
   * sey. Arsiv bilincli bir karardir ve bu yuzden otomatik degil: yanlislikla
   * 5. haftanin ustune 6. haftanin yarim tablosunu yazmak, bu sayfada geri
   * alinamayacak tek islem olurdu.
   *
   * Gonderilen sey GIRDI ve AYAR; karne gonderilmiyor (turetilmis veri
   * bayatlar — `spor_toto/kupon_arsivi.py` bas yorumu). Dogrulama da
   * sunucuda: buradan gecen govde orada yeniden dogrulanir.
   */
  async function arsiveKaydet() {
    setArsivKosuyor(true);
    setArsivHata(null);
    try {
      const kayit = await arsiveYaz({
        hafta,
        not,
        ayar: {
          cizgi: ayar.cizgi,
          arindirma: ayar.arindirma,
          en_az: ayar.enAz,
          tarih: ayar.tarih,
        },
        satirlar: satirlar.map((s) => ({
          lig: s.lig,
          ev: s.ev,
          dep: s.dep,
          oran: { ...s.oran },
        })),
      });
      setYuklenen(kayit.hafta);
      setKaydedildi(kayit.guncellendi.slice(11, 16));
      await listeyiTazele();
    } catch (e) {
      setArsivHata(hataMetni(e, "Kaydedilemedi"));
    } finally {
      setArsivKosuyor(false);
    }
  }

  /**
   * Kayitli bir haftayi ekrana yukler.
   *
   * Analiz sonuclari TEMIZLENIR: ekrandaki karne baska bir haftanin
   * girdisine aitti ve onu yeni tablonun cevabi gibi birakmak, sayfanin
   * "bayat sonuc" kuralinin tam tersi olurdu.
   */
  async function arsivdenAc(no: number) {
    setArsivKosuyor(true);
    setArsivHata(null);
    try {
      const kayit = await getArsivKaydi(no);
      iptalci.current?.abort();
      setSatirlar(kayittanSatirlar(kayit.satirlar));
      setAyar({
        cizgi: (CIZGILER as readonly string[]).includes(kayit.ayar.cizgi)
          ? (kayit.ayar.cizgi as Cizgi)
          : VARSAYILAN_ANALIZ.cizgi,
        arindirma: kayit.ayar
          .arindirma as AnalizAyari["arindirma"],
        enAz: kayit.ayar.en_az,
        tarih: kayit.ayar.tarih ?? "",
      });
      setNot(kayit.not ?? "");
      setHafta(kayit.hafta);
      setYuklenen(kayit.hafta);
      setSonuclar(bosAnaliz(MAC_SAYISI));
      setKosanIz(null);
      setKosuyor(false);
      setKaydedildi(null);
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
      if (yuklenen === no) setYuklenen(null);
      await listeyiTazele();
    } catch (e) {
      setArsivHata(hataMetni(e, "Silinemedi"));
    } finally {
      setArsivKosuyor(false);
    }
  }

  const ozet = kuponOzeti(satirlar);
  const analiz = analizOzeti(sonuclar);
  const hazir = analizeHazir(satirlar, ayar);
  const suankiIz = sorguIzi(satirlar, ayar);
  const bayat = kosanIz != null && kosanIz !== suankiIz;
  const sonucVar = kosanIz != null;
  const doluMu = satirlar.some(
    (s) => s.lig || s.ev || s.dep || s.oran["1"] || s.oran["0"] || s.oran["2"],
  );

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
          title="Hafta arşivi"
          hint={
            yuklenen
              ? `Ekrandaki tablo ${yuklenen}. haftanın kaydından açıldı.`
              : "Kayıt sunucuda dosya olarak durur — başka tarayıcıda da açılır, git'e girebilir."
          }
        />
        <CardBody>
          <ArsivCubugu
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
            yuklenen={yuklenen}
            kosuyor={arsivKosuyor}
            hata={arsivHata}
            onKaydet={arsiveKaydet}
            onAc={arsivdenAc}
            onSil={arsivdenKaldir}
            kaydedildi={kaydedildi}
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Analiz ayarları"
          hint="15 satırın tamamı bu ayarla, tüm liglerin korpusunda aranır — lig süzgeci yok."
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
          />
        </CardBody>
      </Card>

      {sonucVar ? (
        <Card>
          <CardHeader
            title="Karne — tüm ligler"
            hint={
              kosuyor
                ? `${analiz.biten + analiz.hatali}/${MAC_SAYISI} satır tamamlandı…`
                : `${ayar.cizgi === "acilis" ? "Açılış" : "Kapanış"} çizgisi · ${ayar.arindirma} arındırma${ayar.tarih ? ` · ${ayar.tarih} öncesi` : ""}`
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

      <Callout ton={sonucVar && analiz.tamam ? "success" : "neutral"} baslik="Sıradaki aşama">
        {sonucVar && analiz.tamam ? (
          <>
            Karne çıktı. Bundan sonrası <strong>olasılık</strong> ve{" "}
            <strong>işaret seçimi</strong>: hangi sayının kupona gireceği
            (piyasa · karne · karışım) ve 15 maçın banko/çifte/üçlü
            dağılımının hangi bütçeyle kurulacağı — ikisi de henüz karara
            bağlanmadı.
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
