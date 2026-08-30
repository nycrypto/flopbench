# Changelog

All notable changes to FlopBench are documented in this file. The project follows Semantic Versioning and uses Conventional Commits.

## [Unreleased]

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
