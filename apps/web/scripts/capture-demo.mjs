import { chromium } from "@playwright/test";
import { mkdir, rename, rm } from "node:fs/promises";
import { resolve } from "node:path";

const destination = resolve("../../docs/assets/flopbench-dashboard-demo.webm");
const videoDirectory = resolve("../../docs/assets/.capture");

const readiness = {
  probe: {
    cpu: { physical_cores: 6, logical_cores: 12 },
    memory: { total_bytes: 34359738368, available_bytes: 17179869184 },
    disks: [{ kind: "unknown", total_bytes: 1099511627776, available_bytes: 536870912000 }],
    gpu: {
      status: "detected",
      devices: [{
        name: "RTX 5060 (fixture)", vendor: "NVIDIA", vram_total_bytes: 8589934592,
        driver_version: "fixture",
      }],
    },
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
  benchmark_id: "fixture-benchmark",
  model: { name: "flopbench-demo-model" },
  metrics: {
    ttft: { p50: 0.053, p95: 0.054, samples: [0.052, 0.053, 0.054] },
    tokens_per_second: { p50: 44.18, p95: 45.45, samples: [42.85, 44.18, 45.45] },
    latency: { p50: 0.43, p95: 0.44, samples: [0.42, 0.43, 0.44] },
  },
  outcomes: { success: 3, timeout: 0, error: 0, cancelled: 0, partial: 0 },
};

const preview = {
  export: {
    document: {
      privacy_level: "public",
      provenance: { authenticity: "unverified-local-observations" },
    },
    digest: { value: "b".repeat(64) },
  },
  redacted_fields: ["host identifiers", "local paths", "access tokens", "raw response content"],
};

const simulation = {
  simulated: true,
  official_protocol: false,
  request: { session_id: "fixture-session", scenario: "validator-mismatch", seed: 9 },
  events: [
    { event_id: "event-1", actor: "agent", from_state: null, to_state: "created", code: "session.created" },
    { event_id: "event-2", actor: "miner", from_state: "created", to_state: "running", code: "miner.start" },
    { event_id: "event-3", actor: "validator", from_state: "validating", to_state: "challenged", code: "challenge.validator_sample_mismatch" },
    { event_id: "event-4", actor: "validator", from_state: "challenged", to_state: "rejected", code: "challenge.rejected" },
  ],
  challenge: {
    reason_code: "validator_sample_mismatch", validator_action: "full-rerun",
    full_rerun_performed: true, outcome: "rejected",
  },
  accounting: {
    requested_fee: { amount: 25, unit: "mock-credit" },
    charged_fee: { amount: 0, unit: "mock-credit" },
    mock_slashed: { amount: 40, unit: "mock-credit" },
  },
  final_state: "rejected",
};

await mkdir(videoDirectory, { recursive: true });
await rm(destination, { force: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: videoDirectory, size: { width: 1280, height: 720 } },
});
const page = await context.newPage();
await page.addInitScript(() => localStorage.setItem("flopbench-locale", "en"));
await page.route("**/api/v1/**", async (route) => {
  const path = new URL(route.request().url()).pathname;
  if (path.includes("/checks/")) return route.fulfill({ json: readiness });
  if (path.endsWith("/benchmarks")) return route.fulfill({ status: 201, json: benchmark });
  if (path.endsWith("/reports/preview")) return route.fulfill({ json: preview });
  if (path.endsWith("/simulations")) return route.fulfill({ status: 201, json: simulation });
  return route.fulfill({ status: 404, json: { code: "not_found" } });
});

await page.goto("http://127.0.0.1:4173");
await page.getByRole("heading", { name: "Overview" }).waitFor();
await page.waitForTimeout(1200);
await page.getByRole("button", { name: "Benchmark" }).click();
await page.getByRole("button", { name: "Run mock benchmark" }).click();
await page.getByText("flopbench-demo-model").waitFor();
await page.waitForTimeout(1200);
await page.getByRole("button", { name: "Reports" }).click();
await page.getByRole("button", { name: "Preview public report" }).click();
await page.getByText("Device and user names").waitFor();
await page.waitForTimeout(1200);
await page.getByRole("button", { name: "PoUI Simulation" }).click();
await page.getByLabel("Scenario").selectOption("validator-mismatch");
await page.getByRole("button", { name: "Run simulation" }).click();
await page.getByRole("heading", { name: "Event flow" }).waitFor();
await page.waitForTimeout(1600);

const video = page.video();
await context.close();
if (video === null) throw new Error("Playwright did not create a demo video");
await rename(await video.path(), destination);
await browser.close();
await rm(videoDirectory, { recursive: true, force: true });
process.stdout.write(`Captured fixture-only dashboard demo at ${destination}\n`);
