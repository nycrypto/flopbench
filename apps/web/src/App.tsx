import { useEffect, useState } from "react";

import {
  loadPublicPreview,
  loadReadiness,
  runMockBenchmark,
  runSimulation,
  type BenchmarkResponse,
  type ReadinessCheck,
  type ReadinessResponse,
  type ReportPreviewResponse,
  type Role,
  type SimulationResponse,
  type SimulationScenario,
  type Status,
} from "./api";

type Theme = "light" | "dark";
type Locale = "en" | "tr";
type View = "overview" | "benchmark" | "reports" | "simulation";

const copy = {
  tr: {
    documentTitle: "FlopBench · Hazırlık durumu",
    description: "FlopBench yerel hazırlık ve benchmark dashboard'u",
    mainMenu: "Ana menü",
    dashboardSections: "Dashboard bölümleri",
    overview: "Genel Bakış",
    benchmark: "Benchmark",
    reports: "Raporlar",
    simulation: "PoUI Simülasyonu",
    localOnly: "Yalnızca yerel",
    closeMenu: "Menüyü kapat",
    openMenu: "Menüyü aç",
    localWorkspace: "Yerel çalışma alanı",
    language: "Dil seçimi",
    switchDark: "Koyu temaya geç",
    switchLight: "Açık temaya geç",
    darkTheme: "Koyu tema",
    lightTheme: "Açık tema",
    readiness: "Hazırlık durumu",
    roleSelection: "Rol seçimi",
    systemSummary: "Sistem özeti",
    detected: "Algılandı",
    required: "gerekli",
    available: "Kullanılabilir",
    profile: "Profil",
    draftSource: "Taslak kaynak",
    notEligible: "Uygun değil",
    ready: "Hazır",
    reviewRequired: "Kontrol gerekli",
    checking: "Yerel sistem kontrol ediliyor…",
    refresh: "Yenile",
    serviceUnavailable: "Yerel servis kullanılamıyor.",
    retry: "Tekrar dene",
    present: "Mevcut",
    sourceProfile: "Kaynak profili",
    draft: "Taslak",
    source: "Kaynak",
    version: "Sürüm",
    checked: "Kontrol",
    justNow: "Az önce",
    disclaimer: "Resmî uygunluk veya ödül garantisi değildir.",
    checks: "Kontroller",
    results: "sonuç",
    noGpu: "Desteklenen ekran kartı bulunamadı.",
    unsupportedGpu: "Ekran kartı sağlayıcısı desteklenmiyor.",
    unknownGpu: "Ekran kartı durumu belirlenemedi.",
    gpuMemoryLow: "Ekran kartı belleği yetersiz.",
    systemMemoryLow: "Sistem belleği yetersiz.",
    meetsProfile: "Kaynak profil eşiği karşılanıyor.",
    benchmarkTitle: "Yerel benchmark",
    benchmarkIntro: "Deterministik mock testi yalnız düğmeye bastığınızda çalışır.",
    runBenchmark: "Mock benchmark çalıştır",
    runningBenchmark: "Benchmark çalışıyor…",
    noBenchmark: "Henüz benchmark çalıştırılmadı.",
    benchmarkFailed: "Benchmark tamamlanamadı.",
    model: "Model",
    tokensPerSecond: "Token / saniye",
    latency: "Gecikme",
    ttft: "İlk token süresi",
    run: "Çalışma",
    chartLabel: "Token/s çalışma grafiği",
    reportsTitle: "Gizlilik önizlemesi",
    reportsIntro: "Public görünümde paylaşılmayacak alanları önce kontrol edin.",
    previewPublic: "Public raporu önizle",
    preparingPreview: "Önizleme hazırlanıyor…",
    noPreview: "Henüz rapor önizlemesi oluşturulmadı.",
    previewFailed: "Rapor önizlemesi oluşturulamadı.",
    privacy: "Gizlilik",
    digest: "Özet",
    authenticity: "Doğruluk",
    hiddenFields: "Paylaşılmayan alanlar",
    simulationTitle: "PoUI yaşam döngüsü",
    simulationIntro: "Agent, miner ve validator akışını tamamen yerel ve sahte değerlerle inceleyin.",
    runSimulation: "Simülasyonu çalıştır",
    runningSimulation: "Simülasyon çalışıyor…",
    noSimulation: "Henüz simülasyon çalıştırılmadı.",
    simulationFailed: "Simülasyon tamamlanamadı.",
    simulatedOnly: "Eğitim simülasyonu · resmî protokol veya gerçek token işlemi değildir.",
    scenario: "Senaryo",
    finalState: "Son durum",
    eventFlow: "Olay akışı",
    challenge: "Challenge",
    noChallenge: "Challenge oluşmadı.",
    mockAccounting: "Sahte muhasebe",
    requestedFee: "İstenen ücret",
    chargedFee: "Yazılan ücret",
    mockSlashed: "Sahte kesinti",
    redactions: {
      "host identifiers": "Cihaz ve kullanıcı adları",
      "local paths": "Yerel dosya yolları",
      "access tokens": "Erişim anahtarları",
      "raw response content": "Ham model yanıtı",
    },
  },
  en: {
    documentTitle: "FlopBench · Readiness status",
    description: "FlopBench local readiness and benchmark dashboard",
    mainMenu: "Main menu",
    dashboardSections: "Dashboard sections",
    overview: "Overview",
    benchmark: "Benchmark",
    reports: "Reports",
    simulation: "PoUI Simulation",
    localOnly: "Local only",
    closeMenu: "Close menu",
    openMenu: "Open menu",
    localWorkspace: "Local workspace",
    language: "Language selection",
    switchDark: "Switch to dark theme",
    switchLight: "Switch to light theme",
    darkTheme: "Dark theme",
    lightTheme: "Light theme",
    readiness: "Readiness status",
    roleSelection: "Role selection",
    systemSummary: "System summary",
    detected: "Detected",
    required: "required",
    available: "Available",
    profile: "Profile",
    draftSource: "Draft source",
    notEligible: "Not eligible",
    ready: "Ready",
    reviewRequired: "Review required",
    checking: "Checking the local system…",
    refresh: "Refresh",
    serviceUnavailable: "Local service is unavailable.",
    retry: "Try again",
    present: "Available",
    sourceProfile: "Source profile",
    draft: "Draft",
    source: "Source",
    version: "Version",
    checked: "Checked",
    justNow: "Just now",
    disclaimer: "Does not guarantee official eligibility or rewards.",
    checks: "Checks",
    results: "results",
    noGpu: "No supported GPU was found.",
    unsupportedGpu: "The GPU provider is unsupported.",
    unknownGpu: "The GPU status could not be determined.",
    gpuMemoryLow: "GPU memory is insufficient.",
    systemMemoryLow: "System memory is insufficient.",
    meetsProfile: "The source profile threshold is met.",
    benchmarkTitle: "Local benchmark",
    benchmarkIntro: "The deterministic mock test runs only when you press the button.",
    runBenchmark: "Run mock benchmark",
    runningBenchmark: "Benchmark is running…",
    noBenchmark: "No benchmark has been run yet.",
    benchmarkFailed: "Benchmark could not be completed.",
    model: "Model",
    tokensPerSecond: "Tokens / second",
    latency: "Latency",
    ttft: "Time to first token",
    run: "Run",
    chartLabel: "Tokens/s run chart",
    reportsTitle: "Privacy preview",
    reportsIntro: "Review fields that will not be shared in the public view.",
    previewPublic: "Preview public report",
    preparingPreview: "Preparing preview…",
    noPreview: "No report preview has been created yet.",
    previewFailed: "Report preview could not be created.",
    privacy: "Privacy",
    digest: "Digest",
    authenticity: "Authenticity",
    hiddenFields: "Fields not shared",
    simulationTitle: "PoUI lifecycle",
    simulationIntro: "Explore the agent, miner, and validator flow using entirely local mock values.",
    runSimulation: "Run simulation",
    runningSimulation: "Simulation is running…",
    noSimulation: "No simulation has been run yet.",
    simulationFailed: "Simulation could not be completed.",
    simulatedOnly: "Educational simulation · not an official protocol or real token operation.",
    scenario: "Scenario",
    finalState: "Final state",
    eventFlow: "Event flow",
    challenge: "Challenge",
    noChallenge: "No challenge was created.",
    mockAccounting: "Mock accounting",
    requestedFee: "Requested fee",
    chargedFee: "Charged fee",
    mockSlashed: "Mock slash",
    redactions: {
      "host identifiers": "Device and user names",
      "local paths": "Local file paths",
      "access tokens": "Access tokens",
      "raw response content": "Raw model response",
    },
  },
} as const;

const statusLabels: Record<Locale, Record<Status, string>> = {
  tr: { pass: "Geçti", warn: "Uyarı", fail: "Yetersiz", unknown: "Bilinmiyor", skipped: "Atlandı", unsupported: "Desteklenmiyor" },
  en: { pass: "Passed", warn: "Warning", fail: "Insufficient", unknown: "Unknown", skipped: "Skipped", unsupported: "Unsupported" },
};

const scenarioLabels: Record<Locale, Record<SimulationScenario, string>> = {
  tr: {
    success: "Başarılı akış",
    "wrong-model": "Yanlış model",
    "high-latency": "Yüksek gecikme",
    "canned-answer": "Hazır yanıt",
    timeout: "Zaman aşımı",
    "miner-cancel": "Miner iptali",
    "validator-match": "Validator eşleşmesi",
    "validator-mismatch": "Validator uyuşmazlığı",
  },
  en: {
    success: "Successful flow",
    "wrong-model": "Wrong model",
    "high-latency": "High latency",
    "canned-answer": "Canned answer",
    timeout: "Timeout",
    "miner-cancel": "Miner cancellation",
    "validator-match": "Validator match",
    "validator-mismatch": "Validator mismatch",
  },
};

const checkLabels: Record<Locale, Record<string, string>> = {
  tr: {
    "miner.vram_bytes": "Ekran kartı belleği",
    "community.miner.vram_headroom": "Topluluk payı",
    "validator.cpu_physical_cores": "İşlemci",
    "validator.memory_bytes": "Sistem belleği",
    "validator.disk_capacity_bytes": "Depolama",
    "validator.disk_kind": "Disk türü",
    "validator.network_bits_per_second": "Ağ testi",
  },
  en: {
    "miner.vram_bytes": "GPU memory",
    "community.miner.vram_headroom": "Community headroom",
    "validator.cpu_physical_cores": "Processor",
    "validator.memory_bytes": "System memory",
    "validator.disk_capacity_bytes": "Storage",
    "validator.disk_kind": "Disk type",
    "validator.network_bits_per_second": "Network test",
  },
};

function initialTheme(): Theme {
  return window.localStorage.getItem("flopbench-theme") === "dark" ? "dark" : "light";
}

function initialLocale(): Locale {
  const saved = window.localStorage.getItem("flopbench-locale");
  if (saved === "tr" || saved === "en") return saved;
  return window.navigator.language.toLowerCase().startsWith("tr") ? "tr" : "en";
}

function formatNumber(value: number, locale: Locale, digits = 1): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value);
}

function formatBytes(value: number, locale: Locale): string {
  return `${formatNumber(value / 1024 ** 3, locale)} GiB`;
}

function formatCheckValue(check: ReadinessCheck, locale: Locale): string {
  if (check.actual === null) return "—";
  if (check.unit === "byte" && typeof check.actual === "number") return formatBytes(check.actual, locale);
  if (check.unit === "core") return `${check.actual} ${locale === "tr" ? "çekirdek" : "cores"}`;
  if (check.unit === "bit/s" && typeof check.actual === "number") return `${formatNumber(check.actual / 1e9, locale)} Gbit/s`;
  return String(check.actual);
}

function overallStatus(data: ReadinessResponse): Status {
  const sourceStatuses = data.readiness.checks
    .filter((check) => check.source_kind === "source_profile")
    .map((check) => check.status);
  for (const status of ["fail", "unsupported", "unknown", "warn", "skipped"] as const) {
    if (sourceStatuses.includes(status)) return status;
  }
  return "pass";
}

function StatusMark({ tone }: { tone: Status }) {
  const mark = tone === "pass" ? "✓" : tone === "fail" ? "×" : tone === "warn" ? "!" : "?";
  return <span className={`status-mark ${tone}`} aria-hidden="true">{mark}</span>;
}

function Overview({ locale, role }: { locale: Locale; role: Role }) {
  const text = copy[locale];
  const [refreshKey, setRefreshKey] = useState(0);
  const [data, setData] = useState<ReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let current = true;
    loadReadiness(role)
      .then((response) => {
        if (current) setData(response);
      })
      .catch(() => {
        if (current) setFailed(true);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [role, refreshKey]);

  const refresh = () => {
    setLoading(true);
    setFailed(false);
    setRefreshKey((key) => key + 1);
  };

  if (loading && data === null) return <section className="panel state-panel" aria-live="polite">{text.checking}</section>;
  if (failed || data === null) {
    return (
      <section className="panel state-panel error-state" role="alert">
        <strong>{text.serviceUnavailable}</strong>
        <button type="button" className="primary-button" onClick={refresh}>{text.retry}</button>
      </section>
    );
  }

  const status = overallStatus(data);
  const gpu = data.probe.gpu.devices[0];
  const sourceCheck = data.readiness.checks.find((check) => check.source_kind === "source_profile");
  const current = sourceCheck?.actual;
  const threshold = sourceCheck?.threshold;
  const numericCurrent = typeof current === "number" ? current : 0;
  const numericThreshold = typeof threshold === "number" ? threshold : 0;
  const meterWidth = `${numericThreshold > 0 ? Math.min(100, (numericCurrent / numericThreshold) * 100) : 0}%`;
  const resultTitle = data.probe.gpu.status === "no-supported-gpu"
    ? text.noGpu
    : data.probe.gpu.status === "unsupported"
      ? text.unsupportedGpu
      : data.probe.gpu.status === "unknown"
        ? text.unknownGpu
        : status === "pass"
          ? text.meetsProfile
          : role === "miner"
            ? text.gpuMemoryLow
            : text.systemMemoryLow;
  const gpuName = gpu?.name ?? (data.probe.gpu.status === "unsupported" ? statusLabels[locale].unsupported : "CPU only");
  const gpuMemory = gpu?.vram_total_bytes ? formatBytes(gpu.vram_total_bytes, locale) : "—";
  const resultValue = sourceCheck ? formatCheckValue(sourceCheck, locale) : "—";
  const requiredValue = typeof threshold === "number" && sourceCheck?.unit === "byte"
    ? formatBytes(threshold, locale)
    : String(threshold ?? "—");

  return (
    <>
      <section className="summary-grid" aria-label={text.systemSummary}>
        <article><span>GPU</span><strong>{gpuName}</strong><small>{gpu ? text.detected : statusLabels[locale][status]}</small></article>
        <article className={status === "fail" ? "attention" : ""}><span>VRAM</span><strong>{gpuMemory}</strong><small>{role === "miner" ? `${requiredValue} ${text.required}` : text.available}</small></article>
        <article><span>RAM</span><strong>{formatBytes(data.probe.memory.total_bytes, locale)}</strong><small>{text.available}</small></article>
        <article><span>{text.profile}</span><strong>0.1</strong><small>{text.draftSource}</small></article>
      </section>

      <div className="main-grid">
        <section className="panel readiness-panel" aria-labelledby="readiness-title">
          <div className="panel-heading">
            <div><p>{role === "miner" ? "Miner" : "Validator"}</p><h2 id="readiness-title">{status === "pass" ? text.ready : text.notEligible}</h2></div>
            <div className="heading-actions"><span className={`result-label ${status}`}>{statusLabels[locale][status]}</span><button type="button" className="text-button" onClick={refresh}>{text.refresh}</button></div>
          </div>
          <div className={`result-message ${status}`}>
            <StatusMark tone={status} />
            <div><strong>{resultTitle}</strong><span>{resultValue} · {requiredValue} {text.required}</span></div>
          </div>
          {typeof current === "number" && typeof threshold === "number" && (
            <div className="meter" aria-label={`${resultValue}, ${requiredValue} ${text.required}`}>
              <div><span>{text.present}</span><strong>{resultValue} / {requiredValue}</strong></div>
              <div className={`meter-track ${status}`} aria-hidden="true"><span style={{ width: meterWidth }} /></div>
            </div>
          )}
        </section>

        <aside className="panel profile-panel" aria-labelledby="profile-title">
          <div className="panel-heading"><h2 id="profile-title">{text.sourceProfile}</h2><span className="draft-label">{text.draft}</span></div>
          <dl>
            <div><dt>{text.source}</dt><dd>FLOP teaser</dd></div>
            <div><dt>{text.version}</dt><dd>0.1</dd></div>
            <div><dt>{text.checked}</dt><dd>{text.justNow}</dd></div>
          </dl>
          <p>{text.disclaimer}</p>
        </aside>
      </div>

      <section className="panel checks-panel" aria-labelledby="checks-title">
        <div className="panel-heading"><h2 id="checks-title">{text.checks}</h2><span>{data.readiness.checks.length} {text.results}</span></div>
        <div className="check-list">
          {data.readiness.checks.map((check) => (
            <div className="check-row" key={check.code}>
              <StatusMark tone={check.status} />
              <span className="check-name">{checkLabels[locale][check.code] ?? check.code}</span>
              <strong>{formatCheckValue(check, locale)}</strong>
              <span className={`check-status ${check.status}`}>{statusLabels[locale][check.status]}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function BenchmarkView({ locale }: { locale: Locale }) {
  const text = copy[locale];
  const [report, setReport] = useState<BenchmarkResponse | null>(null);
  const [state, setState] = useState<"idle" | "running" | "failed">("idle");

  const run = () => {
    setState("running");
    runMockBenchmark()
      .then((result) => {
        setReport(result);
        setState("idle");
      })
      .catch(() => setState("failed"));
  };
  const samples = report?.metrics.tokens_per_second.samples ?? [];
  const maxSample = Math.max(...samples, 1);

  return (
    <section className="workspace-view" aria-labelledby="benchmark-title">
      <div className="workspace-heading">
        <div><p className="eyebrow">{text.benchmark}</p><h1 id="benchmark-title">{text.benchmarkTitle}</h1><p>{text.benchmarkIntro}</p></div>
        <button type="button" className="primary-button" disabled={state === "running"} onClick={run}>{state === "running" ? text.runningBenchmark : text.runBenchmark}</button>
      </div>
      {state === "failed" && <div className="panel state-panel error-state" role="alert">{text.benchmarkFailed}</div>}
      {report === null && state !== "failed" && <div className="panel state-panel">{state === "running" ? text.runningBenchmark : text.noBenchmark}</div>}
      {report && (
        <>
          <section className="summary-grid benchmark-summary" aria-label={text.benchmarkTitle}>
            <article><span>{text.model}</span><strong>{report.model.name}</strong><small>Mock</small></article>
            <article><span>P50 {text.tokensPerSecond}</span><strong>{formatNumber(report.metrics.tokens_per_second.p50 ?? 0, locale, 2)}</strong><small>token/s</small></article>
            <article><span>P95 {text.latency}</span><strong>{formatNumber(report.metrics.latency.p95 ?? 0, locale, 3)} s</strong><small>nearest-rank</small></article>
            <article><span>P50 {text.ttft}</span><strong>{formatNumber(report.metrics.ttft.p50 ?? 0, locale, 3)} s</strong><small>{report.outcomes.success} {text.results}</small></article>
          </section>
          <section className="panel chart-panel" aria-labelledby="chart-title">
            <div className="panel-heading"><h2 id="chart-title">{text.tokensPerSecond}</h2><span>{samples.length} {text.results}</span></div>
            <ol className="bar-chart" aria-label={text.chartLabel}>
              {samples.map((sample, index) => (
                <li key={`${index}-${sample}`}>
                  <span>{text.run} {index + 1}</span>
                  <span className="bar-track" aria-hidden="true"><span style={{ width: `${(sample / maxSample) * 100}%` }} /></span>
                  <strong>{formatNumber(sample, locale, 2)}</strong>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </section>
  );
}

function ReportsView({ locale }: { locale: Locale }) {
  const text = copy[locale];
  const [preview, setPreview] = useState<ReportPreviewResponse | null>(null);
  const [state, setState] = useState<"idle" | "running" | "failed">("idle");

  const prepare = () => {
    setState("running");
    loadPublicPreview()
      .then((result) => {
        setPreview(result);
        setState("idle");
      })
      .catch(() => setState("failed"));
  };

  return (
    <section className="workspace-view" aria-labelledby="reports-title">
      <div className="workspace-heading">
        <div><p className="eyebrow">{text.reports}</p><h1 id="reports-title">{text.reportsTitle}</h1><p>{text.reportsIntro}</p></div>
        <button type="button" className="primary-button" disabled={state === "running"} onClick={prepare}>{state === "running" ? text.preparingPreview : text.previewPublic}</button>
      </div>
      {state === "failed" && <div className="panel state-panel error-state" role="alert">{text.previewFailed}</div>}
      {preview === null && state !== "failed" && <div className="panel state-panel">{state === "running" ? text.preparingPreview : text.noPreview}</div>}
      {preview && (
        <div className="report-grid">
          <section className="panel report-summary" aria-label={text.reportsTitle}>
            <dl>
              <div><dt>{text.privacy}</dt><dd><span className="draft-label">Public</span></dd></div>
              <div><dt>{text.authenticity}</dt><dd>{preview.export.document.provenance.authenticity}</dd></div>
              <div className="digest-row"><dt>{text.digest}</dt><dd>{preview.export.digest.value}</dd></div>
            </dl>
          </section>
          <section className="panel redaction-panel" aria-labelledby="redactions-title">
            <div className="panel-heading"><h2 id="redactions-title">{text.hiddenFields}</h2><span>{preview.redacted_fields.length}</span></div>
            <ul>{preview.redacted_fields.map((field) => <li key={field}><StatusMark tone="pass" />{text.redactions[field as keyof typeof text.redactions] ?? field}</li>)}</ul>
          </section>
        </div>
      )}
    </section>
  );
}

function SimulationView({ locale }: { locale: Locale }) {
  const text = copy[locale];
  const [scenario, setScenario] = useState<SimulationScenario>("success");
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [state, setState] = useState<"idle" | "running" | "failed">("idle");

  const run = () => {
    setState("running");
    runSimulation(scenario)
      .then((response) => {
        setResult(response);
        setState("idle");
      })
      .catch(() => setState("failed"));
  };

  return (
    <section className="workspace-view" aria-labelledby="simulation-title">
      <div className="workspace-heading simulation-heading">
        <div><p className="eyebrow">{text.simulation}</p><h1 id="simulation-title">{text.simulationTitle}</h1><p>{text.simulationIntro}</p></div>
        <div className="simulation-controls">
          <label>{text.scenario}
            <select value={scenario} onChange={(event) => setScenario(event.target.value as SimulationScenario)}>
              {(Object.keys(scenarioLabels[locale]) as SimulationScenario[]).map((value) => (
                <option key={value} value={value}>{scenarioLabels[locale][value]}</option>
              ))}
            </select>
          </label>
          <button type="button" className="primary-button" disabled={state === "running"} onClick={run}>{state === "running" ? text.runningSimulation : text.runSimulation}</button>
        </div>
      </div>
      <div className="simulation-notice" role="note">{text.simulatedOnly}</div>
      {state === "failed" && <div className="panel state-panel error-state" role="alert">{text.simulationFailed}</div>}
      {result === null && state !== "failed" && <div className="panel state-panel">{state === "running" ? text.runningSimulation : text.noSimulation}</div>}
      {result && (
        <>
          <section className="summary-grid simulation-summary" aria-label={text.simulationTitle}>
            <article><span>{text.scenario}</span><strong>{scenarioLabels[locale][result.request.scenario]}</strong><small>seed {result.request.seed}</small></article>
            <article><span>{text.finalState}</span><strong>{result.final_state}</strong><small>simulated: true</small></article>
            <article><span>{text.challenge}</span><strong>{result.challenge?.outcome ?? "—"}</strong><small>{result.challenge?.validator_action ?? text.noChallenge}</small></article>
            <article><span>{text.mockAccounting}</span><strong>{result.accounting.charged_fee.amount}</strong><small>mock-credit</small></article>
          </section>
          <div className="simulation-grid">
            <section className="panel timeline-panel" aria-labelledby="event-flow-title">
              <div className="panel-heading"><h2 id="event-flow-title">{text.eventFlow}</h2><span>{result.events.length}</span></div>
              <ol className="event-timeline">
                {result.events.map((event) => (
                  <li key={event.event_id}>
                    <span className="event-dot" aria-hidden="true" />
                    <div><strong>{event.to_state}</strong><small>{event.actor} · {event.code}</small></div>
                  </li>
                ))}
              </ol>
            </section>
            <aside className="panel accounting-panel" aria-labelledby="accounting-title">
              <div className="panel-heading"><h2 id="accounting-title">{text.mockAccounting}</h2><span>simulated</span></div>
              <dl>
                <div><dt>{text.requestedFee}</dt><dd>{result.accounting.requested_fee.amount} mock-credit</dd></div>
                <div><dt>{text.chargedFee}</dt><dd>{result.accounting.charged_fee.amount} mock-credit</dd></div>
                <div><dt>{text.mockSlashed}</dt><dd>{result.accounting.mock_slashed.amount} mock-credit</dd></div>
              </dl>
              <p>{result.challenge ? result.challenge.reason_code : text.noChallenge}</p>
            </aside>
          </div>
        </>
      )}
    </section>
  );
}

export function App() {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [role, setRole] = useState<Role>("miner");
  const [view, setView] = useState<View>("overview");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("flopbench-theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.title = copy[locale].documentTitle;
    document.querySelector('meta[name="description"]')?.setAttribute("content", copy[locale].description);
    window.localStorage.setItem("flopbench-locale", locale);
  }, [locale]);

  const text = copy[locale];
  const nextTheme = theme === "light" ? "dark" : "light";
  const selectView = (selected: View) => {
    setView(selected);
    setMenuOpen(false);
  };

  return (
    <div className={`dashboard-shell${menuOpen ? " menu-open" : ""}`}>
      <aside className="sidebar" id="app-sidebar" aria-label={text.mainMenu}>
        <button className="brand" type="button" onClick={() => selectView("overview")}>
          <span className="brand-mark" aria-hidden="true">F</span><span>FlopBench</span>
        </button>
        <nav className="sidebar-nav" aria-label={text.dashboardSections}>
          {(["overview", "benchmark", "reports", "simulation"] as const).map((item, index) => (
            <button className={`nav-item${view === item ? " active" : ""}`} type="button" aria-current={view === item ? "page" : undefined} onClick={() => selectView(item)} key={item}>
              <span aria-hidden="true">0{index + 1}</span>{text[item]}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer"><span className="local-dot" aria-hidden="true" /><div><strong>{text.localOnly}</strong><span>127.0.0.1</span></div></div>
      </aside>

      <button className="menu-backdrop" type="button" aria-label={text.closeMenu} onClick={() => setMenuOpen(false)} />
      <div className="dashboard-content">
        <header className="topbar">
          <button className="menu-button" type="button" aria-label={text.openMenu} aria-controls="app-sidebar" aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}><span aria-hidden="true">☰</span></button>
          <span className="topbar-title">{text.localWorkspace}</span>
          <div className="topbar-actions">
            <div className="language-switch" role="group" aria-label={text.language}>
              <button type="button" aria-pressed={locale === "tr"} onClick={() => setLocale("tr")}>TR</button>
              <button type="button" aria-pressed={locale === "en"} onClick={() => setLocale("en")}>EN</button>
            </div>
            <button className="theme-button" type="button" aria-label={nextTheme === "dark" ? text.switchDark : text.switchLight} onClick={() => setTheme(nextTheme)}>{nextTheme === "dark" ? text.darkTheme : text.lightTheme}</button>
          </div>
        </header>

        <main id="overview">
          {view === "overview" && (
            <>
              <div className="page-heading">
                <div><p className="eyebrow">{text.readiness}</p><h1>{text.overview}</h1></div>
                <div className="role-tabs" role="tablist" aria-label={text.roleSelection}>
                  <button type="button" role="tab" aria-selected={role === "miner"} onClick={() => setRole("miner")}>Miner</button>
                  <button type="button" role="tab" aria-selected={role === "validator"} onClick={() => setRole("validator")}>Validator</button>
                </div>
              </div>
              <Overview key={role} locale={locale} role={role} />
            </>
          )}
          {view === "benchmark" && <BenchmarkView locale={locale} />}
          {view === "reports" && <ReportsView locale={locale} />}
          {view === "simulation" && <SimulationView locale={locale} />}
        </main>
      </div>
    </div>
  );
}
