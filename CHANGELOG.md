# Changelog

All notable changes to FlopBench are documented in this file. The project follows Semantic Versioning and uses Conventional Commits.

## [Unreleased]

## [0.7.0] - 2026-09-11

### English

- Added RFC 8785/JCS signing requests bound to report digest, schema, existing
  Ed25519 `did:key`, algorithms, and a local UTC signing declaration.
- Added offline Ed25519 receipt creation and verification with strict base58btc,
  multicodec, and canonical unpadded base64url validation.
- Added an external-signer-only trust boundary, bilingual security guidance,
  RFC 8032 interoperability vectors, and complete critical branch coverage.

### Türkçe

- Rapor özeti, şema, mevcut Ed25519 `did:key`, algoritmalar ve yerel UTC imza
  beyanına bağlı RFC 8785/JCS imza istekleri eklendi.
- Katı base58btc, multicodec ve canonical padding'siz base64url doğrulamasıyla
  çevrimdışı Ed25519 receipt oluşturma ve doğrulama eklendi.
- Yalnız haricî signer kullanan güven sınırı, iki dilli güvenlik rehberi, RFC
  8032 uyumluluk vektörleri ve kritik yollarda tam dal kapsamı eklendi.

## [0.6.0] - 2026-09-10

### English

- Added a loopback-only FastAPI service protected by startup-token, Host, and Origin checks.
- Added a restrained orange React dashboard with Turkish/English language selection, light and dark themes, live miner and validator readiness, user-initiated mock benchmarks, and public-report privacy preview.
- Added Chromium end-to-end, XSS, keyboard, refresh-safety, and basic WCAG 2.2 AA coverage on Windows and Ubuntu CI.

### Türkçe

- Başlangıç token'ı, Host ve Origin kontrolleriyle korunan yalnızca loopback FastAPI servisi eklendi.
- Türkçe/İngilizce dil seçimi, açık ve koyu tema, canlı miner ve validator readiness, kullanıcı tarafından başlatılan mock benchmark ve public rapor gizlilik önizlemesi içeren sade turuncu React dashboard eklendi.
- Windows ve Ubuntu CI üzerinde Chromium uçtan uca, XSS, klavye, yenileme güvenliği ve temel WCAG 2.2 AA kapsamı eklendi.

## [0.5.0] - 2026-09-09

### English

- Added private, support, and public report exports with RFC 8785 canonical JSON and SHA-256 provenance.
- Added digest-bound public preview consent, standalone offline HTML, terminal summaries, bounded diff, and compatibility-gated benchmark comparison.
- Added strict report schema validation and security coverage for secret leakage, HTML injection, symbolic links, malformed input, and oversized input.

### Türkçe

- RFC 8785 canonical JSON ve SHA-256 provenance ile private, support ve public rapor dışa aktarımları eklendi.
- Digest'e bağlı public önizleme onayı, bağımsız çevrimdışı HTML, terminal özetleri, sınırlı diff ve uyumluluk kapılı benchmark karşılaştırması eklendi.
- Secret sızıntısı, HTML injection, sembolik bağlantı, bozuk girdi ve aşırı büyük girdi için katı rapor şema doğrulaması ve güvenlik kapsamı eklendi.

## [0.4.0] - 2026-09-07

### English

- Added deterministic mock, Ollama, and OpenAI-compatible streaming benchmark adapters.
- Added versioned workloads, complete run accounting, nearest-rank p50/p95 metrics, bounded endpoint policy, and NVML peak-VRAM sampling.
- Corrected end-to-end timing, bounded DNS/TCP/TLS/stream cancellation, partial-result accounting, and metric confidence labels; added cross-platform security gates.

### Türkçe

- Deterministik mock, Ollama ve OpenAI-compatible streaming benchmark adapter'ları eklendi.
- Sürümlü workload'lar, eksiksiz run muhasebesi, nearest-rank p50/p95 metrikleri, sınırlı endpoint politikası ve NVML peak-VRAM örneklemesi eklendi.
- Uçtan uca zaman ölçümü, sınırlı DNS/TCP/TLS/akış iptali, kısmi sonuç muhasebesi ve metrik güven etiketleri düzeltildi; platformlar arası güvenlik kapıları eklendi.

## [0.3.0] - 2026-09-07

### English

- Added consent-gated, bounded disk, TCP-connect network, and optional NTP health tests.
- Added deterministic active-test fixtures, cleanup guarantees, and a validator-doctor schema.

### Türkçe

- Onay kapılı, sınırlı disk, TCP bağlantı ağı ve isteğe bağlı NTP sağlık testleri eklendi.
- Deterministik aktif test fixture'ları, temizleme garantileri ve validator-doctor şeması eklendi.

## [0.2.0] - 2026-08-31

### English

- Added explainable miner and validator readiness evaluation with stable reason codes.
- Kept sourced profile results separate from FlopBench community health checks.

### Türkçe

- Kararlı reason code değerleriyle açıklanabilir miner ve validator readiness değerlendirmesi eklendi.
- Kaynak profil sonuçları FlopBench topluluk sağlık kontrollerinden ayrı tutuldu.

## [0.1.0] - 2026-08-31

### English

- Added passive local OS, CPU, memory, disk, and NVIDIA NVML probing with safe GPU fallbacks.
- Added deterministic hardware fixtures, public/private output, a published probe schema, and zero-network/security gates.

### Türkçe

- Pasif yerel OS, CPU, bellek, disk ve NVIDIA NVML probe'u ile güvenli GPU fallback'leri eklendi.
- Deterministik donanım fixture'ları, public/private çıktı, yayımlanmış probe şeması ve sıfır ağ/güvenlik kapıları eklendi.

## [0.1.0-alpha.1] - 2026-08-30

### English

- Added the sourced `flop-teaser-0.1` draft profile with normalized capacity and network units.
- Added strict Pydantic contracts and deterministic Draft 2020-12 JSON Schemas for profiles, readiness reports, benchmark reports, and receipts.
- Added safe UTF-8/LF YAML loading, duplicate-key rejection, raw-file SHA-256 identity, fixtures, and Stage 1 acceptance tests.

### Türkçe

- Normalize edilmiş kapasite ve ağ birimleriyle kaynaklı `flop-teaser-0.1` taslak profili eklendi.
- Profil, readiness raporu, benchmark raporu ve receipt için katı Pydantic sözleşmeleri ile deterministik Draft 2020-12 JSON Schema dosyaları eklendi.
- Güvenli UTF-8/LF YAML yükleme, çift anahtar reddi, ham dosya SHA-256 kimliği, fixture'lar ve Aşama 1 kabul testleri eklendi.

## [0.0.1] - 2026-08-30

### English

- Established the Apache-2.0 monorepo foundation for Python and React development.
- Added pinned Python and pnpm dependency workflows, Windows/Ubuntu CI, and local quality tasks.
- Added the local-only Stage 0 dashboard, project governance documents, and architecture decisions.
- Verified lint, type checking, tests, builds, and the Windows/Ubuntu GitHub Actions matrix.

### Türkçe

- Python ve React geliştirmesi için Apache-2.0 lisanslı monorepo temeli kuruldu.
- Sabitlenmiş Python ve pnpm bağımlılık iş akışları, Windows/Ubuntu CI ve yerel kalite görevleri eklendi.
- Yalnızca yerelde çalışan Aşama 0 dashboard'u, proje yönetişim belgeleri ve mimari kararlar eklendi.
- Lint, tip kontrolü, testler, derlemeler ve Windows/Ubuntu GitHub Actions matrisi doğrulandı.
