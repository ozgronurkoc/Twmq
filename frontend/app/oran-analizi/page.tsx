"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { ARINDIRMA_YONTEMLERI, getBenzer, type ArindirmaYontemi } from "@/lib/api";
import { adrestenOku, adreseYaz } from "@/lib/adres";
import { useIstek } from "@/lib/istek";
import { CIZGILER, SEMBOLLER, type Cizgi } from "@/lib/types";
import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
} from "@/components/ui/primitives";
import { Collapsible, NumberField, Select } from "@/components/ui/controls";
import {
  GenelKarne,
  LigKirilimi,
  OranGirisi,
  marjHesapla,
  oranGecerli,
  oranSayilari,
  type Sorgu,
} from "@/components/oran-analizi/parts";

const BOS_ORAN: Record<string, string> = { "1": "", "0": "", "2": "" };

const VARSAYILAN: Sorgu = {
  oran: BOS_ORAN,
  cizgi: "kapanis",
  arindirma: "shin",
  tolerans: null,
  enAz: 200,
  sezon: "",
  tarih: "",
};

/**
 * Oran analizi — *"bu oranda geçmişte ne oldu?"*
 *
 * Bu sayfa bir SORGU aracıdır: kullanıcı 1/0/2 oranını kendi girer.
 * `/istatistik` ailesi (sezonun raporu) ile karıştırılmamalı — orada soru
 * "piyasa sezon boyunca ne dedi", burada "bu fiyatta ne oldu".
 *
 * Motor yeni değil: `spor_toto/benzer.py` bu cevabı baştan beri üretiyordu
 * ve `components/benzer/kart.tsx` onu gösteriyordu — ama yalnızca **var
 * olan bir maçın** oranıyla, `/tahmin` ve `/super-toto` içinde. Elle oran
 * girecek bir yer yoktu; lig kırılımının arkasındaki maçlar ise hiç
 * görünmüyordu.
 *
 * ─── Sorgu NIÇIN düğmeye bağlı ────────────────────────────────────────────
 *
 * Tuş vuruşunda koşmuyor. Üç oran kutusu var; canlı sorgu "1", "1.8",
 * "1.82" için üç ayrı tarama demek olurdu ve ilk ikisi anlamsız. Ayrıca
 * `components/benzer/kart.tsx`teki sonsuz döngü tarihçesi (bağımlılık
 * listesi geniş tutulunca saniyede onlarca istek) tam bu sayfada
 * tekrarlanmaya en müsait yerdir. İstek anahtarı bu yüzden **gönderilmiş**
 * sorgudur, forma yazılan değil.
 */
export default function OranAnaliziSayfasi() {
  const [form, setForm] = React.useState<Sorgu>(VARSAYILAN);
  // Kosan sorgu formdan AYRI: form yazilirken degisir, bu yalnizca "Ara"da.
  const [gonderilen, setGonderilen] = React.useState<Sorgu | null>(null);
  const [urlOkundu, setUrlOkundu] = React.useState(false);

  // Adres cubugu tek kaynak: paylasilan bir baglanti ayni sorguyu acmali.
  React.useEffect(() => {
    // Dogrulama BURADA yapilir, `lib/adres` yalnizca mekanizmadir (modul
    // basligindaki kural): adres cubugundaki deger kullanicidan gelir ve
    // bilinmeyen bir `cizgi`/`arindirma` sessizce gecerse sayfa sunucudan
    // 400 alip bos durur.
    const oran = Object.fromEntries(
      SEMBOLLER.map((s) => [s, adrestenOku(`o${s}`) ?? ""]),
    );
    const cizgi = adrestenOku("cizgi");
    const arindirma = adrestenOku("arindirma");
    const tolerans = Number(adrestenOku("tolerans"));
    const enAz = Number(adrestenOku("en_az"));
    const ham: Sorgu = {
      oran,
      cizgi: (CIZGILER as readonly string[]).includes(cizgi ?? "")
        ? (cizgi as Cizgi)
        : "kapanis",
      arindirma: (ARINDIRMA_YONTEMLERI as readonly string[]).includes(
        arindirma ?? "",
      )
        ? (arindirma as ArindirmaYontemi)
        : "shin",
      tolerans: Number.isFinite(tolerans) && tolerans > 0 ? tolerans : null,
      enAz: Number.isInteger(enAz) && enAz > 0 ? enAz : VARSAYILAN.enAz,
      sezon: adrestenOku("sezon") ?? "",
      tarih: adrestenOku("tarih") ?? "",
    };
    setForm(ham);
    if (oranGecerli(oran)) setGonderilen(ham);
    setUrlOkundu(true);
  }, []);

  const gecerli = oranGecerli(form.oran);
  const marj = marjHesapla(form.oran);

  function ara() {
    if (!gecerli) return;
    setGonderilen(form);
    // Varsayilan degerler adrese YAZILMAZ: paylasilan baglanti yalnizca
    // kullanicinin gercekten degistirdigi seyi tasisin.
    const yazilacak: Record<string, string | null> = {
      o1: form.oran["1"] ?? null,
      o0: form.oran["0"] ?? null,
      o2: form.oran["2"] ?? null,
      cizgi: form.cizgi === VARSAYILAN.cizgi ? null : form.cizgi,
      arindirma:
        form.arindirma === VARSAYILAN.arindirma ? null : form.arindirma,
      tolerans: form.tolerans == null ? null : String(form.tolerans),
      en_az: form.enAz === VARSAYILAN.enAz ? null : String(form.enAz),
      sezon: form.sezon || null,
      tarih: form.tarih || null,
    };
    for (const [ad, deger] of Object.entries(yazilacak)) adreseYaz(ad, deger);
  }

  const anahtar = gonderilen
    ? [
        SEMBOLLER.map((s) => gonderilen.oran[s]).join(","),
        gonderilen.cizgi,
        gonderilen.arindirma,
        gonderilen.tolerans ?? "auto",
        gonderilen.enAz,
        gonderilen.sezon,
        gonderilen.tarih,
      ].join("|")
    : "";

  const { veri, hata, yukleniyor } = useIstek(
    (signal) =>
      getBenzer(
        oranSayilari(gonderilen!.oran),
        {
          cizgi: gonderilen!.cizgi,
          arindirma: gonderilen!.arindirma,
          en_az: gonderilen!.enAz,
          ...(gonderilen!.tolerans != null
            ? { tolerans: gonderilen!.tolerans }
            : {}),
          ...(gonderilen!.sezon ? { sezon: gonderilen!.sezon } : {}),
          ...(gonderilen!.tarih ? { tarih: gonderilen!.tarih } : {}),
        },
        signal,
      ),
    [anahtar],
    { hazir: urlOkundu && !!gonderilen, varsayilanHata: "Sorgu başarısız" },
  );

  return (
    <div className="mx-auto w-full max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Oran Analizi</h1>
        <p className="mt-1 max-w-[62ch] text-[13px] leading-relaxed text-muted-foreground">
          Bir maçın 1 / 0 / 2 oranını girin; aynı fiyata sahip geçmiş maçların
          nasıl sonuçlandığını görün. Eşleme <strong>oran uzayında değil,
          marj arındırıldıktan sonra olasılık uzayında</strong> yapılır — aynı
          gerçek olasılık farklı marjda tamamen farklı oran verir. Cevap bir
          tahmin değildir: her yüzdenin yanında n ve %95 aralık durur.
        </p>
      </div>

      <Card>
        <CardHeader
          title="Oranlar"
          hint="Elinizdeki bültenin oranlarını olduğu gibi girin — marj arındırması sunucuda yapılır."
        />
        <CardBody className="space-y-4">
          <OranGirisi
            oran={form.oran}
            onChange={(s, v) =>
              setForm((f) => ({ ...f, oran: { ...f.oran, [s]: v } }))
            }
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Select<Cizgi>
              label="Fiyat çizgisi"
              value={form.cizgi}
              onChange={(v) => setForm((f) => ({ ...f, cizgi: v }))}
              options={[
                { value: "kapanis", label: "Kapanış" },
                { value: "acilis", label: "Açılış" },
              ]}
              hint="Elinizdeki oran açılış oranıysa açılışı seçin: aynı maçın iki fiyatı arasındaki fark ölçülmüş bir şeydir ve kapanış evreninde arama yapmak elmayı armutla karşılaştırmak olur."
            />
            <Select<ArindirmaYontemi>
              label="Marj arındırma"
              value={form.arindirma}
              onChange={(v) => setForm((f) => ({ ...f, arindirma: v }))}
              options={ARINDIRMA_YONTEMLERI.map((y) => ({ value: y, label: y }))}
              hint={
                marj == null ? (
                  "Girilen oranın marjı burada görünür."
                ) : (
                  <>
                    Girilen oranın marjı <strong>%{(100 * marj).toFixed(1)}</strong>
                    {marj > 0.12
                      ? " — korpus ~%7 marjlı; bu farkta yöntem sonucu görünür biçimde değiştirir."
                      : "."}
                  </>
                )
              }
            />
          </div>

          <Collapsible baslik="Gelişmiş" hint="yarıçap · örneklem · kesit">
            <div className="grid grid-cols-1 gap-3 pt-3 sm:grid-cols-2">
              <NumberField
                label="Yarıçap (olasılık puanı)"
                value={form.tolerans ?? 0}
                step={0.005}
                min={0}
                max={0.05}
                onChange={(v) =>
                  setForm((f) => ({ ...f, tolerans: v > 0 ? v : null }))
                }
                hint="0 = uyarlansın (varsayılan): hedef örnekleme ulaşana kadar büyür, ±5 puanda durur. Fiilen kullanılan yarıçap cevapta her zaman yazar."
              />
              <NumberField
                label="Hedef örneklem"
                value={form.enAz}
                min={1}
                max={5000}
                onChange={(v) => setForm((f) => ({ ...f, enAz: v }))}
                hint="Uyarlanan aramanın ulaşmaya çalıştığı maç sayısı."
              />
              <TextAlan
                label="Sezon"
                value={form.sezon}
                placeholder="2425"
                onChange={(v) => setForm((f) => ({ ...f, sezon: v }))}
                hint="Boş = tüm sezonlar."
              />
              <TextAlan
                label="Tarih kesmesi"
                value={form.tarih}
                placeholder="2023-08-01"
                onChange={(v) => setForm((f) => ({ ...f, tarih: v }))}
                hint="YYYY-AA-GG. Verilirse yalnızca bu günden ÖNCEKİ maçlar aranır — kronolojik sorgu böyle kurulur."
              />
            </div>
          </Collapsible>

          <div className="flex items-center gap-3">
            <Button tip="primary" onClick={ara} disabled={!gecerli || yukleniyor}>
              <Search size={15} />
              {yukleniyor ? "Aranıyor…" : "Ara"}
            </Button>
            {!gecerli ? (
              <span className="text-[12px] text-muted-foreground">
                Üç oranı da girin (her biri 1.00&apos;den büyük).
              </span>
            ) : null}
          </div>
        </CardBody>
      </Card>

      {hata ? (
        <Callout ton="danger" baslik="Sorgu başarısız">
          {hata}
        </Callout>
      ) : null}

      {yukleniyor && !veri ? (
        <div className="space-y-3">
          <Skeleton className="h-[280px] w-full" />
          <Skeleton className="h-[220px] w-full" />
        </div>
      ) : null}

      {veri && gonderilen ? (
        <>
          <GenelKarne veri={veri} />
          <LigKirilimi veri={veri} sorgu={gonderilen} />
        </>
      ) : null}
    </div>
  );
}

/** `ui/controls`ta metin alanı yok; sezon/tarih için en küçük karşılığı. */
function TextAlan({
  label,
  value,
  onChange,
  placeholder,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: React.ReactNode;
}) {
  const id = React.useId();
  return (
    <div>
      <label htmlFor={id} className="block text-[12px] font-medium text-muted-foreground">
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 h-10 w-full rounded-xl border border-line bg-background px-3 text-[13.5px] transition-shadow duration-200 ease-smooth focus:outline-none focus:ring-2 focus:ring-primary/50"
      />
      {hint ? (
        <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}
