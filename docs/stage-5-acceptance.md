# Stage 5 acceptance record

- Date: 2026-09-07
- Platform: Windows, NVIDIA GeForce RTX 5060, 8,151 MiB VRAM, driver 610.88
- Runtime: Ollama 0.33.3, loopback only, cloud disabled
- Ollama archive SHA-256: `52cb36a62e7e501f61514f60212dec7117b6c098811357585e02fffe32d2fcd7`
- Model: `llama3.2:3b`
- Model digest: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`
- Workload digest: `fa2c9a30f13784605c2ee74518f8fde0c9cb974dd4e4db7cf26d67a0575e22cb`

## Correction of the earlier candidate record

The initial Stage 5 candidate's green tests did not detect that TTFT and latency
started after response headers. Its latency values are superseded, not valid
acceptance evidence. The initial claim attributing a roughly 256 MiB VRAM gap
to sampling frequency was not supported. Direct calibration found NVML v1 used
memory includes the 268,435,456 reserved bytes; v2 exposes them separately.
An orphaned GPU runner from the initial acceptance session was also found and
stopped before the final hardware rerun. Its unrelated allocations inflated
earlier total-device VRAM observations.

Corrections add delayed-header, silent-stream, trickle-stream, active-cancellation,
real stuck-DNS subprocess cleanup, URL ambiguity and response-limit regressions.
Interrupted runs retain existing observations and completed runs. Missing usage
is null; a missing SSE terminator cannot count as success. Mock observations are
explicitly simulated, and cross-adapter throughput confidence/methods are distinct.
CI now actually invokes the security session on both platforms.

## Final real run

- Warmups: 1; measured runs: 3
- Outcomes: 3 success, 0 timeout, 0 error, 0 cancelled, 0 partial
- Measured token counts: 64, 36, 64
- TTFT nearest-rank p50: 0.0438833 s; p95: 0.0444377 s
- Latency nearest-rank p50: 0.5461419 s; p95: 0.5580281 s
- Tokens/s nearest-rank p50: 125.1175; p95: 126.6767
- NVML peak over all four runs: 3,991,035,904 bytes
- Independent `nvidia-smi` used + reserved peak: 3,991,928,832 bytes, 68 samples
- Difference: 892,928 bytes (<1 MiB); samplers are not exactly synchronized and
  `nvidia-smi` emits rounded MiB, so byte equality is not expected.
- Same-time calibration: NVML v1 used 3,991,035,904; v2 used 3,722,600,448;
  v2 reserved 268,435,456 bytes. Their sum agrees exactly.

All four bounded NDJSON streams were retained locally and independently parsed;
their final `eval_count` and `eval_count * 1e9 / eval_duration` match the adapter
exactly. The two length-capped measured outputs were additionally retokenized
through the loaded llama-server's separate `/tokenize` endpoint with
`add_special=false`, `parse_special=false`: both gave 64 token IDs, matching
64 reported tokens. This is independent of FlopBench's parsing and Ollama's
usage fields, but uses the same model tokenizer, not a second tokenizer engine.
EOS-ended runs have one more reported generation token than visible text chunks;
chunk count is not used as a general tokenizer substitute.

Local evidence under Git-ignored `.acceptance/stage5-recheck/`:

- `report.json` SHA-256: `23d0ec1fa1c92a5be63d10ef994f33326dd2bf40b77fe458f0ca34b6896de294`
- `nvidia-smi.csv` SHA-256: `ba07092698d8d5ef444c72e55f2b8da07646cc253d02534bda994676e599df9e`
- `run-1.ndjson` through `run-4.ndjson`, and `summary.json`

Only the versioned synthetic workload was sent to the local runtime. Runtime,
model blobs and raw outputs remain Git-ignored. Acceptance-owned server/runner
processes were stopped; no test listening ports remain. No user inference server
was terminated and no downloaded model files were deleted.

## Automated gate

Commands:

```powershell
.\.venv\Scripts\python.exe -m nox -s lint typecheck unit contract security build
pnpm --filter "@flopbench/web" lint
pnpm --filter "@flopbench/web" typecheck
pnpm --filter "@flopbench/web" test -- --run
pnpm --filter "@flopbench/web" build
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

- Ruff and strict mypy: passed
- Unit: 162 passed; combined line/branch coverage 88.71%
- Contract: 59 passed (including immutable v1 schema byte checks)
- Security session: 63 passed; 100% line/branch coverage across probe privacy,
  benchmark endpoint policy, bounded transport and response limits (66 branches)
- Web: ESLint, TypeScript, 2 existing shell tests and Vite build passed
- Python: wheel and sdist built; dependency consistency passed
- Remote Windows/Ubuntu CI: release-candidate verification pending. Run
  `34127285161` caught a Linux-only typecheck error in the Windows process flag;
  the flag lookup is now portable, and local typechecking explicitly passes for
  both Linux and Windows targets. Run `34127684736` checks that correction;
  the final versioned release candidate must also pass before closure.

No official FLOP score, public hosted site, signing, or functional dashboard is
claimed. Stage 6 is not open until the corrected Stage 5 remote gate passes.

Method references: [NVIDIA NVML reference](https://docs.nvidia.com/deploy/pdf/NVML_API_Reference_Guide.pdf),
[llama.cpp tokenizer API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#post-tokenize-tokenize-a-given-text).
