import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const readiness = {
  probe: {
    cpu: { physical_cores: 6, logical_cores: 12 },
    memory: { total_bytes: 34359738368, available_bytes: 17179869184 },
    disks: [{ kind: "unknown", total_bytes: 1099511627776, available_bytes: 536870912000 }],
    gpu: { status: "detected", devices: [{ name: "RTX 5060", vendor: "NVIDIA", vram_total_bytes: 8589934592, driver_version: "610.88" }] },
  },
  readiness: {
    role: "miner",
    profile: { id: "flop-teaser-0.1", source_status: "draft", sha256: "a".repeat(64) },
    checks: [
      { code: "miner.vram_bytes", status: "fail", actual: 8589934592, threshold: 17179869184, unit: "byte", source_kind: "source_profile" },
      { code: "community.miner.vram_headroom", status: "fail", actual: 8589934592, threshold: 21474836480, unit: "byte", source_kind: "community" },
    ],
    summary: { pass: 0, warn: 0, fail: 2, unknown: 0, skipped: 0, unsupported: 0 },
  },
};

const benchmark = {
  benchmark_id: "benchmark-1",
  model: { name: '<img src=x onerror="window.__xss=1">' },
  metrics: {
    ttft: { p50: 0.053, p95: 0.054, samples: [0.052, 0.053, 0.054] },
    tokens_per_second: { p50: 44.18, p95: 45.45, samples: [42.85, 44.18, 45.45] },
    latency: { p50: 0.43, p95: 0.44, samples: [0.42, 0.43, 0.44] },
  },
  outcomes: { success: 3, timeout: 0, error: 0, cancelled: 0, partial: 0 },
};

const reportPreview = {
  export: {
    document: { privacy_level: "public", provenance: { authenticity: "unverified-local-observations" } },
    digest: { value: "b".repeat(64) },
  },
  redacted_fields: ["host identifiers", "local paths", "access tokens", "raw response content"],
};

const simulation = {
  simulated: true,
  official_protocol: false,
  disclaimer: "Educational local simulation; not an official protocol.",
  request: { session_id: "session-9", scenario: "validator-mismatch", seed: 9 },
  events: [
    { event_id: "event-1", actor: "agent", from_state: null, to_state: "created", code: "session.created" },
    { event_id: "event-2", actor: "miner", from_state: "created", to_state: "running", code: "miner.start" },
    { event_id: "event-3", actor: "validator", from_state: "validating", to_state: "challenged", code: "challenge.validator_sample_mismatch" },
    { event_id: "event-4", actor: "validator", from_state: "challenged", to_state: "rejected", code: "challenge.rejected" },
  ],
  challenge: { reason_code: "validator_sample_mismatch", validator_action: "full-rerun", full_rerun_performed: true, outcome: "rejected" },
  accounting: {
    requested_fee: { amount: 25, unit: "mock-credit" },
    charged_fee: { amount: 0, unit: "mock-credit" },
    mock_slashed: { amount: 40, unit: "mock-credit" },
  },
  final_state: "rejected",
};

async function installApi(page: Page, onBenchmark?: () => void, onSimulation?: () => void) {
  await page.route("**/api/v1/**", async (route: Route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.includes("/checks/")) return route.fulfill({ json: readiness });
    if (path.endsWith("/benchmarks")) {
      onBenchmark?.();
      return route.fulfill({ status: 201, json: benchmark });
    }
    if (path.endsWith("/reports/preview")) return route.fulfill({ json: reportPreview });
    if (path.endsWith("/simulations")) {
      onSimulation?.();
      return route.fulfill({ status: 201, json: simulation });
    }
    return route.fulfill({ status: 404, json: { code: "not_found" } });
  });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("flopbench-locale", "tr"));
});

test("S7-T03/T05 miner cards and draft profile render", async ({ page }) => {
  await installApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Genel Bakış" })).toBeVisible();
  await expect(page.getByText("RTX 5060")).toBeVisible();
  await expect(page.getByText("Ekran kartı belleği yetersiz.")).toBeVisible();
  await expect(page.getByText("Taslak", { exact: true })).toBeVisible();
});

test("S7-T04 CPU-only state is explicit", async ({ page }) => {
  await page.route("**/api/v1/checks/**", (route) => route.fulfill({
    json: {
      ...readiness,
      probe: { ...readiness.probe, gpu: { status: "no-supported-gpu", devices: [] } },
      readiness: {
        ...readiness.readiness,
        checks: [{ code: "miner.vram_bytes", status: "fail", actual: null, threshold: 17179869184, unit: "byte", source_kind: "source_profile" }],
      },
    },
  }));
  await page.goto("/");
  await expect(page.getByText("Desteklenen ekran kartı bulunamadı.")).toBeVisible();
  await expect(page.getByText("CPU only")).toBeVisible();
});

test("S7-T06/T07/T09 keyboard flow, XSS, and refresh safety", async ({ page }) => {
  let benchmarkRuns = 0;
  await installApi(page, () => { benchmarkRuns += 1; });
  await page.goto("/");
  const benchmarkNav = page.getByRole("button", { name: "Benchmark" });
  await benchmarkNav.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Henüz benchmark çalıştırılmadı.")).toBeVisible();
  expect(benchmarkRuns).toBe(0);

  await page.getByRole("button", { name: "Mock benchmark çalıştır" }).click();
  await expect(page.getByText(benchmark.model.name)).toBeVisible();
  await expect(page.locator("img")).toHaveCount(0);
  expect(await page.evaluate(() => (window as Window & { __xss?: number }).__xss)).toBeUndefined();
  expect(benchmarkRuns).toBe(1);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Genel Bakış" })).toBeVisible();
  expect(benchmarkRuns).toBe(1);
});

test("S7-T08 public preview shows fields removed from sharing", async ({ page }) => {
  await installApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Raporlar" }).click();
  await page.getByRole("button", { name: "Public raporu önizle" }).click();
  await expect(page.getByText("Cihaz ve kullanıcı adları")).toBeVisible();
  await expect(page.getByText("Yerel dosya yolları")).toBeVisible();
  await expect(page.getByText("Erişim anahtarları")).toBeVisible();
});

test("basic WCAG 2.2 AA scan has no serious or critical findings", async ({ page }) => {
  await installApi(page);
  await page.goto("/");
  await expect(page.getByText("Ekran kartı belleği yetersiz.")).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const blocking = results.violations.filter((violation) =>
    violation.impact === "critical" || violation.impact === "serious"
  );
  expect(blocking).toEqual([]);
});

test("S8-T09 dashboard has no private-key upload control", async ({ page }) => {
  await installApi(page);
  await page.goto("/");
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
  await expect(page.locator('input[name*="private" i]')).toHaveCount(0);
  await expect(page.getByLabel(/private key|özel anahtar/i)).toHaveCount(0);
});

test("S9-T08 PoUI flow stays explicit, visual, and simulated", async ({ page }) => {
  let simulationRuns = 0;
  await installApi(page, undefined, () => { simulationRuns += 1; });
  await page.goto("/");
  await page.getByRole("button", { name: "PoUI Simülasyonu" }).click();
  await expect(page.getByText(/resmî protokol veya gerçek token işlemi değildir/i)).toBeVisible();
  expect(simulationRuns).toBe(0);
  await page.getByLabel("Senaryo").selectOption("validator-mismatch");
  await page.getByRole("button", { name: "Simülasyonu çalıştır" }).click();
  await expect(page.getByRole("heading", { name: "Olay akışı" })).toBeVisible();
  await expect(page.getByText("validator_sample_mismatch", { exact: true })).toBeVisible();
  await expect(page.getByText("40 mock-credit")).toBeVisible();
  await expect(page.getByText("simulated: true", { exact: true })).toBeVisible();
  expect(simulationRuns).toBe(1);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations.filter((violation) =>
    violation.impact === "critical" || violation.impact === "serious"
  )).toEqual([]);

  await page.reload();
  expect(simulationRuns).toBe(1);
});
