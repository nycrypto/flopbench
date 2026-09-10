# Local dashboard

## Scope

The Stage 7 dashboard is a bilingual working surface for local readiness,
deterministic mock benchmarking, and public-report privacy previews. It is not
hosted and does not provide an official FLOP eligibility score.

## Start

Build the web assets and start the integrated loopback service:

```powershell
pnpm --filter @flopbench/web build
flopbench serve
```

Open `http://127.0.0.1:4173`. The server accepts literal loopback addresses
only. Remote binding is not a v1 feature.

## Security boundary

- A random token is created for every server process and injected only into the
  same-origin dashboard document.
- API requests other than the health check require that token.
- Host and Origin validation reduce DNS-rebinding and cross-site request risks.
- CSP, no-store caching, MIME sniffing protection, and a no-referrer policy are
  applied to responses.
- Fixture selection uses fixed identifiers rather than user-supplied paths.
- Benchmark model names and report data are rendered as text, not HTML.

## Behavior

The overview runs a passive public probe and evaluates miner or validator
readiness against the bundled versioned profile. `unknown`, `skipped`, and
`unsupported` remain visually distinct from `fail`.

The dashboard never starts a benchmark on load or browser refresh. The mock
benchmark runs only after the user activates its button. Public report preview
lists categories removed from sharing before showing its JCS digest.

Turkish and English are first-class interface languages. The browser language
is used on the first visit; explicit language and light/dark theme choices are
stored only in browser local storage.

## Test

```powershell
pnpm --filter @flopbench/web test
pnpm --filter @flopbench/web build
pnpm --filter @flopbench/web e2e
```

The E2E suite uses Chromium and includes a basic WCAG 2.2 AA scan.
