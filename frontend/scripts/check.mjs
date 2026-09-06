/**
 * Arayuzun saf mantiginin denetimi — tarayici gerektirmeyen her sey.
 *
 * Iki bolum var:
 *   1. Kurulum kodlamasi (kalicilik + paylasilabilir baglanti)
 *   2. Kume-ici hesabi (uretmeden once gorulen kosul)
 *
 * NEDEN VAR: kurulum kodlamasi sabit genislikli ve tek bir alan tasinca
 * ONDAN SONRAKI TUM maclar kayar — yani hata bir maci degil, kuponun
 * yarisini bozar ve hicbir yerde patlamaz, sessizce baska bir kupon
 * uretir. Ilk surumde tam bunu yapti: binde birlik olasilik 0..1000
 * araligindadir, banko bir macta 1000 dort basamak eder ve `padStart(3)`
 * alani 4 karaktere tasirdi. Kume-ici hesabi da ayni sinifta: 15 sayinin
 * carpimi, yanlis oldugunda makul gorunmeye devam eder.
 *
 * Bagimlilik eklemez: tsc (zaten devDependency) modulleri gecici bir
 * dizine cevirir, dosya duz node ile kosar.
 *
 * Calistirma: npm run check   (ya da node scripts/check.mjs)
 */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const kok = join(dirname(fileURLToPath(import.meta.url)), "..");
// Cikti /tmp'e DEGIL frontend/ altina yazilir: `lib/utils.ts` clsx ve
// tailwind-merge'e bagli, repo disindaki bir dizin node_modules'i goremez.
const cikti = mkdtempSync(join(kok, ".kurulum-check-"));

/**
 * Backend'in urettigi sozlesme (`backend/scripts/api_sozlesme.py`).
 * `olculmus` blogu, bu dosyada eskiden DUZ YAZILI duran "(olculdu)"
 * sayilarinin yerine gecer.
 */
/** Uretilmis Super Toto beslemesi (`super_toto_frontend.py`). */
const BESLEME = JSON.parse(
  readFileSync(join(kok, "lib", "super-toto-veri.json"), "utf8"),
);

const SOZLESME = JSON.parse(
  readFileSync(join(kok, "lib", "api-sozlesme.json"), "utf8"),
);

try {
  // CommonJS'e cevrilir: tsc `./types` importlarini uzantisiz birakir ve
  // Node'un ESM cozumleyicisi uzantisiz yolu bulamaz.
  execFileSync(
    "npx",
    [
      "tsc", "lib/kurulum.ts", "lib/kume-ici.ts", "lib/senaryo.ts",
      "lib/utils.ts", "lib/types.ts", "lib/sekmeler.ts",
      "lib/super-toto.ts",
      "--outDir", cikti,
      "--module", "commonjs", "--target", "es2022", "--skipLibCheck",
      // `lib/super-toto.ts` beslemeyi import ediyor.
      "--resolveJsonModule", "--esModuleInterop",
    ],
    { cwd: kok, stdio: "inherit" },
  );

  const iste = createRequire(import.meta.url);
  const K = iste(join(cikti, "kurulum.js"));
  const Z = iste(join(cikti, "kume-ici.js"));
  const S = iste(join(cikti, "senaryo.js"));
  const T = iste(join(cikti, "sekmeler.js"));
  // `types.ts` yalnizca tip TASIMIYOR; `MAC_SAYISI` ve `SEMBOLLER`
  // gibi calisma zamani sabitleri de orada ve ikisi de sunucuyla
  // karsilastirilmak zorunda.
  const TIP = iste(join(cikti, "types.js"));
  const ST = iste(join(cikti, "super-toto.js"));

  let gecen = 0;
  const dene = (ad, fn) => {
    fn();
    gecen++;
    console.log(`  ✓ ${ad}`);
  };

  // ── Isaretler ────────────────────────────────────────────────────────
  dene("varsayilan kurulum gidis-donus", () => {
    const v = K.varsayilanKurulum();
    const geri = K.kurulumuCoz(K.kurulumuKodla(v));
    assert.deepEqual(geri.kurulum.matches, v.matches);
    assert.deepEqual(geri.atlanan, []);
  });

  dene("her isaret kombinasyonu (7 durum) korunur", () => {
    // 15 macin tamami tek tek her kombinasyondan gecirilir.
    const kombinasyonlar = [
      ["1"], ["0"], ["2"], ["1", "0"], ["1", "2"], ["0", "2"], ["1", "0", "2"],
    ];
    for (const kom of kombinasyonlar) {
      const k = K.varsayilanKurulum();
      k.matches = k.matches.map(() => [...kom]);
      const geri = K.kurulumuCoz(K.kurulumuKodla(k));
      assert.deepEqual(geri.kurulum.matches.map((r) => r.join("")), Array(15).fill(kom.join("")));
    }
  });

  // ── Olasiliklar: tasma vakasi ────────────────────────────────────────
  dene("banko mac (p=1.0) sonraki maclari KAYDIRMAZ", () => {
    const k = K.varsayilanKurulum();
    k.probsAcik = true;
    // 1. mac banko: p1 = 1.0 -> binde 1000. Ilk surum burada tasiyordu.
    k.probs = k.probs.map((_, i) =>
      i === 0
        ? { "1": 1, "0": 0, "2": 0 }
        : { "1": 0.25, "0": 0.5, "2": 0.25 },
    );
    const geri = K.kurulumuCoz(K.kurulumuKodla(k));
    assert.equal(geri.atlanan.length, 0, "olasiliklar okunamadi");
    assert.equal(geri.kurulum.probs[0]["1"], 1);
    // Kayma olsaydi bu satirlar bozulurdu.
    for (let i = 1; i < 15; i++) {
      assert.equal(geri.kurulum.probs[i]["1"], 0.25, `${i + 1}. mac kaydi`);
      assert.equal(geri.kurulum.probs[i]["0"], 0.5, `${i + 1}. mac kaydi`);
    }
  });

  dene("her satir 1'e toplanir ve binde bir icinde kalir", () => {
    const k = K.varsayilanKurulum();
    k.probsAcik = true;
    // Ham agirlik (toplami 1 degil) — normalize edilerek tasinmali.
    k.probs = k.probs.map(() => ({ "1": 5, "0": 3, "2": 2 }));
    const geri = K.kurulumuCoz(K.kurulumuKodla(k));
    for (const satir of geri.kurulum.probs) {
      const toplam = satir["1"] + satir["0"] + satir["2"];
      assert.ok(Math.abs(toplam - 1) < 1e-9, `satir 1'e toplanmiyor: ${toplam}`);
      assert.ok(Math.abs(satir["1"] - 0.5) <= 0.001);
      assert.ok(Math.abs(satir["0"] - 0.3) <= 0.001);
      assert.ok(Math.abs(satir["2"] - 0.2) <= 0.001);
    }
  });

  dene("sifir olasilikli sembol korunur", () => {
    const k = K.varsayilanKurulum();
    k.probsAcik = true;
    k.probs = k.probs.map(() => ({ "1": 0, "0": 0, "2": 1 }));
    const geri = K.kurulumuCoz(K.kurulumuKodla(k));
    for (const satir of geri.kurulum.probs) {
      assert.equal(satir["1"], 0);
      assert.equal(satir["0"], 0);
      assert.equal(satir["2"], 1);
    }
  });

  // ── Ayarlar ──────────────────────────────────────────────────────────
  //
  // Burada iki test vardi ve ikisi de kaplama ayarlarini tutuyordu: mod /
  // varyant / butce / plan / motor ayarlarinin gidis-donusu, ve "eski 6
  // alanli motor baglantisi hala cozuluyor". Kaplama sokuldu
  // (docs/DUZ_SISTEME_GECIS.md); o alanlarin hicbiri artik yok. Yerlerine
  // ESKI baglantilarin ne olduğunu tutan test geldi (asagida).

  dene("kalan ayarlar gidis-donus", () => {
    const k = K.varsayilanKurulum();
    k.fireMax = 0;
    k.kati = true;
    k.mcSamples = 150000;
    const geri = K.kurulumuCoz(K.kurulumuKodla(k)).kurulum;
    assert.equal(geri.fireMax, 0);
    assert.equal(geri.kati, true);
  });

  dene("kaplama devrinin baglantilari SESSIZCE yok sayilmaz", () => {
    // Paylasilmis eski adresler `m` (mod), `v` (varyant), `b` (butce),
    // `pc`/`pa` (butce plani) ve `e` (motor ayarlari) tasiyor. Bunlari
    // gormezden gelmek, kullaniciya "istedigin kupon kuruldu" demek
    // olurdu — oysa istedigi sey artik uretilemiyor. Cozucu onlari
    // `atlanan`a yaziyor ve arayuz soyluyor.
    const adres = K.kurulumuKodla(K.varsayilanKurulum())
      + "&m=fix16&v=3&b=4096&pc=12&pa=7&e=9,12345,7,90,512,1024";
    const { kurulum: geri, atlanan } = K.kurulumuCoz(adres);
    for (const ad of ["mod", "varyant", "bütçe", "plan sayısı",
                      "uygulanacak plan", "motor ayarları"]) {
      assert.ok(
        atlanan.some((x) => x.startsWith(ad)),
        `"${ad}" atlanan listesinde yok: ${JSON.stringify(atlanan)}`,
      );
    }
    // Kurulumun geri kalani SAGLAM kalmali: eski parametreler adresi
    // butunuyle bozuk saydirmamali.
    assert.deepEqual(geri.matches, K.VARSAYILAN_MACLAR);
  });

  dene("bayes ayarlari gidis-donus", () => {
    const k = K.varsayilanKurulum();
    k.probsAcik = true;
    k.useBayes = true;
    k.elleAyar = true;
    k.prior = 2.5;
    k.evidence = 40;
    k.mcSamples = 150000;
    const geri = K.kurulumuCoz(K.kurulumuKodla(k)).kurulum;
    assert.equal(geri.useBayes, true);
    assert.equal(geri.elleAyar, true);
    assert.equal(geri.prior, 2.5);
    assert.equal(geri.evidence, 40);
    assert.equal(geri.mcSamples, 150000);
  });

  // ── Bozuk girdi ──────────────────────────────────────────────────────
  // ── Mac adlari ───────────────────────────────────────────────────────

  dene("adlar 15'e sabitlenir, kirpilir, tek satira indirilir", () => {
    const e = K.temizEtiketler([
      "  Galatasaray –  Fenerbahçe  ",
      "Beşiktaş\nTrabzonspor",
      "x".repeat(200),
      42,
      null,
    ]);
    assert.equal(e.length, 15);
    assert.equal(e[0], "Galatasaray – Fenerbahçe");
    assert.equal(e[1], "Beşiktaş Trabzonspor", "satir sonu izgarayi bozardi");
    assert.equal(e[2].length, K.ETIKET_SINIR);
    assert.equal(e[3], "", "string olmayan deger yutulmali");
    assert.equal(e[14], "");
  });

  dene("adlar BAGLANTIDA tasinmaz (URL uc katina cikardi)", () => {
    const k = K.varsayilanKurulum();
    k.labels = k.labels.map((_, i) => `Takım A${i} – Takım B${i}`);
    const kodlu = K.kurulumuKodla(k);
    assert.ok(!kodlu.includes("Tak"), "ad baglantiya sizdi");
    const geri = K.kurulumuCoz(kodlu).kurulum;
    assert.deepEqual(geri.labels, Array(15).fill(""));
  });

  dene("ad degistirmek sonucun parmak izini DEGISTIRMEZ", () => {
    // Ad cozume girmez; maca ad vermek ekrandaki sonucu bayatlatmamali.
    const a = K.varsayilanKurulum();
    const b = K.varsayilanKurulum();
    b.labels = b.labels.map((_, i) => `Mac ${i}`);
    assert.equal(K.kurulumuKodla(a), K.kurulumuKodla(b));
  });

  dene("kurulumsuz adres null doner (`?hafta=51` kurulum sanilmaz)", () => {
    assert.equal(K.kurulumuCoz("?hafta=51"), null);
    assert.equal(K.kurulumuCoz(""), null);
  });

  dene("bozuk alanlar varsayilana duser ve RAPORLANIR", () => {
    const geri = K.kurulumuCoz("?s=99xx&m=uydurma&p=abc&e=1,2");
    assert.ok(geri, "cozum null dondu");
    assert.deepEqual(geri.kurulum.matches, K.VARSAYILAN_MACLAR);
    assert.ok(geri.atlanan.includes("maç seçimleri"));
    assert.ok(geri.atlanan.includes("olasılıklar"));
    assert.ok(geri.atlanan.some((x) => x.startsWith("mod")));
    assert.ok(geri.atlanan.some((x) => x.startsWith("motor ayarları")));
  });

  dene("bozuk olasilik girisi KAPALI acilir, uydurma deger beslenmez", () => {
    const geri = K.kurulumuCoz("?s=111111111111111&p=abc").kurulum;
    assert.equal(geri.probsAcik, false, "bozuk olasilikla giris acik kaldi");
  });

  dene("gecerli olasilik girisi ACIK acilir", () => {
    const k = K.varsayilanKurulum();
    k.probsAcik = true;
    const geri = K.kurulumuCoz(K.kurulumuKodla(k)).kurulum;
    assert.equal(geri.probsAcik, true);
  });

  dene("bos mac (maske 0) reddedilir — motorda ValueError uretirdi", () => {
    const geri = K.kurulumuCoz("?s=011111111111111");
    assert.deepEqual(geri.kurulum.matches, K.VARSAYILAN_MACLAR);
    assert.ok(geri.atlanan.includes("maç seçimleri"));
    assert.ok(geri.kurulum.matches.every((r) => r.length > 0));
  });

  dene("sinir disi sayilar kirpilir, patlamaz", () => {
    const geri = K.kurulumuCoz("?s=111111111111111&f=99&mc=99999999").kurulum;
    assert.equal(geri.fireMax, 2);
    assert.equal(geri.mcSamples, K.SINIRLAR.mc_samples.max);
  });

  // ── Kume-ici hesabi ──────────────────────────────────────────────────

  // README'nin ornek kuponu + check.sh'in ornek olasiliklari. Ikisi de
  // depoda zaten var, yani bu vaka uydurulmus degil.
  // Kupon da sozlesmeden: backend `core.ORNEK_KUPON`u degistirirse
  // buradaki olculmus sayilar baska bir kupona ait olurdu.
  const ORNEK_SEC = SOZLESME.olculmus.ornek_kupon
    .split(",")
    .map((s) => s.split(""));
  const ORNEK_P = [
    [0.5, 0.3, 0.2], [0.4, 0.4, 0.2], [0.6, 0.2, 0.2], [0.5, 0.25, 0.25],
    [0.3, 0.4, 0.3], [0.45, 0.35, 0.2], [0.5, 0.3, 0.2], [0.4, 0.3, 0.3],
    [0.55, 0.25, 0.2], [0.5, 0.3, 0.2], [0.4, 0.3, 0.3], [0.5, 0.3, 0.2],
    [0.45, 0.35, 0.2], [0.5, 0.25, 0.25], [0.4, 0.4, 0.2],
  ].map(([a, b, c]) => ({ "1": a, "0": b, "2": c }));

  dene("kume-ici, backend'in exact hesabiyla ayni sayiyi verir", () => {
    const h = Z.kumeIciHesapla(ORNEK_SEC, ORNEK_P);
    // Beklenen deger SOZLESMEDEN gelir. Once burada duz yaziliydi
    // ("0.00014902 (olculdu)") ve backend matematigi degistiginde sessizce
    // yanlislanirdi: test yesil kalir ama artik yanlis bir seyi dogrulardi.
    assert.ok(
      Math.abs(h.p - SOZLESME.olculmus.p_kume_ici) < 1e-8,
      `beklenen ${SOZLESME.olculmus.p_kume_ici}, gelen ${h.p}`,
    );
  });

  dene("en zayif uc mac dogru secilir", () => {
    const h = Z.kumeIciHesapla(ORNEK_SEC, ORNEK_P);
    // 7. mac banko "2" (0.20), 14. mac banko "2" (0.25), 5. mac banko "0" (0.40)
    assert.deepEqual(
      h.zayiflar.map((i) => i + 1).sort((a, b) => a - b),
      SOZLESME.olculmus.en_zayif_uc_mac,
    );
  });

  dene("varsayilan satirlar 'bilgi yok' sayilir, %100 diye basilmaz", () => {
    // uniformProb: tum kutle isaretli sembollerde -> p tanim geregi 1.
    const p = ORNEK_SEC.map((sec) => {
      const pay = 1 / sec.length;
      return {
        "1": sec.includes("1") ? pay : 0,
        "0": sec.includes("0") ? pay : 0,
        "2": sec.includes("2") ? pay : 0,
      };
    });
    const h = Z.kumeIciHesapla(ORNEK_SEC, p);
    assert.ok(Math.abs(h.p - 1) < 1e-9, "p 1 cikmali");
    assert.equal(h.bilgiYok, true, "bilgisiz durum yakalanmadi");
  });

  dene("gercek tahmin girilince 'bilgi yok' kalkar", () => {
    const h = Z.kumeIciHesapla(ORNEK_SEC, ORNEK_P);
    assert.equal(h.bilgiYok, false);
  });

  dene("kutleler esitken 'en zayif uc' YOKTUR (keyfi suclama olurdu)", () => {
    const esit = ORNEK_SEC.map(() => ({ "1": 1 / 3, "0": 1 / 3, "2": 1 / 3 }));
    // Hepsi banko: her kutle 1/3, yani tamamen esit.
    const h = Z.kumeIciHesapla(Array(15).fill(["1"]), esit);
    assert.deepEqual(h.zayiflar, []);
  });

  dene("hepsi kapama ise %100 gercektir, 'bilgi yok' degildir", () => {
    const sec = Array(15).fill(["1", "0", "2"]);
    const h = Z.kumeIciHesapla(sec, ORNEK_P);
    assert.ok(Math.abs(h.p - 1) < 1e-9);
    assert.equal(h.bilgiYok, false, "kapama maclar bilgisiz sanildi");
  });

  dene("bir mac imkansizsa p sifir olur ve mac adiyla raporlanir", () => {
    const sec = ORNEK_SEC.map((r) => [...r]);
    const p = ORNEK_P.map((r) => ({ ...r }));
    // 3. mac yalnizca "1" isaretli; "1"in olasiligini sifirla.
    p[2] = { "1": 0, "0": 0.5, "2": 0.5 };
    const h = Z.kumeIciHesapla(sec, p);
    assert.equal(h.p, 0);
    assert.deepEqual(h.imkansizlar, [2]);
  });

  dene("sifir olasilikli sembol ONERILMEZ (bedeli artirir, kazanci yok)", () => {
    const sec = [["1"]];
    const p = [{ "1": 1, "0": 0, "2": 0 }];
    const h = Z.kumeIciHesapla(sec, p);
    assert.deepEqual(h.oneriler, [], "sifir olasilikli sembol onerildi");
  });

  dene("oneri carpanlari dogru: kume ×(kutle+p)/kutle, bedel ×(k+1)/k", () => {
    // Tek mac, banko "2" (p=0.2). "1" eklenirse kutle 0.2 -> 0.7.
    const h = Z.kumeIciHesapla([["2"]], [{ "1": 0.5, "0": 0.3, "2": 0.2 }]);
    const o = h.oneriler.find((x) => x.sembol === "1");
    assert.ok(o, "'1' onerisi yok");
    assert.ok(Math.abs(o.kumeCarpani - 3.5) < 1e-9, `kume carpani ${o.kumeCarpani}`);
    assert.ok(Math.abs(o.bedelCarpani - 2) < 1e-9, `bedel carpani ${o.bedelCarpani}`);
    assert.ok(Math.abs(o.verim - 1.75) < 1e-9, `verim ${o.verim}`);
  });

  dene("oneriler verime gore sirali", () => {
    const h = Z.kumeIciHesapla(ORNEK_SEC, ORNEK_P);
    for (let i = 1; i < h.oneriler.length; i++) {
      assert.ok(h.oneriler[i - 1].verim >= h.oneriler[i].verim, "siralama bozuk");
    }
  });

  // Burada iki test vardi ve ikisi de `kaplamaAltSiniri`yi olcuyordu:
  // kure-kaplama alt sinirinin backend'in `alt_sinir`iyla ayni cikmasi, ve
  // uclu maclarin top boyutuna 2 katmasi. Kaplama sokuldu
  // (docs/DUZ_SISTEME_GECIS.md) ve alt sinir kavrami dustu — duzde alt
  // sinir da ust sinir da uzayin KENDISI. Backend `alt_sinir` alanini
  // artik hic gondermiyor.

  dene("kupon bedeli backend'in kolon_bedeli'yle ayni", () => {
    // Ornek kupon: 8 cifte -> 2^8 = 256 kolon (backend olculdu).
    const a = Z.kuponBedeli(ORNEK_SEC);
    assert.equal(a.uzay, SOZLESME.olculmus.uzay);
    assert.equal(a.uzay, SOZLESME.olculmus.duz_kolon);
  });

  dene("bedel isaret sayilarinin CARPIMI: 2^cifte * 3^uclu", () => {
    assert.equal(Z.kuponBedeli([["1", "0", "2"], ["1", "0"], ["1"]]).uzay, 6);
    assert.equal(Z.kuponBedeli([["1", "0"], ["1", "0"], ["1", "0"]]).uzay, 8);
    assert.equal(Z.kuponBedeli([["1"], ["1"], ["1"]]).uzay, 1);
  });

  dene("kucuk olasilik okunur yazilir (sabit basamak farki yutardi)", () => {
    assert.equal(Z.olasilikYaz(0.25), "%25.0");
    assert.equal(Z.olasilikYaz(0.052), "%5.20");
    assert.equal(Z.olasilikYaz(0), "%0");
    // Asil vaka: bu iki kupon farkli, yazim da farkli olmali.
    assert.equal(Z.olasilikYaz(0.000149), "%0.0149");
    assert.equal(Z.olasilikYaz(0.000151), "%0.0151");
    assert.notEqual(Z.olasilikYaz(0.000149), Z.olasilikYaz(0.000151));
    // Sondaki sifirlar dusurulur.
    assert.equal(Z.olasilikYaz(0.00002), "%0.002");
  });

  dene("bir-de-kac orani", () => {
    assert.equal(Z.birdeKac(0.001), "1/1.000");
    assert.equal(Z.birdeKac(0), null);
    assert.equal(Z.birdeKac(1), null);
    const h = Z.kumeIciHesapla(ORNEK_SEC, ORNEK_P);
    assert.equal(Z.birdeKac(h.p), `1/${Math.round(1 / h.p).toLocaleString("tr-TR")}`);
  });

  // ── Senaryo karsilastirmasi ──────────────────────────────────────────

  const sn = (id, secim, ek = {}) => ({
    id, secimParmak: secim, baslik: "", satir: 1, bedel: 256,
    pKumeIci: null, kurulum: K.varsayilanKurulum(), ...ek,
  });

  dene("ayni kurulum tekrar kosulursa satir YERINDE yenilenir", () => {
    let l = [];
    l = S.senaryoEkle(l, sn("a", "s1", { bedel: 32 }));
    l = S.senaryoEkle(l, sn("b", "s1", { bedel: 64 }));
    l = S.senaryoEkle(l, sn("a", "s1", { bedel: 33 }));
    assert.equal(l.length, 2, "kopya satir eklendi");
    // Yeri korunmali: "a" hala ikinci sirada.
    assert.equal(l[1].id, "a");
    assert.equal(l[1].bedel, 33, "satir yenilenmedi");
  });

  dene("liste sinirlanir, en yenisi basta durur", () => {
    let l = [];
    for (let i = 0; i < 10; i++) l = S.senaryoEkle(l, sn(`id${i}`, "s1"), 6);
    assert.equal(l.length, 6);
    assert.equal(l[0].id, "id9");
  });

  // Uc test buradaydi ve ucu de `enUcuzGarantili`yi olcuyordu: "yalnizca
  // ayni secimden secilir", "garanti vermeyen daha ucuz satir en ucuz
  // sayilmaz", "kiyaslanacak sey yoksa null". Kaplama sokuldu
  // (docs/DUZ_SISTEME_GECIS.md); duzde ayni secim HER ZAMAN ayni bedeli
  // verir ve garanti diye bir secenek yok, yani o soru dejenere.
  //
  // Yerine gecen soru: odenen her kolon ne kadar kume-ici olasilik
  // aliyor? (`enIyiVerim`)

  dene("en iyi verim KOLON BASINA olasiliktan secilir, ucuzdan degil", () => {
    const l = [
      sn("ucuz", "s1", { bedel: 8, pKumeIci: 0.001 }),    // 1,25e-4 / kolon
      sn("verimli", "s2", { bedel: 64, pKumeIci: 0.02 }), // 3,13e-4 / kolon
      sn("pahali", "s3", { bedel: 512, pKumeIci: 0.03 }), // 5,86e-5 / kolon
    ];
    const e = S.enIyiVerim(l);
    assert.equal(e.id, "verimli", "en ucuz satir one cikti");
  });

  dene("olasiligi bilinmeyen satir verim kiyasina GIRMEZ", () => {
    const l = [
      sn("a", "s1", { bedel: 8, pKumeIci: null }),
      sn("b", "s2", { bedel: 64, pKumeIci: 0.02 }),
      sn("c", "s3", { bedel: 128, pKumeIci: 0.01 }),
    ];
    assert.equal(S.enIyiVerim(l).id, "b");
  });

  dene("kiyaslanacak sey yoksa null doner", () => {
    assert.equal(S.enIyiVerim([]), null);
    // Tek satir bir KIYAS degildir: yanina koyacak sey yok.
    assert.equal(S.enIyiVerim([sn("a", "s1", { pKumeIci: 0.5 })]), null);
    // Olasilik girilmemisse verim hesaplanamaz.
    assert.equal(
      S.enIyiVerim([sn("a", "s1"), sn("b", "s2")]),
      null,
    );
  });

  dene("senaryoYap: p_kume_ici YUZDEden 0-1'e cevrilir", () => {
    const r = {
      baslik: "x", satir_sayisi: 1, kolon_bedeli: 256,
      advanced: { exact: { p_kume_ici: 0.015, p_15: 0, p_14: 0, p_tek: 0 } },
    };
    const y = S.senaryoYap(r, K.varsayilanKurulum(), "id", "s1");
    assert.ok(Math.abs(y.pKumeIci - 0.00015) < 1e-9, `gelen ${y.pKumeIci}`);
    assert.equal(y.satir, 1, "duzde kupon tek satirdir");
    assert.equal(y.bedel, 256);
  });

  dene("olasilik girilmemisse pKumeIci null kalir (uydurulmaz)", () => {
    const r = {
      baslik: "x", satir_sayisi: 1, kolon_bedeli: 256, advanced: null,
    };
    const y = S.senaryoYap(r, K.varsayilanKurulum(), "id", "s1");
    assert.equal(y.pKumeIci, null);
  });

  // ── Sozlesme: types.ts ile backend govdesi ─────────────────────────
  //
  // NEDEN VAR: `lib/types.ts` 1000 satir ve ELLE bakiliyordu. Bir alan adi
  // backend'de degistiginde motor sapasaglam kalir, butun testler gecer ve
  // sayfa sessizce bos doner — tam da tip sisteminin yakalayamadigi hata
  // sinifi, cunku `istek<T>()` cevabi dogrulamadan `as T` ile kaliba
  // sokuyor. Asagidaki denetim o boslugu kapatir.
  //
  // TypeScript zaten devDependency; derleyici API'siyle arayuzler
  // OKUNUR (calisma aninda tip yok, o yuzden kaynak ayristirilir).

  const ts = iste("typescript");
  const tipKaynagi = readFileSync(join(kok, "lib", "types.ts"), "utf8");
  const tipAgaci = ts.createSourceFile(
    "types.ts", tipKaynagi, ts.ScriptTarget.ES2022, true,
  );

  /** Bir arayuzun KENDI alanlari ve genislettigi arayuzler. */
  const hamArayuzler = new Map();
  tipAgaci.forEachChild((d) => {
    if (!ts.isInterfaceDeclaration(d)) return;
    const alanlar = new Map();
    for (const uye of d.members) {
      if (!ts.isPropertySignature(uye) || !uye.name) continue;
      const ad = uye.name.getText(tipAgaci).replace(/^["']|["']$/g, "");
      // Tip METNI de saklaniyor: derinlemesine denetim ic ice arayuzu
      // buradan cozuyor. Once yalnizca `istegeBagli` tutuluyordu ve
      // denetim 1 SEVIYE derinde kaliyordu.
      alanlar.set(ad, {
        istegeBagli: !!uye.questionToken,
        tip: uye.type ? uye.type.getText(tipAgaci) : "",
        uye,
      });
    }
    const atalar = (d.heritageClauses ?? [])
      .filter((h) => h.token === ts.SyntaxKind.ExtendsKeyword)
      .flatMap((h) => h.types.map((t) => t.expression.getText(tipAgaci)));
    hamArayuzler.set(d.name.text, { alanlar, atalar });
  });

  /**
   * Miras COZULUR. `WeekDetail extends WeekRow` gibi durumlarda yalnizca
   * `members`a bakmak alanlarin yarisini kaciriyordu ve denetim yanlis
   * alarm veriyordu — ilk kosuda tam bunu yapti.
   */
  const arayuzler = new Map();
  const coz = (ad, gorulen = new Set()) => {
    if (arayuzler.has(ad)) return arayuzler.get(ad);
    const ham = hamArayuzler.get(ad);
    if (!ham || gorulen.has(ad)) return new Map();
    gorulen.add(ad);
    const birlesik = new Map();
    for (const ata of ham.atalar) {
      for (const [k, v] of coz(ata, gorulen)) birlesik.set(k, v);
    }
    for (const [k, v] of ham.alanlar) birlesik.set(k, v);
    arayuzler.set(ad, birlesik);
    return birlesik;
  };
  for (const ad of hamArayuzler.keys()) coz(ad);

  /**
   * Uc -> onu okuyan tip. Elle tutulan TEK esleme bu; gerisi uretilir.
   * Buradaki bir ucun tipi yoksa denetim sessizce atlamaz, PATLAR.
   */
  const ESLEME = {
    "GET /api/meta": "MetaResponse",
    "GET /api/health": "HealthReport",
    "GET /api/health/checks": "HealthChecksResponse",
    "GET /api/health/history": "HealthHistoryResponse",
    "POST /api/health/kupon": "KuponDenetimSonuc",
    "GET /api/stats": "StatsResponse",
    "GET /api/stats/<week>": "WeekDetail",
    "GET /api/backtest": "BacktestResponse",
    "GET /api/pazar": "PazarResponse",
    "GET /api/takimlar": "TakimlarResponse",
    "GET /api/tahmin": "TahminResponse",
    "GET /api/benzer": "BenzerResponse",
    "POST /api/solve": "SolveResponse",
  };

  /**
   * Bir alan TIP DUGUMUNDEN alan haritasi cikarir.
   *
   * Tek bir arayuz adi yetmiyor; depodaki tipler bilesik:
   *   `TahminBlogu & { ad: string }`   kesisim
   *   `TahminciSkoru | null`           birlesim
   *   `BacktestWeek[]`                 dizi
   * Ilk yazim yalnizca "tip metninde gecen ilk buyuk harfli ad"a bakiyordu
   * ve kesisimin inline yarisini kaciriyordu — yanlis alarm verdi
   * (`alternatif.ad` "tipte yok" dedi, oysa kesisimin oteki yarisindaydi).
   */
  const alanlariCoz = (dugum, derinlik = 0) => {
    if (!dugum || derinlik > 6) return null;
    if (ts.isParenthesizedTypeNode(dugum)) {
      return alanlariCoz(dugum.type, derinlik + 1);
    }
    if (ts.isArrayTypeNode(dugum)) {
      return alanlariCoz(dugum.elementType, derinlik + 1);
    }
    if (ts.isTypeLiteralNode(dugum)) {
      const m = new Map();
      for (const u of dugum.members) {
        if (!ts.isPropertySignature(u) || !u.name) continue;
        m.set(u.name.getText(tipAgaci).replace(/^["']|["']$/g, ""), {
          istegeBagli: !!u.questionToken,
          tip: u.type ? u.type.getText(tipAgaci) : "",
          uye: u,
        });
      }
      return m;
    }
    if (ts.isIntersectionTypeNode(dugum)) {
      // Kesisim: butun dallarin alanlari birlesir, zorunluluk korunur.
      const birlesik = new Map();
      let bulundu = false;
      for (const p of dugum.types) {
        const m = alanlariCoz(p, derinlik + 1);
        if (!m) continue;
        bulundu = true;
        for (const [k, v] of m) birlesik.set(k, v);
      }
      return bulundu ? birlesik : null;
    }
    if (ts.isUnionTypeNode(dugum)) {
      // Birlesim BASKA bir kural ister: bir alan ancak HER dalda varsa
      // zorunludur. `ErrorFreq = {...} | { skipped: true; reason: string }`
      // gibi "atlandi" varyantlarinda kesisim kurali yanlis alarm verir —
      // ilk yazimda tam bunu yapti.
      const dallar = dugum.types
        .map((p) => alanlariCoz(p, derinlik + 1))
        .filter((m) => m && m.size);
      if (!dallar.length) return null;
      const birlesik = new Map();
      for (const m of dallar) {
        for (const [k, v] of m) {
          const hepsinde = dallar.every((d) => d.has(k));
          const zorunlu = hepsinde && dallar.every((d) => !d.get(k).istegeBagli);
          const onceki = birlesik.get(k);
          birlesik.set(k, onceki ?? { ...v, istegeBagli: !zorunlu });
        }
      }
      return birlesik;
    }
    if (ts.isTypeReferenceNode(dugum)) {
      const ad = dugum.typeName.getText(tipAgaci);
      // `Record<string, X>`: alan adlari VERIDEN gelir, tipten degil.
      if (ad === "Record") return null;
      if (arayuzler.has(ad)) return arayuzler.get(ad);
      // `Array<X>`, `Partial<X>` gibi sarmalayicilar
      for (const arg of dugum.typeArguments ?? []) {
        const m = alanlariCoz(arg, derinlik + 1);
        if (m) return m;
      }
      return null;
    }
    return null;
  };

  /**
   * Sunucu govdesi ile arayuzu **ic ice** karsilastirir.
   *
   * ONCEDEN 1 SEVIYE DERINDI ve bu, iki gercek ayrismanin CI'dan yesil
   * gecmesine yol acti: `MetaResponse.engine_defaults` ust duzeyde vardi,
   * ama ICINDEKI `auto_ilp_limit` tipte yoktu (sunucu ilan ediyor, arayuz
   * gonderemiyor); `TahminciSkoru.fark` dort alan diyordu, sunucu yedi
   * gonderiyordu. Ust duzey anahtar tuttugu icin denetim ikisini de
   * gormedi.
   *
   * Diziler: ilk eleman ornek alinir (sozlesme uretimi zaten tek bir
   * gercek cagriyi ornekliyor, elemanlar ayni sekli tasir).
   */
  const karsilastir = (yol, govde, alanlar, hatalar, derinlik = 0) => {
    if (derinlik > 6 || !alanlar) return;
    for (const [k, v] of Object.entries(govde)) {
      if (!alanlar.has(k)) hatalar.push(`${yol}.${k} sunucuda VAR, tipte YOK`);
    }
    for (const [k, meta] of alanlar) {
      if (!meta.istegeBagli && !(k in govde)) {
        hatalar.push(`${yol}.${k} tipte ZORUNLU, sunucu gondermiyor`);
      }
    }
    for (const [k, v] of Object.entries(govde)) {
      const meta = alanlar.get(k);
      if (!meta) continue;
      let deger = v;
      if (Array.isArray(deger)) deger = deger[0];
      if (!deger || typeof deger !== "object") continue;
      const ic = alanlariCoz(meta.uye?.type);
      if (!ic || ic.size === 0) continue;
      karsilastir(`${yol}.${k}`, deger, ic, hatalar, derinlik + 1);
    }
  };

  for (const [uc, tipAdi] of Object.entries(ESLEME)) {
    dene(`sozlesme: ${uc} -> ${tipAdi}`, () => {
      const govde = SOZLESME.uclar[uc];
      assert.ok(govde, `sozlesmede ${uc} yok`);
      const alanlar = arayuzler.get(tipAdi);
      assert.ok(alanlar, `types.ts icinde ${tipAdi} arayuzu yok`);

      const hatalar = [];
      karsilastir(tipAdi, govde, alanlar, hatalar);
      assert.deepEqual(hatalar, [], hatalar.join("; "));
    });
  }

  // ── Sekme seridi (§6.8 G1: "sekme gecisinde dilim korunur") ──────────
  dene("sekme adresi dilimi tasir", () => {
    // Kirildiginda SESSIZ: `/istatistik?last=12`'den oranlara gecen
    // kullanici tum sezona duser ve iki sayfa ayni anda iki farkli kesiti
    // anlatir. Olculdu (tarayici, 2026-08): uc sekmede de last=12 kaldi.
    for (const s of T.ISTATISTIK_SEKMELERI) {
      assert.equal(T.sekmeAdresi(s.href, 12), `${s.href}?last=12`);
      assert.equal(T.sekmeAdresi(s.href, null), s.href);
      // 0 ve negatif "dilim yok" demektir, uydurma bir parametre degil.
      assert.equal(T.sekmeAdresi(s.href, 0), s.href);
      assert.equal(T.sekmeAdresi(s.href, -3), s.href);
    }
  });

  dene("sekme adresi SEZONU da tasir", () => {
    // Bu bekci `?last` icin vardi ve sezon eklendiginde SESSIZ bir arizayi
    // gormedi: serit yalnizca `?last` tasiyordu, yani 2023/24 secip
    // *Oranlar*a gecen kullanici varsayilan sezona dusuyordu. Ayni arizanin
    // ikinci turu; bu yuzden artik iki parametre birlikte sinaniyor.
    for (const s of T.ISTATISTIK_SEKMELERI) {
      assert.equal(T.sekmeAdresi(s.href, null, "2023_24"), `${s.href}?sezon=2023_24`);
      assert.equal(T.sekmeAdresi(s.href, 12, "2023_24"),
                   `${s.href}?last=12&sezon=2023_24`);
      // Sezon yoksa adres KIRLENMEZ — bos parametre eklenmez.
      assert.equal(T.sekmeAdresi(s.href, null, null), s.href);
      assert.equal(T.sekmeAdresi(s.href, null, ""), s.href);
      assert.equal(T.sekmeAdresi(s.href, 12, null), `${s.href}?last=12`);
    }
  });

  dene("sekme listesi ucu de kapsiyor", () => {
    const yollar = T.ISTATISTIK_SEKMELERI.map((s) => s.href);
    assert.deepEqual(yollar, [
      "/istatistik",
      "/istatistik/oranlar",
      "/istatistik/geri-test",
    ]);
    // Adresler benzersiz olmali: iki sekme ayni yola giderse `usePathname`
    // ikisini birden etkin gosterir.
    assert.equal(new Set(yollar).size, yollar.length);
  });

  dene("sozlesme: SINIRLARIN TAMAMI sunucuyla ayni", () => {
    // `lib/kurulum.ts` bu sinirlari SABIT tutmak zorunda (saf modul, istek
    // atamaz). Ayrisma gecmisi:
    //   · `mc_samples` burada 1.000.000, sunucuda 200.000 yaziyordu;
    //   · bekci o tek ornege baglandi ve KALAN ONU denetlenmedi;
    //   · denetlenmeyen onda gercek bir ayrisma vardi: `budget` burada
    //     10 M'e kirpiliyor, sunucu hicbir sinir ILAN ETMIYOR ve
    //     `/api/solve` onu SINIRSIZ aliyordu.
    // Bekci artik SINIFA bakiyor: sunucunun ilan ettigi her sinir, arayuzun
    // `SINIRLAR` tablosunda ayni degerle bulunmak zorunda.
    const sunucu = SOZLESME.sinirlar;
    const arayuz = K.SINIRLAR;

    // Sunucuya OZGU sinirlar: arayuz bunlari uygulamaz, yalnizca gosterir.
    // `fire_maliyet` bir kullanici girdisi degil, sunucunun HESAPLADIGI
    // maliyetin tavani (`meta.FIRE_MAX_MALIYET`) — arayuzde kirpilacak bir
    // alan yok. Liste bilerek kisa ve gerekceli: buyudugu gun bekci
    // anlamsizlasir.
    const SUNUCUYA_OZGU = new Set(["fire_maliyet"]);

    const eksik = Object.keys(sunucu)
      .filter((k) => !SUNUCUYA_OZGU.has(k))
      .filter((k) => !(k in arayuz));
    assert.deepEqual(eksik, [],
      `sunucunun ilan ettigi sinir arayuzde YOK: ${eksik.join(", ")}`);

    const fazla = Object.keys(arayuz).filter((k) => !(k in sunucu));
    assert.deepEqual(fazla, [],
      `arayuz sinir uyguluyor ama sunucu ILAN ETMIYOR: ${fazla.join(", ")}`);

    const ayrisan = [];
    for (const [ad, s] of Object.entries(sunucu)) {
      if (SUNUCUYA_OZGU.has(ad)) continue;
      const a = arayuz[ad];
      for (const alan of ["min", "max", "default"]) {
        if (!(alan in s)) continue;
        if (a[alan] !== s[alan]) {
          ayrisan.push(`${ad}.${alan}: arayuz=${a[alan]} sunucu=${s[alan]}`);
        }
      }
    }
    assert.deepEqual(ayrisan, [], ayrisan.join("; "));
  });

  dene("sozlesme: MAC_SAYISI ve SEMBOLLER sunucuyla ayni", () => {
    // Ikisi de iki tarafta SABIT yaziliydi ve hic karsilastirilmiyordu.
    // `lib/api.ts` `/api/benzer?oran=` dizesini `SEMBOLLER`den KONUMSAL
    // kuruyor: sunucu `symbols` sirasini degistirirse her oran ucluşu
    // sessizce yer degistirir ve hicbir yerde patlamaz.
    //
    // Sozlesme anlik goruntusu `/api/meta` icin DEGER degil SEKIL sakliyor
    // ("int", ["str"]), o yuzden karsilastirma `olculmus` blogundan yapilir:
    // ornek kupon sunucunun gercek ciktisidir.
    const kupon = SOZLESME.olculmus.ornek_kupon.split(",");
    assert.equal(kupon.length, TIP.MAC_SAYISI,
      `MAC_SAYISI=${TIP.MAC_SAYISI} ama sunucunun ornek kuponu ${kupon.length} mac`);

    // Kupondaki her isaret `SEMBOLLER` alfabesinden olmali.
    const alfabe = new Set(TIP.SEMBOLLER);
    const yabanci = [...new Set(kupon.join("").split(""))]
      .filter((c) => !alfabe.has(c));
    assert.deepEqual(yabanci, [],
      `sunucunun kuponunda SEMBOLLER disinda isaret var: ${yabanci.join(", ")}`);

    // Duzen de onemli: `/api/benzer?oran=` konumsal kuruluyor.
    assert.deepEqual([...TIP.SEMBOLLER], ["1", "0", "2"],
      "SEMBOLLER duzeni degismis — `lib/api.ts` oran dizesini KONUMSAL kuruyor");
  });

  console.log(`\nOK — ${gecen} arayuz denetimi gecti`);

// ─── yuzde/sayi gibi bicimleyiciler tek kaynakta mi ─────────────────────
//
// `app/pazarlar/page.tsx` `yuzde`yi YENIDEN YAZMISTI ve kanonik govdeden
// zayifti: yalnizca `v == null` eliyordu, `NaN`/`Infinity` elemiyordu — yani
// kapsanmayan bir banttaki bolme ekrana "%NaN" basardi. `/api/pazar` tam da
// null tasiyan uc. `lib/utils.ts` bu tekillestirmenin yapildigini yaziyordu;
// bir kopya hayatta kalmisti. Bekci sinifa bakar, tek dosyaya degil.
dene("bicimleyiciler lib/utils.ts'ten TURER (yeniden yazilmaz)", () => {
  const kok = join(dirname(fileURLToPath(import.meta.url)), "..");
  const adlar = ["yuzde", "sayi", "ondalik"];
  const bulunan = [];
  const gez = (dizin) => {
    for (const g of readdirSync(dizin, { withFileTypes: true })) {
      const yol = join(dizin, g.name);
      if (g.isDirectory()) { gez(yol); continue; }
      if (!/\.tsx?$/.test(g.name)) continue;
      const metin = readFileSync(yol, "utf8");
      // `@/lib/utils`ten ne getirilmis? Sarmalayici mesrudur: kanonik
      // govdeyi CAGIRIP bir argumani sabitler (`_yuzde(v, 0)` gibi).
      // Yasak olan, kanonigi hic getirmeden yeniden YAZMAK.
      const getirilen = new Set();
      for (const m of metin.matchAll(/import\s*\{([^}]*)\}\s*from\s*"@\/lib\/utils"/g)) {
        for (const parca of m[1].split(",")) {
          const ad = parca.trim().split(/\s+as\s+/).pop();
          if (ad) getirilen.add(ad.trim());
        }
      }
      for (const ad of adlar) {
        const yerel = new RegExp(
          `(?:^|\\n)\\s*(?:export\\s+)?(?:const|function)\\s+${ad}\\b[^\\n]*(?:\\n[^\\n]*){0,3}`);
        const m = yerel.exec(metin);
        if (!m) continue;
        const govde = m[0];
        const turemis = [...getirilen].some((g) => new RegExp(`\\b${g}\\b`).test(govde));
        if (!turemis) bulunan.push(`${g.name}:${ad}`);
      }
    }
  };
  for (const alt of ["app", "components"]) gez(join(kok, alt));
  assert.deepEqual(
    bulunan, [],
    `bicimleyici lib/utils.ts'ten TUREMEDEN yeniden yazilmis: ${bulunan.join(", ")}`,
  );
});

// ─── capraz dil: saglayici etiketi iki dilde AYNI mi ────────────────────
dene("saglayici etiketi Python ile birebir ayni", () => {
  // Harita tek kaynak (`spor_toto.odds.SAGLAYICI_ADLARI`) ama BICIMLEYICI
  // iki dilde iki govde ve ayrismislardi: soneksiz bir anahtarda
  // ("pinnacle") Python `else` dalina dusup "kapanış" UYDURUYOR, TypeScript
  // uydurmuyordu. Yani ayni fiyat kaynagi rapor sayfasinda ve arayuzde iki
  // farkli adla gorunuyordu.
  //
  // Besleme Python'un GERCEK ciktisini tasiyor; burada arayuzun onu birebir
  // yeniden urettigi dogrulanir. Sinir durumlar (soneksiz, bilinmeyen)
  // bilerek listede.
  const ornekler = BESLEME.saglayici_ornekleri;
  assert.ok(ornekler && Object.keys(ornekler).length >= 6,
    "beslemede `saglayici_ornekleri` yok — Python tarafi eskimis olabilir");
  const ayrisan = [];
  for (const [kind, beklenen] of Object.entries(ornekler)) {
    const bulunan = ST.saglayiciAdi(kind);
    if (bulunan !== beklenen) {
      ayrisan.push(`${kind}: arayuz=${bulunan} python=${beklenen}`);
    }
  }
  assert.deepEqual(ayrisan, [], ayrisan.join("; "));
  // Bos/None girdide iki taraf da ayni sozu vermeli.
  assert.equal(ST.saglayiciAdi(""), "bilinmiyor");
  assert.equal(ST.saglayiciAdi(null), "bilinmiyor");
});

// ─── font geri dusus olculeri Next'in KENDI tablosuyla ayni mi ──────────
dene("Bodoni geri dusus olculeri Next'in tablosundan TURETILMIS", () => {
  // `next/font` bu aile icin olcu uyumlu geri dusus URETEMIYOR: Next 14'un
  // iki ic tablosu celisiyor — font listesinde aile "Bodoni Moda", olcu
  // tablosunda ise yalnizca "bodoniModa11pt" var. Arama ilk addan gidiyor,
  // bulamiyor ve SESSIZCE vazgeciyor (cikis kodu bozulmuyor, yalnizca
  // soguk derlemede iki uyari satiri). Sonucu uretilen CSS'te gorunuyordu:
  // tek bir `size-adjust` bile yoktu, yani `display: swap` her sayfa
  // acilisinda baslik yuzunde gorunur bir sicrama uretiyordu.
  //
  // Yuz `globals.css`te ELLE tanimli ama SAYILARI elle uydurulmus DEGIL.
  // Bu denetim onlari Next'in kendi olcu tablosundan, Next'in kendi
  // formuluyle YENIDEN HESAPLAYIP karsilastirir: tablo guncellenirse ya da
  // taban yuz (Georgia) degisirse kapi kirmizi yanar.
  const iste = createRequire(import.meta.url);
  const olcuYolu = iste.resolve("next/dist/server/capsize-font-metrics.json");
  const olcu = JSON.parse(readFileSync(olcuYolu, "utf8"));
  const b = olcu.bodoniModa11pt;
  const g = olcu.georgia;
  assert.ok(b && g, "Next olcu tablosunda bodoniModa11pt ya da georgia yok");

  const sizeAdjust = (b.xWidthAvg / b.unitsPerEm) / (g.xWidthAvg / g.unitsPerEm);
  const yuzde = (x) => `${(x * 100).toFixed(2)}%`;
  const beklenen = {
    "size-adjust": yuzde(sizeAdjust),
    "ascent-override": yuzde(b.ascent / (b.unitsPerEm * sizeAdjust)),
    "descent-override": yuzde(Math.abs(b.descent) / (b.unitsPerEm * sizeAdjust)),
    "line-gap-override": yuzde(b.lineGap / (b.unitsPerEm * sizeAdjust)),
  };

  const css = readFileSync(join(kok, "app", "globals.css"), "utf8");
  const blok = css.match(/@font-face\s*\{[^}]*Bodoni Moda Fallback[^}]*\}/);
  assert.ok(blok, "globals.css icinde 'Bodoni Moda Fallback' yuzu yok");

  const ayrisan = [];
  for (const [ozellik, deger] of Object.entries(beklenen)) {
    const bulunan = blok[0].match(new RegExp(`${ozellik}\\s*:\\s*([^;]+);`));
    if (!bulunan) { ayrisan.push(`${ozellik}: CSS'te yok`); continue; }
    if (bulunan[1].trim() !== deger) {
      ayrisan.push(`${ozellik}: css=${bulunan[1].trim()} hesap=${deger}`);
    }
  }
  assert.deepEqual(ayrisan, [],
    `font geri dusus olculeri Next tablosundan ayrismis — ${ayrisan.join("; ")}`);

  // Yuz yalnizca tanimli olmasin, KULLANILIYOR da olsun.
  const tw = readFileSync(join(kok, "tailwind.config.ts"), "utf8");
  assert.ok(/display:\s*\[[^\]]*Bodoni Moda Fallback/s.test(tw),
    "geri dusus yuzu tanimli ama `display` yiginina konmamis");
});

} finally {
  rmSync(cikti, { recursive: true, force: true });
}
