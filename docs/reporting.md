# Reports, privacy, and comparison

Stage 6 adds a local report-export envelope around existing FlopBench reports.
The envelope records its disclosure level, provenance, optional source-profile
binding, and a SHA-256 digest of the RFC 8785 JSON Canonicalization Scheme (JCS)
bytes of the `document` object. The digest detects changes; it is not a signature
and does not prove identity, hardware ownership, eligibility, or rewards.

## Disclosure profiles

- `private` retains detailed local identifiers, but refuses credential-like
  strings such as API-token labels and private-key PEM markers.
- `support` removes host/user/IP, disk path/device, GPU serial/bus, active-test
  network target, and clock server fields while retaining OS version details.
- `public` applies support redaction and also removes the OS version/build.

Public output can be previewed on stdout. Writing it to disk requires
`--confirm-preview` with the exact document digest emitted by that preview. This
binds consent to the bytes about to be written. Existing files and symbolic-link
inputs are refused; report input is capped at 8 MiB.

```powershell
flopbench report export benchmark.json `
  --privacy public `
  --profile profiles/flop-teaser-0.1.yaml

flopbench report export benchmark.json `
  --privacy public `
  --profile profiles/flop-teaser-0.1.yaml `
  --format html `
  --output public-report.html `
  --confirm-preview <preview-digest>
```

HTML exports are standalone files with inline CSS, no JavaScript, no external
resources, and a restrictive Content Security Policy. Every untrusted field is
HTML-escaped.

## Comparison methodology

`flopbench report diff LEFT RIGHT` provides a bounded structural diff of two
verified exports. It is descriptive and does not imply that measurements are
comparable.

`flopbench report compare LEFT RIGHT` only calculates metric deltas for v2
benchmark reports when all of these conditions match:

- exact source-profile reference, including its raw-file SHA-256;
- workload identity, version, raw-file SHA-256, warmup count, and measured count;
- complete adapter identity, including runtime version and endpoint scope;
- exact model name and content digest;
- metric unit and confidence label.

Missing or different profiles, workloads, adapters, units, or confidence labels
produce explicit reason codes and an empty metric list. A positive delta means
the right-hand p50 value is numerically higher; it is not automatically “better”
because latency, throughput, and memory have different desired directions.

## Determinism and provenance

Canonicalization rejects duplicate JSON fields, non-finite numbers, unsafe
integers, invalid UTF-8, and values outside the JCS domain. Re-exporting identical
input with the same tool and profile bytes produces identical canonical JSON and
digest. Private exports may contain the source report's JCS digest for local
traceability; support and public exports deliberately omit it to avoid
fingerprinting private source content.
