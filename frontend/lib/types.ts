/**
 * Python API'sinin sozlesmesi.
 *
 * Onceki arayuzde `result` dogrudan `Record<string, unknown>` idi; yani
 * backend'in dondurdugu ~20 alanin hicbiri tipli degildi ve arayuzun
 * backend'i dogru okuyup okumadigini soyleyecek hicbir sey yoktu.
 * Bu dosya o boslugu kapatir — kaynak: backend/web_app.py.
 */

export type Sembol = "1" | "0" | "2";

/** Kupon duzeni. Alfabetik siralama ("01") okuma hatasi yaptirir. */
export const SEMBOLLER: readonly Sembol[] = ["1", "0", "2"] as const;
export const MAC_SAYISI = 15;

// ─── /api/meta ────────────────────────────────────────────────────────────

export type ModeId =
  | "fix16" | "auto" | "exact" | "block" | "heuristic" | "butce" | "maxcov";

export interface ModeInfo {
  id: ModeId;
  label: string;
  aciklama: string;
  /** false ise bu mod 14-garanti VERMEZ (maxcov). */
  garanti: boolean;
  needs_budget: boolean;
  needs_scipy: boolean;
}

export interface BayesPresetInfo {
  id: string;
  prior_strength: number;
  evidence_strength: number;
}

export interface EngineDefaults {
  trials: number;
  ls_iters: number;
  seed: number;
  time_limit: number;
  block_limit: number;
  exact_limit: number;
}

export interface Limit { min: number; max: number; default?: number }

export interface MetaResponse {
  version: string;
  has_scipy: boolean;
  match_count: number;
  symbols: Sembol[];
  modes: ModeInfo[];
  bayes_presets: BayesPresetInfo[];
  engine_defaults: EngineDefaults;
  limits: Record<string, Limit>;
}

// ─── POST /api/solve — istek ──────────────────────────────────────────────

export type ProbRow = Record<Sembol, number>;

export interface SolveRequest {
  picks?: string;
  matches?: Sembol[][];
  mode?: ModeId;
  variant?: number;
  budget?: number;
  /** Butce modu: kac plan uretilsin / hangisi uygulansin (1 tabanli). */
  plan_count?: number;
  plan_apply?: number;
  kati?: boolean;
  probs?: ProbRow[];
  use_bayes?: boolean;
  bayes_preset?: string | null;
  prior_strength?: number;
  evidence_strength?: number;
  mc_samples?: number;
  /** 0 = fire analizi kapalı, 1 = yalnızca 1-fire, 2 = ikisi de. */
  fire_max?: number;
  // Motor ayarlari
  trials?: number;
  ls_iters?: number;
  seed?: number;
  time_limit?: number;
  block_limit?: number;
  exact_limit?: number;
}

// ─── POST /api/solve — cevap ──────────────────────────────────────────────

export interface CouponRow {
  /** 15 hucre; cok isaretli olanlar "10", "102" gibi. */
  cells: string[];
  /** Bu satirin kac KOLONA mal oldugu. Satir != kolon. */
  cost: number;
}

export interface DistItem {
  d: number;
  dogru: number;
  label: string;
  count: number;
  pct: string;
}

export interface UniformProb { count: number; pct: string }

/**
 * DIKKAT — BIRIM: bu blogun tum alanlari YUZDE'dir (sunucu `100 *`
 * uygulayip yollar), oysa `MarkovBlock` icindeki ayni buyuklukler 0-1
 * OLASILIK'tir. Ayni cevapta ayni sey iki birimde donuyor; 100 kat
 * yanilmak icin tek gereken bunu bilmemek.
 */
export interface ExactProb {
  /** Yüzde. `markov.error_budget.p_kume_ici` ile aynı büyüklük ama × 100. */
  p_kume_ici: number;
  p_15: number;
  p_14: number;
  p_tek: number;
}

export interface McRate {
  p: number;
  pct: number;
  se: number;
  ci95: number;
  count: number;
}

export interface MonteCarlo {
  n_samples: number;
  kume_ici: McRate;
  p15: McRate;
  p14: McRate;
  p13: McRate;
  p12: McRate;
  warning?: string;
}

export interface Advanced {
  exact: ExactProb;
  monte_carlo: MonteCarlo;
  /** Olasiliklar dogrudan kullanicidan mi, Bayes posterior'undan mi geldi. */
  source: "user_probs" | "bayes_posterior";
}

export interface BayesMatch {
  mac: number;
  prior: ProbRow;
  evidence: ProbRow;
  posterior: ProbRow;
  kl: number;
  kl_label: string;
}

export interface BayesTopShift {
  mac: number;
  kl: number;
  kl_label: string;
  prior: ProbRow;
  posterior: ProbRow;
}

export interface BayesSummary {
  n: number;
  mean_kl_prior_post: number;
  mean_kl_label: string;
  top_shifts: BayesTopShift[];
  guide: { alpha: string; n: string; kl: string };
}

export interface BayesBlock {
  prior_strength: number;
  evidence_strength: number;
  summary: BayesSummary;
  matches: BayesMatch[];
}

export interface Survival {
  states: string[];
  /** k mac sonra hala secim kumesinde olma olasiligi (k = 0..15). */
  p_in_after: number[];
  p_survive: number;
}

/** BIRIM: bu blokta olasiliklar 0-1'dir — `ExactProb` yuzde donerken. */
export interface ErrorBudget {
  states: string[];
  p_final: { "0": number; "1": number; "2+": number };
  /** Kume ici olup en fazla 1 hatali olma olasiligi. */
  p_garanti: number;
  p_kume_ici: number;
  p_in_and_garanti: number;
  /** Kapsama tam degilse bu > 0 olur ve garanti gecerli degildir. */
  acik_nokta?: number;
  tam_kaplama?: boolean;
  method: string;
}

export interface MarkovBlock {
  survival: Survival;
  error_budget: ErrorBudget;
  summary: {
    p_kume_ici: number;
    p_garanti_path: number;
    p0: number;
    p1: number;
    p2plus: number;
    method: string;
  };
}

export interface ErrorFreqItem { mac: number; count: number; pct: number }

export interface ErrorFreq {
  d1: ErrorFreqItem[];
  d2: ErrorFreqItem[];
  n1: number;
  n2: number;
}

// ─── Fire (seçim DIŞI) ────────────────────────────────────────────────────

export type FireTip = "banko" | "double" | "triple";

export interface FireTypeStat {
  n: number;
  /** { "14": adet, "13": adet, … } */
  scores: Record<string, number>;
  pct: Record<string, number>;
}

export interface FireMatchStat {
  mac: number;
  type: FireTip;
  n: number;
  /** Üçlü (kapama) maçlar fire üretemez: küme dışı sembolleri yoktur. */
  can_fail: boolean;
  scores: Record<string, number>;
  pct: Record<string, number>;
}

export interface FireBlock {
  n: number;
  scores: Record<string, number>;
  pct: Record<string, number>;
  /** Fire türüne göre: banko / double / triple, fire2'de "banko+double" gibi. */
  by_type: Record<string, FireTypeStat>;
  by_match: FireMatchStat[];
  min_best: number | null;
  max_best: number | null;
  p_ge_14: number;
  p_ge_13: number;
  p_ge_12: number;
}

/**
 * Seçim DIŞI fire raporu — 14-garantinin geçerli OLMADIĞI bölge.
 * `skipped` true ise hesap bilerek atlanmıştır; `reason` nedenini söyler.
 */
export interface FireReport {
  note?: string;
  fire1?: FireBlock;
  fire2?: FireBlock;
  skipped: boolean;
  maliyet: number;
  fire_max: number;
  esik?: number;
  reason?: string;
}

export interface ButcePlan {
  index: number;
  bedel: number;
  satir: number;
  selections: string[];
  degisiklikler: string[];
  /**
   * YUZDE (0-100), 3 basamaga yuvarlanmis — `web_app._plan_to_dict` zaten
   * `100 *` uygular. Bu alanin birimi hicbir yerde yazmiyordu ve depoda
   * ayni adin iki birimi var: `ExactProb.p_kume_ici` yuzde,
   * `ErrorBudget.p_kume_ici` 0-1. Karistirmak 100 kat hata demektir.
   */
  p_kume_ici: number | null;
  secili: boolean;
}

export interface SolveResult {
  baslik: string;
  notlar: string[];
  uyarilar?: string[];
  mode?: ModeId;
  bayes_preset?: string | null;

  satir_sayisi: number;
  /** Odenecek tutar budur. satir_sayisi ile karistirilmamali. */
  kolon_bedeli: number;
  alt_sinir: number;
  guaranteed: boolean;
  worst: number;
  acik: number;

  rows: CouponRow[];
  dist: DistItem[];
  probs: Record<"15" | "14" | "13" | "12", UniformProb>;

  advanced: Advanced | null;
  bayes: BayesBlock | null;
  markov: MarkovBlock | null;
  error_freq: ErrorFreq | null;
  fire: FireReport | null;
  butce_planlari?: ButcePlan[];

  stat_lines: string[];
  match_count: number;
  total_space: number;
  has_scipy: boolean;
  run_log_text?: string;
}

export interface SolveResponse {
  ok: boolean;
  error: string | null;
  result: SolveResult | null;
  run_log_text: string;
  version: string;
}

// ─── /api/stats ───────────────────────────────────────────────────────────

export interface StatsMeta {
  season: string;
  date_from: string;
  date_to: string;
  weeks: number;
  matches: number;
  source: string;
  rule: string;
  generated_at: string;
  /** Dilimin ilk/son hafta numarasi ve `?last=N` ile kirpilip kirpilmadigi. */
  week_from: number | null;
  week_to: number | null;
  sliced: boolean;
}

export interface Band {
  avg: number;
  median: number;
  min: number;
  max: number;
  std: number;
  above_mean: number;
  above_n: number;
  above_gap: number;
  below_mean: number;
  below_n: number;
  below_gap: number;
}

export interface Streak {
  symbol: string;
  start: number;
  length: number;
}

/** Kupondaki tek maç. `code` skorun kendisinden türer. */
export interface Mac {
  no: number;
  home: string;
  away: string;
  /** "2025-12-19 17:00" — kaynaktaki başlama saati (UTC). */
  kickoff: string;
  hg: number | null;
  ag: number | null;
  code: Sembol | "";
}

export interface WeekRow {
  week: number;
  close_date: string;
  season: string;
  n1: number;
  n0: number;
  n2: number;
  /** 15 karakterlik sonuc dizisi, ornek "120021012210020". */
  results: string;
  /** Diziden turetilen sayimlar — n1/n0/n2 ile ayni, sembolle anahtarli. */
  counts: Record<Sembol, number>;
  top: Sembol;
  /** Hafta icindeki en uzun ayni-sembol serisi. */
  max_streak: Streak;
  complete: boolean;
  /** Dosyadaki hazir n1/n0/n2 ile dizi ortusuyor mu. */
  consistent: boolean;
  reported_counts: Record<Sembol, number> | null;
  /** Haftanin mac listesi — takim adlari, saat, skor. */
  matches: Mac[];
  /** Mac listesinin kodlari `results` dizisiyle sirasiyla ortusuyor mu. */
  matches_match_results: boolean;
}

/** Kuponun 1..15 sirasindaki bir mac icin sezon dagilimi. */
export interface PositionStat {
  pos: number;
  counts: Record<Sembol, number>;
  pct: Record<Sembol, number>;
  n: number;
  top: Sembol | "";
}

export interface Analytics {
  positions: PositionStat[];
  transitions: {
    counts: Record<Sembol, Record<Sembol, number>>;
    pct: Record<Sembol, Record<Sembol, number>>;
    row_totals: Record<Sembol, number>;
    n: number;
    repeat_pct: number;
  };
  distribution: Record<Sembol, Array<{ count: number; weeks: number; pct: number }>>;
  streaks: {
    by_symbol: Record<Sembol, { length: number; week: number | null; start: number }>;
    top: Array<{ week: number; symbol: Sembol; start: number; length: number }>;
    avg_week_max: number;
  };
  extremes: Record<
    Sembol,
    {
      max: { week: number; value: number; results: string } | null;
      min: { week: number; value: number; results: string } | null;
    }
  >;
  recent: {
    window: number;
    weeks: number[];
    avg: Record<Sembol, number>;
    delta: Record<Sembol, number>;
  };
}

/**
 * Veri seti kendini denetler: dosyadaki hazir sayim ile 15 karakterlik dizi
 * catistiginda fark GIZLENMEZ, buradan raporlanir.
 */
export interface DataQuality {
  source: string;
  weeks_total: number;
  weeks_with_matches: number;
  count_conflicts: Array<{
    week: number;
    close_date: string;
    reported: Record<Sembol, number> | null;
    derived: Record<Sembol, number>;
  }>;
  /** Mac listesi ile `results` dizisi ortusmeyen haftalar. */
  match_conflicts: number[];
  weeks_without_matches: number[];
  incomplete_weeks: number[];
  duplicate_results: Array<{ results: string; weeks: number[] }>;
  ok: boolean;
}

/**
 * Tek maçın maç sonucu (1X2) oranı. Arşivdeki diğer pazarlar (alt/üst, Asya
 * handikap) arayüze gelmez; onlar analiz katmanı içindir.
 */
export interface MacOran {
  odds: Record<Sembol, number>;
  /** Marj arındırılmış, toplamı 1 olan olasılıklar. */
  probs: Record<Sembol, number>;
  favourite: Sembol;
  hit: boolean;
  /** Bahisçi payı (overround), 0.0758 = %7,58. */
  margin: number;
  book: string;
  closing: boolean;
}

export interface OddsSummary {
  matches: number;
  with_odds: number;
  coverage_pct: number;
  favourite_hit: number;
  favourite_miss: number;
  favourite_hit_pct: number;
  favourite_split: Record<Sembol, number>;
  /** Favori TUTTUĞUNDA gerçekleşen sonuçlar; "0" daima 0'dır. */
  outcome_when_hit: Record<Sembol, number>;
  /** Favori TUTMADIĞINDA gerçekleşen sonuçlar. */
  outcome_when_miss: Record<Sembol, number>;
  /** Favori (satır) × gerçekleşen (sütun). */
  cross: Record<Sembol, Record<Sembol, number>>;
  /** Favorinin karşı tarafının kazandığı maç sayısı (beraberlik hariç). */
  underdog_wins: number;
  /** Favori oranı bandına göre isabet — banko kararının dayanağı. */
  favourite_bands: Array<{
    lo: number;
    hi: number | null;
    label: string;
    n: number;
    hit: number;
    miss: number;
    /** `miss`in beraberlikten gelen kısmı. */
    draw: number;
    /** `miss`in karşı tarafın kazanmasından gelen kısmı. */
    upset: number;
    hit_pct: number;
    miss_pct: number;
    draw_pct: number;
    upset_pct: number;
  }>;
  /**
   * Çift (ilk iki sembol) işaretlemek sonucu ne sıklıkla kapsıyor.
   * `model_pct` piyasanın söylediği, `in_two_pct` gerçekleşen kapsamadır.
   */
  set_coverage: Array<{
    lo: number;
    hi: number | null;
    label: string;
    n: number;
    model_pct: number;
    in_two: number;
    in_two_pct: number;
    /** Aynı bantta banko yapılsaydı: tek sembolün tutma sayısı. */
    in_one: number;
    in_one_pct: number;
    low_sample: boolean;
  }>;
  /** Favori ile ikincinin olasılık farkına göre beraberlik oranı. */
  draw_profile: Array<{
    lo: number;
    hi: number | null;
    label: string;
    n: number;
    draw: number;
    draw_pct: number;
    model_draw_pct: number;
    favourite_hit_pct: number;
    low_sample: boolean;
  }>;
  /** Lig lig beraberlik ve favori isabeti. Etiket oran arşivinden gelir. */
  leagues: Array<{
    league: string;
    label: string;
    n: number;
    share_pct: number;
    /** Kupon başına ortalama kaç maç bu ligden geliyor. */
    per_week: number;
    draw: number;
    draw_pct: number;
    favourite_hit: number;
    favourite_hit_pct: number;
    low_sample: boolean;
  }>;
  /**
   * Hafta hafta "piyasa ne kadar yanıldı". Brier = Σ(p − gerçekleşme)²;
   * 0 kusursuz, 2 tam ters. Favori isabetinden daha dürüsttür: 1,05 oranlı
   * favorinin tutmasıyla 2,40 oranlınınki aynı sayılmaz.
   */
  weekly_brier: Array<{
    week: number;
    n: number;
    brier: number;
    favourite_hit: number;
    favourite_hit_pct: number;
    /** 15 maçın hepsinde oran yoksa hafta karşılaştırmaya girmemeli. */
    partial: boolean;
  }>;
  brier_avg: number;
  /** Üç sembole eşit olasılık verilseydi çıkacak skor — referans çizgi. */
  brier_uniform: number;
  /** Bu maç sayısının altındaki satırlar `low_sample` işaretlenir. */
  low_sample_at: number;
  outcome_totals: Record<Sembol, number>;
  avg_margin_pct: number;
  /** Olasılık kovası başına model vs gerçekleşme. */
  calibration: Array<{
    lo: number;
    hi: number;
    n: number;
    model_pct: number;
    actual_pct: number;
  }>;
  books: string[];
  note: string;
}

export interface StatsResponse {
  meta: Partial<StatsMeta>;
  totals: Partial<Record<Sembol | "pct_1" | "pct_0" | "pct_2", number>>;
  weekly_avg: Partial<Record<Sembol, number>>;
  bands: Partial<Record<Sembol, Band>>;
  data_quality: DataQuality;
  analytics: Analytics;
  /** Maç sonucu oranı özeti; arşiv yoksa null. */
  odds: OddsSummary | null;
  weeks: WeekRow[];
  /** Uygulanan dilim (`?last=N`); tum sezon icin null. */
  last: number | null;
  error?: string | null;
}

/** /api/stats/<week> — WeekRow'un ustune komsular ve sezon bagi. */
export interface WeekDetail extends WeekRow {
  prev_week: number | null;
  next_week: number | null;
  cells: Array<{ pos: number; symbol: Sembol }>;
  runs: Streak[];
  season_avg: Record<Sembol, number>;
  delta_vs_avg: Record<Sembol, number>;
  rank: Record<Sembol, { rank: number; of: number }>;
  position_stats: PositionStat[];
  /** Maç numarasına göre 1X2 oranı; oranı bulunamayan maç listede yoktur. */
  odds: Record<string, MacOran>;
  /** Bu haftada kapanış favorisinin tuttuğu maç sayısı. */
  odds_hit: number;
}

// ─── /api/backtest ────────────────────────────────────────────────────────

/** Bir eşik çiftinin sezon özeti. `sweep` satırları da bu biçimdedir. */
export interface BacktestSeason {
  weeks: number;
  /** Seçim uzayı sınırı aşıldığı için çözülemeyen hafta sayısı. */
  skipped: number;
  /** Gerçek sonucun 15 maçta da işaretlerin içinde kaldığı hafta sayısı. */
  in_set: number;
  in_set_pct: number;
  hit15: number;
  hit14: number;
  hit13: number;
  hit14_pct: number;
  /** Wilson %95 güven aralığı — 41 hafta küçük örneklem. */
  hit14_ci: [number, number];
  columns_total: number;
  columns_avg: number;
  columns_max: number;
  /** 14+ tutan hafta başına kolon bedeli; hiç tutmadıysa null. */
  columns_per_hit14: number | null;
  rows_avg: number;
  banko_avg: number;
  double_avg: number;
  triple_avg: number;
  misses_total: number;
  all_guaranteed: boolean;
}

export interface SweepRow extends BacktestSeason {
  banko: number;
  uclu: number;
}

export interface BacktestWeek {
  week: number;
  close_date: string;
  skipped: boolean;
  /** Hafta çözülemediyse nedeni; aksi halde tanımsız. */
  reason?: string;
  /** 15 maçın işaretleri: "1", "10", "102". */
  picks: string[];
  banko: number;
  double: number;
  triple: number;
  /** Ödenecek tutarın ölçüsü. Satır sayısıyla karıştırılmamalı. */
  columns: number;
  rows: number;
  engine: string;
  guaranteed: boolean;
  /** 15 maçın tamamı işaretlerin içinde mi kaldı. */
  in_set: boolean;
  misses: number;
  /** Küme dışı kalan maçların 1 tabanlı numaraları. */
  miss_at: number[];
  /** Kolonların içinde en çok tutturanın doğru sayısı. */
  best: number;
  results: string;
}

/**
 * Eşik o haftayı GÖRMEDEN seçildiğinde ne oldu (leave-one-out). Tarama
 * satırlarıyla arasındaki fark, aşırı uyumun büyüklüğüdür.
 */
export interface BacktestHoldout {
  weeks: number;
  hit14?: number;
  hit14_pct?: number;
  hit14_ci?: [number, number];
  columns_total?: number;
  columns_avg?: number;
  chosen?: Array<{ threshold: string; weeks: number }>;
}

export interface BacktestResponse {
  meta: {
    weeks_available: number;
    weeks_used: number;
    weeks_dropped: Array<{ week: number; missing: number }>;
    match_count: number;
    space_limit: number;
    note: string;
  };
  strategy: { banko: number; uclu: number; explain: string };
  season: BacktestSeason;
  weeks: BacktestWeek[];
  sweep: SweepRow[];
  sweep_best: SweepRow | null;
  holdout: BacktestHoldout;
  grid: { banko: number[]; uclu: number[] };
  warning: string;
}

// ─── /api/health ──────────────────────────────────────────────────────────

/** Motorun katmanları; kaynak: backend/spor_toto/health.py KATEGORILER. */
export type HealthKategoriId =
  | "cekirdek" | "motor" | "olasilik" | "analiz" | "ucuca" | "ortam";

export interface HealthCheck {
  name: string;
  ok: boolean;
  detail: string;
  duration_ms: number;
  category: HealthKategoriId;
  category_label: string;
  /** Kontrolün NEYİ koruduğu — arayüz kriptik `name` yerine bunu gösterir. */
  aciklama: string;
  /** false ise düşmesi raporu UNHEALTHY yapmaz, yalnızca "degraded" işaretler. */
  critical: boolean;
  /** Beklenen üst süre (ms). Aşılması kontrolü DÜŞÜRMEZ. */
  butce_ms: number | null;
  /** Süre bütçesi aşıldı mı; ısınma koşusunda her zaman false. */
  yavas: boolean;
}

export interface HealthKategori {
  id: HealthKategoriId;
  label: string;
  aciklama: string;
  passed: number;
  failed: number;
  total: number;
  duration_ms: number;
  /** Kritik olmayan bir kontrol düşse bile kategori `ok` kalır. */
  ok: boolean;
}

export interface HealthEnv {
  python: string;
  platform: string;
  numpy: string | null;
  scipy: string | null;
  flask: string | null;
}

/**
 * Kısa TTL önbelleğinin durumu. Önbellekten dönen bir rapor bunu SAKLAMAZ:
 * ne zaman ölçüldüğünü gizleyen bir sağlık raporu değersizdir.
 */
export interface HealthOnbellek {
  cached: boolean;
  yas_ms: number;
  ttl_s: number;
}

/** Raporu hangi süreç üretti — çok örnekli dağıtımda "hangi örnek?" */
export interface HealthOrnek {
  pid: number;
  host: string | null;
  etiket: string | null;
  baslangic: string;
  uptime_s: number;
}

/** Çekirdek kontrollerin koştuğu kupon sınıfı. */
export interface HealthKuponSinifi {
  etiket: string;
  picks: string;
  uzay: number;
  alt_sinir: number;
}

export interface HealthSummary {
  ornek_kupon?: string;
  kupon_siniflari?: HealthKuponSinifi[];
  ornek?: HealthOrnek;
  /** Sürecin İLK raporu: süre bütçeleri uygulanmaz (ısınma). */
  isinma?: boolean;
  /** Süre bütçesini aşan kontroller — düşmediler, yavaşladılar. */
  butce_asan?: string[];
  has_scipy?: boolean;
  env?: HealthEnv;
  slowest?: { name: string; duration_ms: number } | null;
  /** `?only=` ile çalıştırıldıysa filtre metni. */
  only?: string | null;
  /** true ise rapor kontrollerin TAMAMINI kapsamıyor. */
  kismi?: boolean;
  kayitli_kontrol?: number;
  onbellek?: HealthOnbellek;
}

export interface HealthReport {
  version: string;
  timestamp: string;
  ok: boolean;
  /** Kritikler geçti ama bilgi amaçlı bir kontrol düştü. */
  degraded: boolean;
  passed: number;
  failed: number;
  total: number;
  duration_ms: number;
  categories: HealthKategori[];
  checks: HealthCheck[];
  summary: HealthSummary;
}

/** GET /api/health/history — sunucudaki son koşular. */
export interface HealthGecmisKaydi {
  timestamp: string;
  durum: "HEALTHY" | "DEGRADED" | "UNHEALTHY";
  ok: boolean;
  degraded: boolean;
  passed: number;
  total: number;
  duration_ms: number;
  dusenler: string[];
  yavaslar: string[];
  version: string;
}

export interface HealthGecmisOzet {
  kayit: number;
  durum: "HEALTHY" | "DEGRADED" | "UNHEALTHY" | null;
  /** Aynı durumda kaç koşu geçti — "ne zamandan beri" sorusunun sayısı. */
  bu_durumda_kosu: number;
  degisim_zamani: string | null;
  son_saglikli: string | null;
  sinir?: number;
  /** Durum değişiminde dışarı bildirim gidiyor mu (varsayılan kapalı). */
  alarm?: boolean;
}

export interface HealthHistoryResponse {
  version: string;
  ozet: HealthGecmisOzet;
  kayitlar: HealthGecmisKaydi[];
  ornek: HealthOrnek;
}

/** POST /api/health/kupon — KULLANICININ kendi kuponunun denetimi. */
export interface KuponDenetimKontrol {
  name: string;
  ok: boolean;
  aciklama: string;
  detail: string;
}

export interface KuponDenetimSonuc {
  ok: boolean;
  mode: ModeId;
  picks: string;
  baslik: string;
  notlar: string[];
  satir: number;
  bedel: number;
  alt_sinir: number;
  uzay: number;
  guaranteed: boolean;
  worst: number;
  acik: number;
  checks: KuponDenetimKontrol[];
  duration_ms: number;
  timestamp: string;
  version: string;
  ornek: HealthOrnek;
  /** Kayıtlı rapordan AYRI olduğunu söyleyen uyarı metni. */
  uyari: string;
}

/** /api/health/checks — çalıştırmadan alınan envanter. */
export interface HealthCheckInfo {
  name: string;
  category: HealthKategoriId;
  category_label: string;
  aciklama: string;
  critical: boolean;
  butce_ms: number | null;
}

export interface HealthChecksResponse {
  version: string;
  checks: HealthCheckInfo[];
}

/* ── Benzer maçlar (A5) ──────────────────────────────────────────────────── */

/** Bir sembolün geçmişteki karnesi. Yüzde ASLA n ve aralık olmadan gelmez. */
export interface BenzerSembol {
  adet: number;
  oran: number | null;
  ga_alt: number;
  ga_ust: number;
  /** Piyasanın aynı fiyatta dediği olasılık. */
  piyasa: number;
  fark: number | null;
  /** Piyasa güven aralığının içinde mi — asıl okunacak alan budur. */
  piyasa_ga_icinde: boolean | null;
}

export interface BenzerKarne {
  n: number;
  /** `AZ_ORNEK` (30) altındaysa yüzde okunmaz. */
  yeterli: boolean;
  semboller: Record<string, BenzerSembol>;
}

export interface BenzerDilim {
  deger: string;
  karne: BenzerKarne;
}

export interface BenzerResponse {
  oranlar: Record<string, number>;
  marj: number;
  arindirma: string;
  hedef_olasilik: Record<string, number>;
  /** Fiilen kullanılan yarıçap — genişlemiş arama kendini gizlemez. */
  tolerans: number;
  tolerans_uyarlandi: boolean;
  tolerans_genisledi: boolean;
  tolerans_tavana_dayandi: boolean;
  evren: number;
  toplam: BenzerKarne;
  dilimler: { lig: BenzerDilim[]; sezon: BenzerDilim[] };
  uyarilar: string[];
}

/* ── Tahmin (C2) ─────────────────────────────────────────────────────────── */

/** Tek maçın tahmini. `olasilik` marj arındırılmıştır ve 1'e toplanır. */
export interface TahminBlogu {
  olasilik: Record<string, number>;
  en_olasi: string | null;
  guven: number | null;
}

export interface TahminSatiri extends TahminBlogu {
  kaynak: string;
  lig: string;
  tarih: string;
  saat: string;
  ev: string;
  dep: string;
  oran_kaynak: string;
  /** Ölçülen isabetin ait olduğu lig evreninde mi. */
  olculen_lig: boolean;
  oranlar: Record<string, number>;
  /**
   * Korpusta eğitilmiş yeniden kalibrasyonun aynı maça verdiği olasılık.
   * Manşetin YERİNE geçmez, yanında durur — ölçüldü ve geçmedi.
   */
  alternatif: (TahminBlogu & { ad: string }) | null;
}

/**
 * Tahmincinin ÖLÇÜLMÜŞ isabeti. Arşivden koşulur, elle yazılmaz.
 * `olculdu=false` ise oran arşivi eksiktir ve sayı gösterilmez.
 */
/** Tek bir tahmincinin kupon setindeki ölçülmüş skoru. */
export interface TahminciSkoru {
  ad: string;
  aciklama?: string;
  n_mac: number;
  mac_basina_isabet: number;
  brier: number;
  log_kaybi: number;
  hafta_ortalamasi: number;
  en_iyi_hafta: number;
  hafta_14_arti: number;
  hafta_13_arti: number;
  /** Yalnızca alternatifte: manşete göre fark ve güven aralığı. */
  fark?: { fark: number; alt: number; ust: number; tekrar: number };
  /** Yalnızca alternatifte: aralık tamamen sıfırın altında mı. */
  gecti?: boolean;
}

export interface OlculmusIsabet {
  olculdu: boolean;
  not?: string;
  kesit?: string;
  n_hafta?: number;
  referans?: string;
  manset?: TahminciSkoru;
  alternatif?: TahminciSkoru | null;
}

export interface TahminUyarisi {
  ad: string;
  metin: string;
}

/**
 * Tahmin gövdesi. `tahminler` ile `olculmus_isabet` AYRILAMAZ — biri
 * gösteriliyorsa diğeri de gösterilir. Projenin tek kırmızı çizgisi budur.
 */
export interface TahminResponse {
  n_mac: number;
  kaynaklar: string[];
  /** Alternatif kaç maçta FARKLI sembol seçiyor. 0 = tek kolon için ikisi aynı. */
  alternatif_farkli_secim?: number;
  olculen_kaynak: boolean;
  tahminler: TahminSatiri[];
  olculmus_isabet: OlculmusIsabet;
  uyarilar: TahminUyarisi[];
  bos_sebep: string | null;
}
