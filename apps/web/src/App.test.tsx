import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

import { App } from "./App";
import type { ReadinessResponse, SimulationResponse } from "./api";

const minerReadiness: ReadinessResponse = {
  probe: {
    cpu: { physical_cores: 6, logical_cores: 12 },
    memory: { total_bytes: 32 * 1024 ** 3, available_bytes: 16 * 1024 ** 3 },
    disks: [{ kind: "unknown", total_bytes: 1024 ** 4, available_bytes: 500 * 1024 ** 3 }],
    gpu: { status: "detected", devices: [{ name: "RTX 5060", vendor: "NVIDIA", vram_total_bytes: 8 * 1024 ** 3, driver_version: "610.88" }] },
  },
  readiness: {
    role: "miner",
    profile: { id: "flop-teaser-0.1", source_status: "draft", sha256: "a".repeat(64) },
    checks: [
      { code: "miner.vram_bytes", status: "fail", actual: 8 * 1024 ** 3, threshold: 16 * 1024 ** 3, unit: "byte", source_kind: "source_profile" },
      { code: "community.miner.vram_headroom", status: "fail", actual: 8 * 1024 ** 3, threshold: 20 * 1024 ** 3, unit: "byte", source_kind: "community" },
    ],
    summary: { pass: 0, warn: 0, fail: 2, unknown: 0, skipped: 0, unsupported: 0 },
  },
};

const validatorReadiness: ReadinessResponse = {
  ...minerReadiness,
  readiness: {
    ...minerReadiness.readiness,
    role: "validator",
    checks: [
      { code: "validator.cpu_physical_cores", status: "fail", actual: 6, threshold: 8, unit: "core", source_kind: "source_profile" },
      { code: "validator.memory_bytes", status: "fail", actual: 32 * 1024 ** 3, threshold: 64 * 1024 ** 3, unit: "byte", source_kind: "source_profile" },
      { code: "validator.disk_capacity_bytes", status: "fail", actual: 1024 ** 4, threshold: 2 * 1024 ** 4, unit: "byte", source_kind: "source_profile" },
      { code: "validator.network_bits_per_second", status: "skipped", actual: null, threshold: 1e9, unit: "bit/s", source_kind: "source_profile" },
    ],
    summary: { pass: 0, warn: 0, fail: 3, unknown: 0, skipped: 1, unsupported: 0 },
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

const preview = {
  export: {
    document: { privacy_level: "public", provenance: { authenticity: "unverified-local-observations" } },
    digest: { value: "b".repeat(64) },
  },
  redacted_fields: ["host identifiers", "local paths", "access tokens", "raw response content"],
};

const simulation: SimulationResponse = {
  simulated: true,
  official_protocol: false,
  disclaimer: "Educational local simulation; not an official protocol.",
  request: { session_id: "session-9", scenario: "validator-mismatch", seed: 9 },
  events: [
    { event_id: "event-1", actor: "agent", from_state: null, to_state: "created", code: "session.created" },
    { event_id: "event-2", actor: "validator", from_state: "validating", to_state: "challenged", code: "challenge.validator_sample_mismatch" },
    { event_id: "event-3", actor: "validator", from_state: "challenged", to_state: "rejected", code: "challenge.rejected" },
  ],
  challenge: { reason_code: "validator_sample_mismatch", validator_action: "full-rerun", full_rerun_performed: true, outcome: "rejected" },
  accounting: {
    requested_fee: { amount: 25, unit: "mock-credit" },
    charged_fee: { amount: 0, unit: "mock-credit" },
    mock_slashed: { amount: 40, unit: "mock-credit" },
  },
  final_state: "rejected",
};

function installFetch(options: { readiness?: ReadinessResponse; fail?: string } = {}) {
  const mock = vi.fn((input: RequestInfo | URL) => {
    const path = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (options.fail && path.includes(options.fail)) return Promise.resolve(new Response("error", { status: 500 }));
    if (path.includes("/checks/validator")) return Promise.resolve(Response.json(validatorReadiness));
    if (path.includes("/checks/miner")) return Promise.resolve(Response.json(options.readiness ?? minerReadiness));
    if (path.endsWith("/benchmarks")) return Promise.resolve(Response.json(benchmark, { status: 201 }));
    if (path.includes("/reports/preview")) return Promise.resolve(Response.json(preview));
    if (path.endsWith("/simulations")) return Promise.resolve(Response.json(simulation, { status: 201 }));
    return Promise.resolve(new Response("missing", { status: 404 }));
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("flopbench-locale", "tr");
    document.head.innerHTML = '<meta name="flopbench-token" content="test-token">';
    delete document.documentElement.dataset.theme;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders live miner cards and a visible draft label", async () => {
    const fetchMock = installFetch();
    render(<App />);

    expect(await screen.findByText("Ekran kartı belleği yetersiz.")).toBeInTheDocument();
    expect(screen.getByText("RTX 5060")).toBeInTheDocument();
    expect(screen.getByText("Taslak")).toBeInTheDocument();
    expect(screen.getAllByText("8 GiB").length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/checks/miner");
  });

  it("shows a clear CPU-only state", async () => {
    installFetch({
      readiness: {
        ...minerReadiness,
        probe: { ...minerReadiness.probe, gpu: { status: "no-supported-gpu", devices: [] } },
        readiness: {
          ...minerReadiness.readiness,
          checks: [{ code: "miner.vram_bytes", status: "fail", actual: null, threshold: 16 * 1024 ** 3, unit: "byte", source_kind: "source_profile" }],
          summary: { pass: 0, warn: 0, fail: 1, unknown: 0, skipped: 0, unsupported: 0 },
        },
      },
    });
    render(<App />);
    expect(await screen.findByText("Desteklenen ekran kartı bulunamadı.")).toBeInTheDocument();
    expect(screen.getByText("CPU only")).toBeInTheDocument();
  });

  it("does not style unknown as failure", async () => {
    installFetch({
      readiness: {
        ...minerReadiness,
        probe: { ...minerReadiness.probe, gpu: { status: "unknown", devices: [] } },
        readiness: {
          ...minerReadiness.readiness,
          checks: [{ code: "miner.vram_bytes", status: "unknown", actual: null, threshold: 16 * 1024 ** 3, unit: "byte", source_kind: "source_profile" }],
          summary: { pass: 0, warn: 0, fail: 0, unknown: 1, skipped: 0, unsupported: 0 },
        },
      },
    });
    render(<App />);
    expect(await screen.findByText("Ekran kartı durumu belirlenemedi.")).toBeInTheDocument();
    const label = screen.getByText("Bilinmiyor", { selector: ".result-label" });
    expect(label).toHaveClass("unknown");
    expect(label).not.toHaveClass("fail");
  });

  it("renders a passing non-numeric source check", async () => {
    installFetch({
      readiness: {
        ...minerReadiness,
        readiness: {
          ...minerReadiness.readiness,
          checks: [{ code: "validator.disk_kind", status: "pass", actual: "nvme", threshold: "nvme", unit: null, source_kind: "source_profile" }],
          summary: { pass: 1, warn: 0, fail: 0, unknown: 0, skipped: 0, unsupported: 0 },
        },
      },
    });
    render(<App />);

    expect(await screen.findByText("Kaynak profil eşiği karşılanıyor.")).toBeInTheDocument();
    expect(screen.getByText("nvme")).toBeInTheDocument();
    expect(screen.getByText("Hazır")).toBeInTheDocument();
  });

  it("switches the role and the complete interface language", async () => {
    installFetch();
    render(<App />);
    await screen.findByText("Ekran kartı belleği yetersiz.");

    fireEvent.click(screen.getByRole("tab", { name: "Validator" }));
    expect(await screen.findByText("Sistem belleği yetersiz.")).toBeInTheDocument();
    expect(screen.getByText("6 çekirdek")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(screen.getByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByText("System memory is insufficient.")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
    expect(window.localStorage.getItem("flopbench-locale")).toBe("en");
  });

  it("uses the browser language on a first visit and saves dark mode", async () => {
    window.localStorage.removeItem("flopbench-locale");
    vi.spyOn(window.navigator, "language", "get").mockReturnValue("en-US");
    installFetch();
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("flopbench-theme")).toBe("dark");
  });

  it("supports keyboard navigation through the primary flow", async () => {
    installFetch();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Ekran kartı belleği yetersiz.");

    const benchmarkButton = screen.getByRole("button", { name: "Benchmark" });
    benchmarkButton.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { name: "Yerel benchmark" })).toBeInTheDocument();
    await user.tab();
    expect(document.activeElement).not.toBe(document.body);
  });

  it("renders a malicious model name as text and never as markup", async () => {
    const fetchMock = installFetch();
    const { container, unmount } = render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Benchmark" }));
    expect(screen.getByText("Henüz benchmark çalıştırılmadı.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([url]) => typeof url === "string" && url.endsWith("/benchmarks"))).toHaveLength(0);

    fireEvent.click(screen.getByRole("button", { name: "Mock benchmark çalıştır" }));
    expect(await screen.findByText(benchmark.model.name)).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getAllByText(/Çalışma/).length).toBeGreaterThan(0);

    unmount();
    render(<App />);
    await screen.findByText("Ekran kartı belleği yetersiz.");
    expect(fetchMock.mock.calls.filter(([url]) => typeof url === "string" && url.endsWith("/benchmarks"))).toHaveLength(1);
  });

  it("shows the public report redaction preview", async () => {
    installFetch();
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Raporlar" }));
    expect(screen.getByText("Henüz rapor önizlemesi oluşturulmadı.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Public raporu önizle" }));

    expect(await screen.findByText("Cihaz ve kullanıcı adları")).toBeInTheDocument();
    expect(screen.getByText("Yerel dosya yolları")).toBeInTheDocument();
    expect(screen.getByText("Erişim anahtarları")).toBeInTheDocument();
    expect(screen.getByText("b".repeat(64))).toBeInTheDocument();
  });

  it("shows concise API errors and retries", async () => {
    const fetchMock = installFetch({ fail: "/checks/miner" });
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Yerel servis kullanılamıyor.");
    fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it("keeps benchmark and report failures short", async () => {
    installFetch({ fail: "/benchmarks" });
    const { unmount } = render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Benchmark" }));
    fireEvent.click(screen.getByRole("button", { name: "Mock benchmark çalıştır" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Benchmark tamamlanamadı.");

    unmount();
    installFetch({ fail: "/reports/preview" });
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Raporlar" }));
    fireEvent.click(screen.getByRole("button", { name: "Public raporu önizle" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Rapor önizlemesi oluşturulamadı.");
  });

  it("opens and closes navigation and returns to the overview", async () => {
    installFetch();
    render(<App />);
    await screen.findByText("Ekran kartı belleği yetersiz.");

    const menu = screen.getByRole("button", { name: "Menüyü aç" });
    fireEvent.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("button", { name: "Menüyü kapat" }));
    expect(menu).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    fireEvent.click(screen.getByRole("button", { name: "TR" }));
    fireEvent.click(screen.getByRole("tab", { name: "Validator" }));
    await screen.findByText("Sistem belleği yetersiz.");
    fireEvent.click(screen.getByRole("tab", { name: "Miner" }));
    await screen.findByText("Ekran kartı belleği yetersiz.");

    fireEvent.click(screen.getByRole("button", { name: "Raporlar" }));
    fireEvent.click(screen.getByRole("button", { name: "FlopBench" }));
    expect(screen.getByRole("heading", { name: "Genel Bakış" })).toBeInTheDocument();
  });

  it("S8-T09 never exposes a private-key upload control", async () => {
    installFetch();
    const { container } = render(<App />);
    await screen.findByText("Ekran kartı belleği yetersiz.");

    expect(container.querySelector('input[type="file"]')).toBeNull();
    expect(container.querySelector('input[name*="private" i]')).toBeNull();
    expect(screen.queryByLabelText(/private key|özel anahtar/i)).not.toBeInTheDocument();
  });

  it("renders the explicitly simulated PoUI event flow", async () => {
    installFetch();
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "PoUI Simülasyonu" }));
    expect(screen.getByText(/resmî protokol veya gerçek token işlemi değildir/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Senaryo"), { target: { value: "validator-mismatch" } });
    fireEvent.click(screen.getByRole("button", { name: "Simülasyonu çalıştır" }));

    expect(await screen.findByText("validator_sample_mismatch")).toBeInTheDocument();
    expect(screen.getAllByText("rejected").length).toBeGreaterThan(0);
    expect(screen.getByText("40 mock-credit")).toBeInTheDocument();
    expect(screen.getAllByText("simulated: true").length).toBeGreaterThan(0);
  });

  it("keeps simulation failures concise", async () => {
    installFetch({ fail: "/simulations" });
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "PoUI Simülasyonu" }));
    fireEvent.click(screen.getByRole("button", { name: "Simülasyonu çalıştır" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Simülasyon tamamlanamadı.");
  });
});
