# Stage 5 acceptance record

- Date: 2026-09-07
- Platform: Windows, NVIDIA GeForce RTX 5060, 8,151 MiB VRAM, driver 610.88
- Runtime: Ollama 0.33.3, loopback only
- Ollama archive SHA-256: `52cb36a62e7e501f61514f60212dec7117b6c098811357585e02fffe32d2fcd7`
- Model: `llama3.2:3b`
- Model digest: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`
- Workload digest: `fa2c9a30f13784605c2ee74518f8fde0c9cb974dd4e4db7cf26d67a0575e22cb`

## Real run

- Warmups: 1; measured runs: 3
- Outcomes: 3 success, 0 timeout, 0 error, 0 cancelled, 0 partial
- Measured token counts: 64, 36, 64
- Tokens/s nearest-rank p50: 145.7895; p95: 152.8088
- Latency nearest-rank p50: 0.4200 s; p95: 0.4394 s
- FlopBench NVML peak: 3,952,222,208 bytes
- Independent `nvidia-smi` peak: 3,684,696,064 bytes over 14 samples
- Peak difference: 267,526,144 bytes (the 20 ms NVML sampler captured a
  shorter transient than the lower-frequency command-line sampler)

For a same-stream raw comparison, Ollama's final NDJSON object reported
`eval_count=64` and `eval_duration=463058000 ns`. The adapter produced exactly
64 generated tokens and 138.2116279170212 token/s from those fields. Both
comparisons were exact. The bounded raw stream was 7,229 bytes.

The downloaded runtime, model blobs, logs, and temporary wheel installation
remain Git-ignored. The test-started loopback runtime was stopped after the
acceptance run.

## Automated gate

- Ruff: passed
- mypy strict: passed
- Unit: 102 passed; total line/branch coverage 87.13%
- Contract: 59 passed
- Security: 8 passed; required redaction branch gate 100%
- Web: ESLint and TypeScript passed; 2 Vitest tests passed; Vite build passed
- Python: wheel and sdist built; dependency check passed

The public v1 benchmark schema remains immutable. Stage 5 emits the additive
`flopbench-benchmark-report-v2` contract.
