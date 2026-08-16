/**
 * Kurulum kodlamasinin gidis-donus denetimi.
 *
 * NEDEN VAR: kodlama sabit genislikli ve tek bir alan tasinca ONDAN SONRAKI
 * TUM maclar kayar — yani hata bir maci degil, kuponun yarisini bozar ve
 * hicbir yerde patlamaz, sessizce baska bir kupon uretir. Ilk surumde tam
 * bunu yapti: binde birlik olasilik 0..1000 araligindadir, banko bir macta
 * 1000 dort basamak eder ve `padStart(3)` alani 4 karaktere tasirdi.
 *
 * Bagimlilik eklemez: tsc (zaten devDependency) modulu gecici bir dizine
 * cevirir, dosya duz node ile kosar.
 *
 * Calistirma: node scripts/kurulum-check.mjs
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
      "tsc", "lib/kurulum.ts", "lib/utils.ts", "lib/types.ts",
      "--outDir", cikti,
      "--module", "commonjs", "--target", "es2022", "--skipLibCheck",
    ],
    { cwd: kok, stdio: "inherit" },
  );

  const K = createRequire(import.meta.url)(join(cikti, "kurulum.js"));

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

  console.log(`\nOK — ${gecen} kurulum denetimi gecti`);
} finally {
  rmSync(cikti, { recursive: true, force: true });
}
