"use client";

import * as React from "react";

/**
 * Sunucudan veri çeken tek kanca.
 *
 * **Neden var.** Aynı desen sekiz yerde elle kurulmuştu — `AbortController`,
 * `yukleniyor`, `hata`, `.then/.catch`, temizlik — ve üç ayrı iptal deyimi
 * ortaya çıkmıştı: kimi `e instanceof DOMException && e.name === "AbortError"`
 * bakıyordu, `app/tahmin` `signal?.aborted`e bakıyordu,
 * `components/benzer/kart` ikisinin üstüne bir de yerel `iptal` bayrağı
 * koyuyordu. Üçü aynı şeyi kastediyor ama farklı durumları kaçırıyorlar:
 * `signal.aborted` iptal *edilmiş* ama henüz reddetmemiş bir isteği yakalar,
 * `DOMException` kontrolü ise `fetch` reddettiğinde çalışır.
 *
 * Burada tek kural var: **iptal bir hata değildir**, sessizce yutulur ve
 * durum hiç güncellenmez.
 *
 * `getir` bir ref'te tutulur, yani çağıranın onu `useCallback`'e sarması
 * gerekmez; isteği ne zaman yenileyeceğine **yalnızca** `bagimliliklar`
 * karar verir. Bu bilinçli: `components/benzer/kart`taki sonsuz döngü tam
 * olarak her render'da yeni kimlik alan bir nesnenin bağımlılık listesine
 * girmesinden çıkmıştı.
 */

export interface IstekDurumu<T> {
  veri: T | null;
  hata: string | null;
  yukleniyor: boolean;
  /** Aynı isteği elle tekrarlar (kullanıcının "Yenile" düğmesi). */
  yenile: () => void;
}

export interface IstekSecenek {
  /** `false` iken istek atılmaz — henüz okunmamış URL, geçersiz parametre. */
  hazir?: boolean;
  /** `Error` olmayan bir şey fırlatılırsa gösterilecek metin. */
  varsayilanHata?: string;
  /**
   * Yeni istek koşarken önceki veri ekranda kalsın mı. Varsayılan `true`:
   * filtre değiştirdiğinde tablo bir anlığına kaybolmaz. `false` verilirse
   * (ör. hafta detayı) eski hafta yeni haftanın verisiymiş gibi görünmez.
   */
  eskiyiKoru?: boolean;
}

/** İptal bir hata değildir — üç deyimin de kapsadığı durumların birleşimi. */
export function iptalMi(e: unknown, signal?: AbortSignal): boolean {
  if (signal?.aborted) return true;
  return e instanceof DOMException && e.name === "AbortError";
}

export function hataMetni(e: unknown, varsayilan: string): string {
  if (e instanceof Error && e.message) return e.message;
  return varsayilan;
}

export function useIstek<T>(
  getir: (signal: AbortSignal) => Promise<T>,
  bagimliliklar: React.DependencyList,
  secenek: IstekSecenek = {},
): IstekDurumu<T> {
  const { hazir = true, varsayilanHata = "İstek başarısız", eskiyiKoru = true } =
    secenek;

  const [veri, setVeri] = React.useState<T | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = React.useState(hazir);
  const [tetik, setTetik] = React.useState(0);

  // `getir` her render'da yeni bir kapanış olabilir; bağımlılık listesine
  // girmemesi için ref'te taşınır (yukarıdaki gerekçe).
  const getirRef = React.useRef(getir);
  React.useEffect(() => {
    getirRef.current = getir;
  });

  React.useEffect(() => {
    if (!hazir) {
      setYukleniyor(false);
      return;
    }
    const ac = new AbortController();
    let gecerli = true;

    setYukleniyor(true);
    if (!eskiyiKoru) setVeri(null);

    getirRef
      .current(ac.signal)
      .then((d) => {
        if (!gecerli) return;
        setVeri(d);
        setHata(null);
        setYukleniyor(false);
      })
      .catch((e: unknown) => {
        if (!gecerli || iptalMi(e, ac.signal)) return;
        setHata(hataMetni(e, varsayilanHata));
        setYukleniyor(false);
      });

    return () => {
      gecerli = false;
      ac.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...bagimliliklar, hazir, tetik]);

  const yenile = React.useCallback(() => setTetik((t) => t + 1), []);
  return { veri, hata, yukleniyor, yenile };
}
