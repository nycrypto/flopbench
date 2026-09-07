# Inference benchmarks

Stage 5 provides a provider-independent benchmark engine. It is a local
measurement tool, not a FLOP eligibility score, reward estimate, or official
network benchmark.

## Adapters

- `mock` is deterministic, opens no sockets, and is the CI reference adapter.
- `ollama` uses the native streaming `/api/generate` API and obtains the exact
  model SHA-256 digest from `/api/tags`.
- `openai-compatible` uses streaming `/chat/completions`. Because compatible
  servers do not expose a portable content identity, `--model-digest` is
  mandatory. An optional API key is read from an environment variable and is
  never written to the report.

Loopback endpoints are accepted by default. An external endpoint requires both
an exact `--allow-host` entry and `--approve-external`. Credentials, query
strings, fragments, traversal paths, redirects, oversized responses, and
unapproved external hosts are rejected.

## Workload and run accounting

The packaged `smoke-v1.json` workload is strict UTF-8/LF JSON. The report records the SHA-256
digest of its exact bytes, version, fixed seed, warmup count, and measured count.
Warmups remain visible in `runs` but are excluded from summary metrics.

Every measured request is classified as `success`, `timeout`, `error`,
`cancelled`, or `partial`. Error rate is the number of all non-success outcomes
divided by the configured measured-run count. Failed requests are never silently
removed. Partial streams preserve safe numeric observations and a digest of the
bounded raw runtime response.

## Metrics

- TTFT: wall-clock seconds from request start to first non-empty streamed token.
- Latency: wall-clock seconds from request start to completed stream.
- Tokens/s: Ollama's `eval_count / eval_duration`; OpenAI-compatible completion
  tokens divided by wall-clock generation time after the first token.
- Peak VRAM: bytes of total used memory sampled through NVML for the selected GPU
  during each request. It may be empty where NVML is unavailable.
- p50/p95: nearest-rank percentiles over successful measured requests only.

FlopBench does not calculate a FLOP estimate in Stage 5. If a later release adds
one, the contract requires it to be labeled `estimated`, never `measured`.

## Examples

```powershell
flopbench benchmark run --adapter mock --model fixture-model

flopbench benchmark run `
  --adapter ollama `
  --model llama3.2:3b `
  --endpoint http://127.0.0.1:11434

flopbench benchmark run `
  --adapter openai-compatible `
  --model local-model `
  --model-digest <64-lowercase-hex-characters> `
  --endpoint http://127.0.0.1:8000/v1
```

The command writes the strict `flopbench-benchmark-report-v2` JSON document to
stdout. Target disclosure is written to stderr so redirected report JSON stays
valid.
