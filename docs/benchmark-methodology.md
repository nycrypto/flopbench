# Benchmark methodology

FlopBench measures end-to-end inference behavior; it does not calculate an
official FLOP score, eligibility decision, reward estimate, or proof that a
remote model performed the work.

## Reproducibility inputs

Every result records the adapter/runtime identity, model name and digest,
workload ID/version/raw-file SHA-256, prompt seed, warm-up count, measured count,
timeout, run outcomes, tool version, and UTC timestamps. The deterministic mock
adapter uses fixed synthetic measurements for cross-platform contract tests.
Ollama and OpenAI-compatible results must not be compared when model, workload,
adapter, or compatible schema identity differs.

## Metrics

- Time to first token starts before connection/request work and ends at the first
  non-empty streamed token.
- Latency covers the complete request through stream completion.
- Tokens per second uses runtime-reported counts where the adapter provides them;
  otherwise it is derived and labeled accordingly.
- Peak VRAM is an observed NVML sample and can include allocations from other
  processes.
- p50 and p95 use nearest-rank percentiles over successful measured runs only.
  Warm-ups are recorded but excluded. Timeout, partial, cancellation, and error
  runs remain visible in outcome counters and error rate.

## Operating procedure

1. Close unrelated GPU-heavy work and record driver/runtime/model digest.
2. Use the unchanged versioned workload and default warm-up/measured counts.
3. Run at least twice; investigate thermal throttling or large variance.
4. Compare only when FlopBench's compatibility gate permits it.
5. Share a public-redacted export, not the private source report.

Detailed adapter commands, timeout semantics, and SSRF controls are documented
in [`benchmarks.md`](./benchmarks.md). Report schema compatibility rules are in
[`schema-versioning.md`](./schema-versioning.md).
