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
import { mkdtempSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const kok = join(dirname(fileURLToPath(import.meta.url)), "..");
// Cikti /tmp'e DEGIL frontend/ altina yazilir: `lib/utils.ts` clsx ve
// tailwind-merge'e bagli, repo disindaki bir dizin node_modules'i goremez.
const cikti = mkdtempSync(join(kok, ".kurulum-check-"));

try {
  // CommonJS'e cevrilir: tsc `./types` importlarini uzantisiz birakir ve
  // Node'un ESM cozumleyicisi uzantisiz yolu bulamaz.
  execFileSync(
    "npx",
    [
      "tsc", "lib/kurulum.ts", "lib/kume-ici.ts", "lib/senaryo.ts",
      "lib/utils.ts", "lib/types.ts",
      "--outDir", cikti,
      "--module", "commonjs", "--target", "es2022", "--skipLibCheck",
    ],
    { cwd: kok, stdio: "inherit" },
  );

  const iste = createRequire(import.meta.url);
  const K = iste(join(cikti, "kurulum.js"));
  const Z = iste(join(cikti, "kume-ici.js"));
  const S = iste(join(cikti, "senaryo.js"));

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
  dene("motor ayarlari ve mod gidis-donus", () => {
    const k = K.varsayilanKurulum();
    k.mode = "butce";
    k.budget = 4096;
    k.planCount = 12;
    k.planApply = 7;
    k.variant = 3;
    k.fireMax = 0;
    k.kati = true;
    k.eng = { trials: 9, ls_iters: 12345, seed: 7, time_limit: 90, block_limit: 512, exact_limit: 1024 };
    const geri = K.kurulumuCoz(K.kurulumuKodla(k)).kurulum;
    assert.equal(geri.mode, "butce");
    assert.equal(geri.budget, 4096);
    assert.equal(geri.planCount, 12);
    assert.equal(geri.planApply, 7);
    assert.equal(geri.variant, 3);
    assert.equal(geri.fireMax, 0);
    assert.equal(geri.kati, true);
    assert.deepEqual(geri.eng, k.eng);
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
    assert.equal(geri.kurulum.mode, "fix16");
    assert.ok(geri.atlanan.includes("maç seçimleri"));
    assert.ok(geri.atlanan.includes("mod"));
    assert.ok(geri.atlanan.includes("olasılıklar"));
    assert.ok(geri.atlanan.includes("motor ayarları"));
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
    const geri = K.kurulumuCoz("?s=111111111111111&v=-5&f=99&pc=999&pa=999").kurulum;
    assert.equal(geri.variant, 0);
    assert.equal(geri.fireMax, 2);
    assert.equal(geri.planCount, 50);
    assert.ok(geri.planApply <= geri.planCount);
  });

  // ── Kume-ici hesabi ──────────────────────────────────────────────────

  // README'nin ornek kuponu + check.sh'in ornek olasiliklari. Ikisi de
  // depoda zaten var, yani bu vaka uydurulmus degil.
  const ORNEK_SEC = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
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
    // backend olasilik_raporu -> p_kume_ici = 0.00014902 (olculdu)
    assert.ok(
      Math.abs(h.p - 0.00014902) < 1e-8,
      `beklenen 0.00014902, gelen ${h.p}`,
    );
  });

  dene("en zayif uc mac dogru secilir", () => {
    const h = Z.kumeIciHesapla(ORNEK_SEC, ORNEK_P);
    // 7. mac banko "2" (0.20), 14. mac banko "2" (0.25), 5. mac banko "0" (0.40)
    assert.deepEqual(h.zayiflar.map((i) => i + 1).sort((a, b) => a - b), [5, 7, 14]);
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

  dene("kaplama alt siniri backend'in alt_sinir'iyla ayni", () => {
    // Ornek kupon: 8 cifte -> uzay 256, top 9, alt sinir 29 (backend olculdu)
    const a = Z.kaplamaAltSiniri(ORNEK_SEC);
    assert.equal(a.uzay, 256);
    assert.equal(a.topBoyutu, 9);
    assert.equal(a.altSinir, 29);
  });

  dene("uclu maclar top boyutuna 2 katar", () => {
    const a = Z.kaplamaAltSiniri([["1", "0", "2"], ["1", "0"], ["1"]]);
    assert.equal(a.uzay, 6);
    assert.equal(a.topBoyutu, 1 + 2 + 1 + 0);
    assert.equal(a.altSinir, Math.ceil(6 / 4));
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
    id, secimParmak: secim, mode: "fix16", baslik: "", satir: 16, bedel: 32,
    garanti: true, acik: 0, altSinir: 29, pKumeIci: null,
    kurulum: K.varsayilanKurulum(), ...ek,
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

  dene("en ucuz garantili YALNIZCA ayni secimden secilir", () => {
    const l = [
      sn("a", "s1", { bedel: 32, mode: "fix16" }),
      sn("b", "s2", { bedel: 8, mode: "fix16" }),   // baska secim: sayilmaz
      sn("c", "s1", { bedel: 29, mode: "auto" }),
    ];
    const e = S.enUcuzGarantili(l, "s1");
    assert.equal(e.id, "c", "baska secimden bir satir secildi");
    assert.equal(e.bedel, 29);
  });

  dene("garanti vermeyen daha ucuz satir 'en ucuz' sayilmaz", () => {
    const l = [
      sn("a", "s1", { bedel: 32, garanti: true }),
      sn("b", "s1", { bedel: 12, garanti: false, acik: 40, mode: "maxcov" }),
    ];
    const e = S.enUcuzGarantili(l, "s1");
    assert.equal(e.id, "a", "garantisiz satir one cikti");
  });

  dene("kiyaslanacak sey yoksa null doner", () => {
    assert.equal(S.enUcuzGarantili([], "s1"), null);
    assert.equal(S.enUcuzGarantili([sn("a", "s2")], "s1"), null);
  });

  dene("senaryoYap: p_kume_ici YUZDEden 0-1'e cevrilir", () => {
    const r = {
      mode: "fix16", baslik: "x", satir_sayisi: 16, kolon_bedeli: 32,
      acik: 0, worst: 1, alt_sinir: 29,
      advanced: { exact: { p_kume_ici: 0.015, p_15: 0, p_14: 0, p_tek: 0 } },
    };
    const y = S.senaryoYap(r, K.varsayilanKurulum(), "id", "s1");
    assert.ok(Math.abs(y.pKumeIci - 0.00015) < 1e-9, `gelen ${y.pKumeIci}`);
    assert.equal(y.garanti, true);
  });

  dene("acik nokta varsa garanti YOK sayilir", () => {
    const r = {
      mode: "maxcov", baslik: "x", satir_sayisi: 8, kolon_bedeli: 12,
      acik: 40, worst: 2, alt_sinir: 29, advanced: null,
    };
    const y = S.senaryoYap(r, K.varsayilanKurulum(), "id", "s1");
    assert.equal(y.garanti, false);
    assert.equal(y.pKumeIci, null);
  });

  console.log(`\nOK — ${gecen} arayuz denetimi gecti`);
} finally {
  rmSync(cikti, { recursive: true, force: true });
}
