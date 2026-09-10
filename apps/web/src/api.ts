export type Status = "pass" | "warn" | "fail" | "unknown" | "skipped" | "unsupported";
export type Role = "miner" | "validator";

export type GpuDevice = {
  name: string;
  vendor: string;
  vram_total_bytes: number | null;
  driver_version: string | null;
};

export type ReadinessCheck = {
  code: string;
  status: Status;
  actual: number | string | boolean | null;
  threshold: number | string | boolean | null;
  unit: string | null;
  source_kind: "source_profile" | "community";
};

export type ReadinessResponse = {
  probe: {
    cpu: { physical_cores: number | null; logical_cores: number };
    memory: { total_bytes: number; available_bytes: number };
    disks: Array<{ kind: string; total_bytes: number; available_bytes: number }>;
    gpu: { status: string; devices: GpuDevice[] };
  };
  readiness: {
    role: Role;
    profile: { id: string; source_status: string; sha256: string };
    checks: ReadinessCheck[];
    summary: Record<Status, number>;
  };
};

export type BenchmarkResponse = {
  benchmark_id: string;
  model: { name: string };
  metrics: {
    ttft: { p50: number | null; p95: number | null; samples: number[] };
    tokens_per_second: { p50: number | null; p95: number | null; samples: number[] };
    latency: { p50: number | null; p95: number | null; samples: number[] };
  };
  outcomes: { success: number; timeout: number; error: number; cancelled: number; partial: number };
};

export type ReportPreviewResponse = {
  export: {
    document: { privacy_level: string; provenance: { authenticity: string } };
    digest: { value: string };
  };
  redacted_fields: string[];
};

function startupToken(): string {
  return document.querySelector<HTMLMetaElement>('meta[name="flopbench-token"]')?.content ?? "";
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-FlopBench-Token": startupToken(),
      ...init.headers,
    },
  });
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json() as Promise<T>;
}

export function loadReadiness(role: Role, fixture: string = "live"): Promise<ReadinessResponse> {
  return apiRequest(`/api/v1/checks/${role}`, {
    method: "POST",
    body: JSON.stringify({ fixture }),
  });
}

export function runMockBenchmark(): Promise<BenchmarkResponse> {
  return apiRequest("/api/v1/benchmarks", {
    method: "POST",
    body: JSON.stringify({ adapter: "mock", model_name: "fixture-model" }),
  });
}

export function loadPublicPreview(): Promise<ReportPreviewResponse> {
  return apiRequest("/api/v1/reports/preview", {
    method: "POST",
    body: JSON.stringify({ privacy: "public" }),
  });
}
