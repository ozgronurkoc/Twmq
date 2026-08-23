/**
 * Adres çubuğundaki sorgu parametrelerini okuma/yazma — **tek mekanizma**.
 *
 * Aynı iki fonksiyon beş yerde elle kurulmuştu (`istatistik/parts` `?last`,
 * `super-toto/haftalar` `?hafta`, `saglik` `?only`, `kurulum` iki varyant) ve
 * yazma yarıları satır satır aynıydı. Buraya taşınan şey yalnızca
 * **mekanizma**; her çağıran kendi **doğrulamasını** kendi tutar, çünkü
 * doğrulamalar gerçekten farklıdır ("all" özel değeri, haftanın listede olup
 * olmadığı, boş metin).
 *
 * **`router.replace` değil, doğrudan `history.replaceState`.** Router
 * üzerinden gidildiğinde aynı rotaya yapılan replace sayfa bileşenini
 * yeniden bağlıyor: veri sıfırlanıyor ve her filtre tıkında iskelet
 * parlıyordu. Arama parametresini aynı yolda değiştirmek router'ın bilmesi
 * gereken bir şey değil. Ölçüldü: `replaceState` ile tablo tıkta ayakta
 * kalıyor ve yalnızca beklenen tek istek atılıyor.
 *
 * **Sunucuda sessizce `null` döner.** Ön-render edilen bir sayfada render
 * sırasında `window`'a bakmak hidrasyon uyuşmazlığı yapar; değer her zaman
 * bir efektte uygulanır.
 */

/** Bir sorgu parametresini okur. Yoksa/boşsa `null`. */
export function adrestenOku(ad: string): string | null {
  if (typeof window === "undefined") return null;
  const ham = new URL(window.location.href).searchParams.get(ad);
  return ham && ham.trim() ? ham.trim() : null;
}

/**
 * Bir sorgu parametresini yazar; `null` verilirse siler.
 *
 * Adres zaten aynıysa `replaceState` HİÇ çağrılmaz — gereksiz bir geçmiş
 * dokunuşu bazı tarayıcılarda kaydırma konumunu oynatır.
 */
export function adreseYaz(ad: string, deger: string | null): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (deger) url.searchParams.set(ad, deger);
  else url.searchParams.delete(ad);
  const yeni = url.pathname + (url.search || "") + url.hash;
  const mevcut =
    window.location.pathname + window.location.search + window.location.hash;
  if (yeni === mevcut) return;
  window.history.replaceState(window.history.state, "", yeni);
}
