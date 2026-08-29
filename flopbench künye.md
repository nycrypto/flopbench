# FlopBench Proje Künyesi

> FLOP Network için yerel çalışan donanım hazırlık, inference benchmark, doğrulanabilir rapor ve PoUI simülasyon çalışma alanı.

## 1. Belge kontrolü

| Alan | Değer |
|---|---|
| Belge adı | FlopBench Proje Künyesi |
| Belge sürümü | 0.1.0 |
| Belge tarihi | 29 Ağustos 2026 |
| Belge durumu | Uygulama öncesi onaya hazır taslak |
| Proje türü | Açık kaynak, topluluk tarafından geliştirilen araç |
| Önerilen depo adı | `flopbench` |
| Önerilen lisans | Apache-2.0 |
| Ana dokümantasyon dili | İngilizce |
| İkinci dokümantasyon dili | Türkçe |
| Resmî proje durumu | FLOP Labs veya Flop Foundation ürünü değildir |
| Hedef ilk kararlı sürüm | `v1.0.0` |

### 1.1 Belgenin amacı

Bu belge FlopBench'in ürün tanımını, kapsamını, teknik mimarisini, güvenlik sınırlarını, veri sözleşmelerini, aşamalı geliştirme yol haritasını ve her aşamanın bağımsız olarak nasıl test edileceğini tanımlar.

Belge tamamlanmış FLOP protokolü varmış gibi davranmaz. FLOP Network teaser belgesi `Version 0.1 (draft)` durumundadır; Yellow Paper, testnet istemcisi ve nihai API sözleşmeleri henüz kamuya açık değildir. Bu nedenle resmî olmayan bütün eşikler, skorlar ve simülasyon davranışları açıkça `community`, `mock` veya `provisional` olarak etiketlenecektir.

## 2. Proje kimliği

### 2.1 Ürün adı

**FlopBench**

### 2.2 Tek cümlelik tanım

FlopBench; gelecekteki FLOP miner, validator ve agent katılımcılarının sistemlerini yerel olarak ölçmesine, inference iş yüklerini kıyaslamasına, paylaşılabilir raporlar üretmesine ve PoUI akışını güvenli bir simülasyonda incelemesine yardımcı olan açık kaynaklı bir hazırlık çalışma alanıdır.

### 2.3 İngilizce kısa tanım

> Local-first readiness, benchmarking and proof-of-inference workbench for future FLOP miners, validators and AI agents.

### 2.4 Temel problem

FLOP Network miner, validator ve agent rollerinden oluşan bir inference ekonomisi öneriyor. Buna rağmen bugün katılımcıların şu sorularına yanıt veren ortak ve doğrulanabilir bir araç bulunmuyor:

- Donanımım yayımlanan geçici önerileri karşılıyor mu?
- Yerel inference performansım nedir?
- Ölçümüm başka bir makinede tekrar üretilebilir mi?
- Hangi metrik gerçek ölçüm, hangisi tahmin veya simülasyon?
- Bir agent–miner–validator oturumu kavramsal olarak nasıl ilerliyor?
- Hangi bilgileri güvenle paylaşabilirim?
- FLOP spesifikasyonu değiştiğinde eski raporun hangi profile göre üretildiği nasıl anlaşılır?

### 2.5 Çözüm özeti

FlopBench bu problemi beş bileşenle çözer:

1. **Readiness Probe:** Donanım ve çalışma ortamını yerel olarak tespit eder.
2. **Inference Benchmark:** Tekrarlanabilir inference testleri çalıştırır.
3. **Validator Doctor:** CPU, RAM, disk, ağ ve saat sağlığını kontrol eder.
4. **Verifiable Reports:** Sürümlü, redakte edilebilir ve isteğe bağlı imzalanabilir rapor üretir.
5. **PoUI Simulator:** Resmî protokol olduğunu iddia etmeden agent–miner–validator–challenge akışını öğretir.

## 3. Kaynak ve doğruluk politikası

### 3.1 Kaynak önceliği

Uygulamada parametre kaynağı şu sırayla belirlenir:

1. Nihai FLOP Yellow Paper veya resmî protokol spesifikasyonu
2. FLOP Labs/Flop Foundation tarafından yayımlanan resmî testnet dokümanı
3. Resmî FLOP teaser belgesi
4. Resmî `flop-labs` GitHub depoları ve sürümleri
5. Açıkça işaretlenmiş FlopBench topluluk varsayımları

Topluluk rehberleri resmî parametre kaynağı olarak kullanılmaz.

### 3.2 Başlangıç referansları

- [FLOP resmî sitesi](https://flop.finance/)
- [FLOP Network Teaser v0.1](https://flop.finance/teaser/)
- [FLOP Labs GitHub organizasyonu](https://github.com/flop-labs)
- [Technocore resmî deposu](https://github.com/flop-labs/technocore-chat)
- [Technocore protokol dokümanı](https://technocore.chat/llms.txt)
- [Technocore kimlik ve imza dokümanı](https://technocore.chat/auth.md)
- [DID ve yararlı katkı hakkındaki FLOP Labs duyurusu](https://x.com/flop_labs/status/2091830155270672521)
- [Testnet faaliyeti ve Technocore faucet açıklaması](https://x.com/flop_labs/status/2092286130041565223)

### 3.3 Parametrelerin kodda tutulması

FLOP'a ait geçici değerler uygulama koduna dağınık biçimde yazılmayacaktır. Her kaynak ayrı ve sürümlü bir profil dosyasında tutulacaktır:

```yaml
id: flop-teaser-0.1
source_url: https://flop.finance/teaser/
source_status: draft
retrieved_at: 2026-08-29
parameters:
  miner:
    recommended_vram_gb: 16
  validator:
    recommended_cpu_cores: 8
    recommended_memory_gb: 64
    recommended_nvme_tb: 2
    recommended_network_gbps: 1
```

Her rapor kullanılan profil kimliğini ve profil dosyasının SHA-256 özetini taşımalıdır. Böylece gelecekte parametreler değişse bile eski raporun hangi kurallara göre üretildiği anlaşılır.

## 4. Ürün ilkeleri

1. **Yerel öncelikli:** Ölçüm verileri varsayılan olarak cihazdan çıkmaz.
2. **Doğrulanabilir:** Her metrik kaynak, birim ve ölçüm yöntemiyle birlikte kaydedilir.
3. **Sürümlü:** Rapor, profil ve şema sürümleri birbirinden bağımsız yönetilir.
4. **Resmîlik iddiası yok:** Topluluk skoru ile FLOP protokol gerekliliği birbirine karıştırılmaz.
5. **Gizlilik varsayılanı:** Hostname, kullanıcı adı, IP ve seri numarası paylaşılmaz.
6. **GPU'suz test edilebilirlik:** CI ve geliştirici testleri fiziksel GPU gerektirmeden fixture/mock verileriyle çalışır.
7. **Tekrarlanabilirlik:** Aynı fixture aynı normalize edilmiş raporu üretir.
8. **Açıklanabilir sonuç:** Kullanıcıya yalnızca skor değil, skorun veya sonucun nedeni gösterilir.
9. **Güvenli imzalama:** Özel DID anahtarı web arayüzüne veya arka plan servisine verilmez.
10. **Geleceğe uyum:** Resmî testnet adaptörü çekirdeğe gömülmez; ayrı bir adaptör olarak eklenir.

## 5. Hedef kullanıcılar

### 5.1 Miner adayı

GPU'sunun kapasitesini, model çalışma performansını, gecikmesini, VRAM kullanımını ve uzun yük altındaki kararlılığını görmek ister.

### 5.2 Validator adayı

CPU, RAM, NVMe, ağ, NTP/saat, container çalışma ortamı ve uzun süreli hizmet kararlılığını kontrol etmek ister.

### 5.3 Agent geliştiricisi

Model, maksimum gecikme, gizlilik ve bütçe gibi alanlarla inference session oluşturmayı; yanıt, receipt ve challenge akışını deneyimlemek ister.

### 5.4 Araştırmacı ve topluluk üyesi

FLOP'un PoUI yaklaşımını görsel, tekrar üretilebilir ve dürüstçe sınırlandırılmış bir laboratuvarda incelemek ister.

### 5.5 Entegrasyon geliştiricisi

Sürümlü JSON şemalarını, adaptör sözleşmelerini ve örnek fixture'ları kullanarak yeni runtime veya testnet bağlantısı eklemek ister.

## 6. Hedefler ve başarı ölçütleri

### 6.1 Ürün hedefleri

- Windows ve Linux üzerinde aynı rapor şemasını üretmek.
- GPU olmayan bir makinede anlaşılır hata yerine `cpu-only`/`no-supported-gpu` sonucu vermek.
- NVIDIA, AMD ve bilinmeyen GPU durumlarını sağlayıcı eklentileriyle ayırmak.
- Kullanıcı izni olmadan ağ üzerinden rapor göndermemek.
- Miner ve validator kontrollerini ayrı çalıştırabilmek.
- Gerçek ölçüm ile tahmini FLOP hesabını ayrı alanlarda göstermek.
- Testnet olmadan mock session ve challenge akışını çalıştırabilmek.
- İsteğe bağlı olarak rapor hash'ini Technocore DID ile imzalayabilmek.

### 6.2 Ölçülebilir kalite hedefleri

| Alan | Hedef |
|---|---|
| Çekirdek birim testleri | En az %85 satır kapsamı |
| Kritik güvenlik/redaksiyon modülleri | %100 dal kapsamı hedefi |
| JSON Schema örnek doğrulaması | Tüm fixture'larda başarılı |
| CI işletim sistemleri | Windows ve Ubuntu |
| Probe süresi | Normal sistemde 30 saniyenin altında |
| Varsayılan ağ erişimi | Sıfır |
| Varsayılan gizli alan sızıntısı | Sıfır tolerans |
| Aynı fixture için deterministik çıktı | Bayt düzeyinde aynı normalize edilmiş JSON |
| Web erişilebilirliği | Temel WCAG 2.2 AA kontrolleri |
| Release bütünlüğü | SHA-256 checksum ve SBOM |

Bu hedefler FLOP Labs gerekliliği değil, FlopBench kalite hedefidir.

## 7. Kapsam

### 7.1 İlk kararlı sürüm kapsamı

- Sistem ve donanım tespiti
- Miner readiness değerlendirmesi
- Validator readiness değerlendirmesi
- Yerel/uyumlu endpoint üzerinde inference benchmark
- Makine tarafından okunabilir JSON raporu
- İnsan tarafından okunabilir HTML raporu
- Gizlilik redaksiyonu
- Yerel web dashboard
- İsteğe bağlı DID imzalı report receipt
- Mock PoUI session ve challenge simülasyonu
- Windows ve Linux paketleme
- İngilizce ve Türkçe temel dokümantasyon

### 7.2 Kapsam dışı

- Airdrop puanı veya token miktarı tahmini
- Claim sitesi, claim otomasyonu veya eligibility checker
- Cüzdan oluşturma, bağlama veya seed saklama
- Token transferi, stake veya gerçek slashing
- Otomatik Technocore spam/check-in/heartbeat
- Resmî FLOP node, miner ya da validator istemcisi olduğunu iddia etmek
- TEE veya TOPLOC'un üretim seviyesinde gerçek implementasyonu olduğunu iddia etmek
- Donanım seri numarası veya IP adresi toplayan merkezi skor tablosu
- Token fiyatı veya yatırım getirisi tahmini
- Kullanıcının açık izni olmadan benchmark sonucu yayımlamak
- Nihai FLOP protokolüne aitmiş gibi uydurma API alanları sunmak

## 8. Ana kullanıcı akışları

### 8.1 Miner akışı

```text
Kurulum
  → Yerel sistem taraması
  → Desteklenen runtime seçimi
  → Kısa benchmark
  → İsteğe bağlı uzun kararlılık testi
  → Readiness sonuçları
  → Hassas alan önizlemesi
  → JSON/HTML rapor
  → İsteğe bağlı harici imza
```

### 8.2 Validator akışı

```text
Kurulum
  → CPU/RAM/NVMe/ağ/saat kontrolleri
  → Resmî taslak profil ile karşılaştırma
  → PASS/WARN/FAIL/UNKNOWN sonuçları
  → Darboğaz önerileri
  → Redakte edilmiş rapor
```

### 8.3 Agent simülasyon akışı

```text
Model ve bütçe seçimi
  → Session request oluşturma
  → Mock miner kabulü
  → Inference veya fixture sonucu
  → Execution receipt
  → Validator örnekleme
  → PASS veya CHALLENGE
  → Simüle edilmiş muhasebe sonucu
```

### 8.4 Rapor imzalama akışı

```text
Rapor üretimi
  → Redaksiyon önizlemesi
  → Canonical JSON
  → SHA-256 digest
  → İnsan tarafından terminalde onay
  → DID imzası
  → Ayrı receipt dosyası
  → Anahtarsız offline doğrulama
```

## 9. Teknik mimari

### 9.1 Genel mimari

```text
┌─────────────────────────────────────────────────────────────┐
│                         Web UI                              │
│ Readiness · Charts · Report Preview · PoUI Playground      │
└──────────────────────────────┬──────────────────────────────┘
                               │ localhost only
┌──────────────────────────────▼──────────────────────────────┐
│                       Local API                             │
│ Read-only by default · Explicit commands for active tests  │
└─────────────┬────────────────┬────────────────┬─────────────┘
              │                │                │
┌─────────────▼──────┐ ┌──────▼────────┐ ┌─────▼─────────────┐
│ Hardware Probe    │ │ Benchmark Core │ │ PoUI Simulator    │
└─────────────┬──────┘ └──────┬────────┘ └─────┬─────────────┘
              │                │                │
┌─────────────▼────────────────▼────────────────▼─────────────┐
│ Schema · Profiles · Redaction · Canonicalization · Reports │
└──────────────────────────────┬──────────────────────────────┘
                               │ explicit human approval
┌──────────────────────────────▼──────────────────────────────┐
│ Optional External DID Signer / Future Testnet Adapters     │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Güven sınırları

- Web UI yalnızca loopback adresine bağlanır.
- Yerel API varsayılan olarak internete açılmaz.
- Web UI özel DID anahtarına erişemez.
- Probe sistemi pasif tespitle başlar; ağır benchmark ayrıca kullanıcı onayı ister.
- Dış endpoint benchmark'ı yalnızca kullanıcı tarafından açıkça verilen allowlist adreslerine gider.
- Report signer ayrı süreç ve ayrı sorumluluk olarak tasarlanır.
- Testnet adaptörü yayınlandığında çekirdek rapor üretiminden ayrılmış kalır.

### 9.3 Önerilen teknoloji seti

| Katman | Öneri | Gerekçe |
|---|---|---|
| Çekirdek/CLI | Python 3.12+ | Sistem ölçümü ve ML runtime entegrasyonu |
| CLI framework | Typer | Test edilebilir ve okunabilir komut yapısı |
| Veri modeli | Pydantic v2 | Güçlü doğrulama ve JSON Schema üretimi |
| Yerel API | FastAPI | Şema uyumu ve yerel dashboard entegrasyonu |
| Sistem ölçümü | `psutil` + sağlayıcı adaptörleri | Platformlar arası temel metrikler |
| NVIDIA ölçümü | NVML adaptörü | VRAM, sıcaklık ve güç ölçümü |
| AMD ölçümü | Ayrı opsiyonel adaptör | Çekirdeği sürücü bağımlılığından ayırmak |
| Web | React + TypeScript + Vite | Hızlı, tip güvenli dashboard |
| Grafik | Hafif, erişilebilir chart katmanı | Zaman serisi ve karşılaştırmalar |
| Test | pytest + Vitest + Playwright | Birim, sözleşme ve E2E testleri |
| Paketleme | Python wheel + platform scriptleri | Kolay kurulum ve tekrarlanabilir release |
| CI | GitHub Actions | Windows/Linux matrisi |

Kesin sürümler uygulama başlangıcında kilit dosyalarına sabitlenecektir. `latest` etiketi üretim veya CI içinde kullanılmayacaktır.

### 9.4 Önerilen depo yapısı

```text
flopbench/
├── apps/
│   ├── api/                         # Yerel FastAPI uygulaması
│   └── web/                         # React dashboard
├── src/flopbench/
│   ├── cli/                         # Komutlar
│   ├── probe/                       # Donanım ve ortam tespiti
│   │   └── providers/               # NVIDIA/AMD/CPU sağlayıcıları
│   ├── validator_doctor/            # Validator kontrolleri
│   ├── benchmark/                   # Benchmark motoru
│   │   └── adapters/                # Mock/Ollama/OpenAI-compatible
│   ├── simulator/                   # PoUI mock durum makinesi
│   ├── profiles/                    # FLOP kaynak profilleri
│   ├── reports/                     # Oluşturma ve dışa aktarma
│   ├── redaction/                   # Gizlilik filtresi
│   ├── receipts/                    # Canonicalization ve imza doğrulama
│   └── common/                      # Hata ve ortak tipler
├── schemas/                         # Yayınlanan JSON Schema dosyaları
├── profiles/                        # Sürümlü profil YAML dosyaları
├── fixtures/                        # CI için sahte donanım/benchmark verileri
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── security/
│   └── e2e/
├── docs/
│   ├── architecture.md
│   ├── security-model.md
│   ├── protocol-mapping.md
│   ├── benchmark-methodology.md
│   ├── privacy.md
│   └── limitations.md
├── .github/
│   └── workflows/
├── README.md
├── README.tr.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
└── package.json
```

## 10. Alan modeli ve rapor sözleşmesi

### 10.1 Sonuç durumları

Her kontrol yalnızca aşağıdaki durumlardan birini döndürür:

| Durum | Anlamı |
|---|---|
| `pass` | Seçili profil şartını karşılıyor |
| `warn` | Çalışıyor fakat risk veya düşük marj var |
| `fail` | Şartı karşılamıyor veya test başarısız |
| `unknown` | Güvenilir ölçüm yapılamadı |
| `skipped` | Kullanıcı tarafından çalıştırılmadı |
| `unsupported` | Platform veya sağlayıcı desteklenmiyor |

`unknown`, `fail` olarak; `unsupported` ise donanımın yetersiz olduğu şeklinde gösterilmez. Kullanıcıya ölçülemeyen şey açıkça söylenir.

### 10.2 Metrik güven düzeyi

Her metrik şunlardan birini taşır:

- `measured`: Doğrudan araç veya işletim sisteminden ölçüldü.
- `reported`: Sürücü veya runtime tarafından bildirildi.
- `derived`: Ölçülen alanlardan hesaplandı.
- `estimated`: Model veya varsayımla tahmin edildi.
- `simulated`: Gerçek donanım/ağ sonucu değil.

Bu alan UI'da gizlenmez.

### 10.3 Readiness raporu asgari şeması

```json
{
  "schema": "flopbench-readiness-report-v1",
  "report_id": "uuid",
  "role": "miner",
  "profile": {
    "id": "flop-teaser-0.1",
    "sha256": "...",
    "status": "draft"
  },
  "environment": {
    "os_family": "windows",
    "architecture": "x86_64",
    "privacy_level": "public"
  },
  "checks": [],
  "summary": {
    "pass": 0,
    "warn": 0,
    "fail": 0,
    "unknown": 0
  },
  "created_at": "RFC3339 UTC",
  "tool_version": "0.1.0"
}
```

### 10.4 Benchmark raporu asgari şeması

```json
{
  "schema": "flopbench-benchmark-report-v1",
  "benchmark_id": "uuid",
  "adapter": "mock",
  "model": {
    "name": "fixture-model",
    "digest_algorithm": "sha256",
    "digest": "..."
  },
  "workload": {
    "id": "smoke-v1",
    "prompt_set_digest": "...",
    "warmup_runs": 1,
    "measured_runs": 3
  },
  "metrics": {
    "time_to_first_token_ms": {},
    "tokens_per_second": {},
    "latency_ms": {},
    "peak_vram_bytes": {},
    "error_rate": {}
  },
  "started_at": "RFC3339 UTC",
  "finished_at": "RFC3339 UTC"
}
```

### 10.5 İmzalı receipt

İmza doğrudan büyük rapor dosyasına değil, canonical rapor digest'ine uygulanır:

```json
{
  "schema": "flopbench-receipt-v1",
  "report_schema": "flopbench-readiness-report-v1",
  "report_sha256": "...",
  "did": "did:key:z6Mk...",
  "canonicalization": "jcs-rfc8785",
  "signature_algorithm": "Ed25519",
  "signature": "base64url",
  "signed_at": "RFC3339 UTC"
}
```

`signed_at` yerel beyan niteliğindedir; güvenilir zaman damgası olarak sunulmaz. Technocore sequence ve server timestamp değerleri de DID imzasının otomatik parçası sayılmaz.

## 11. Readiness değerlendirme politikası

### 11.1 Resmî profil sonucu

Resmî kaynakta açıkça yayımlanan şartlar ayrı gösterilir:

```text
FLOP teaser 0.1 miner recommendation
VRAM 16 GB or higher: PASS
```

### 11.2 Topluluk sağlık sonucu

Sıcaklık marjı, uzun yük kararlılığı, disk IOPS veya jitter gibi FlopBench değerlendirmeleri ayrı başlık taşır:

```text
FlopBench community health check
Sustained thermal stability: WARN
```

Bu iki sonuç birleştirilerek “resmî FLOP skoru” oluşturulmaz.

### 11.3 Skor kullanımı

MVP'de tek bir 0–100 toplam skor yerine `PASS/WARN/FAIL/UNKNOWN` özeti tercih edilir. Daha sonra kullanıcı araştırması toplam skorun yararlı olduğunu gösterirse skor eklenebilir; bu skor her zaman `FlopBench Community Score` adıyla ve açık formülle sunulur.

## 12. Benchmark metodolojisi

### 12.1 Benchmark türleri

1. **Smoke:** Kurulum ve adapter çalışıyor mu?
2. **Short:** Hızlı karşılaştırma; az tekrar.
3. **Standard:** Isınma ve yeterli tekrarlarla ana rapor.
4. **Sustained:** Termal ve kararlılık için uzun çalışma.

### 12.2 Temel metrikler

- Time to first token (TTFT)
- Input/prefill süresi
- Output/decode süresi
- Token/saniye
- Toplam latency
- p50, p95 ve maksimum latency
- Başarısız istek oranı
- Peak ve ortalama VRAM
- GPU utilization — sağlayıcı destekliyorsa
- Sıcaklık — sağlayıcı destekliyorsa
- Güç/enerji — sağlayıcı destekliyorsa
- Runtime ve model başlatma süresi
- Tahmini FLOP — ölçüm olmadığı açıkça belirtilerek

### 12.3 Tekrarlanabilirlik şartları

- Prompt seti sürümlü ve hash'li olmalıdır.
- Model digest'i kaydedilmelidir.
- Runtime sürümü kaydedilmelidir.
- Warmup çalışmaları ölçümden ayrılmalıdır.
- Sistem saati UTC olarak yazılmalıdır.
- Ortalama tek başına kullanılmamalı; dağılım metrikleri verilmelidir.
- Hatalı çalıştırmalar rapordan sessizce çıkarılmamalıdır.
- Rastgelelik kullanılıyorsa seed ve generation parametreleri kaydedilmelidir.

### 12.4 Adil karşılaştırma sınırı

Farklı quantization, context length, batch size, runtime veya generation parametrelerine sahip raporlar doğrudan eşdeğer olarak sıralanmaz. UI karşılaştırma yapmadan önce uyumsuz alanları gösterir.

## 13. Güvenlik ve gizlilik modeli

### 13.1 Korunacak varlıklar

- DID özel anahtarı ve parolası
- Cüzdan seed'i ve cüzdan özel anahtarı
- API anahtarları
- İşletim sistemi kullanıcı adı
- Hostname ve yerel dosya yolları
- IP/MAC adresleri
- Donanım seri numaraları
- Model dosyalarının özel konumları
- Benchmark prompt'larında bulunabilecek hassas içerik

### 13.2 Kesin yasaklar

- Cüzdan seed'i veya özel anahtar istemek
- DID anahtarını tarayıcı depolamasına koymak
- Parolayı komut satırı argümanı olarak almak
- Gizli alanları hata loguna yazmak
- Varsayılan olarak public leaderboard'a yüklemek
- Kullanıcı onayı olmadan Technocore'a mesaj göndermek
- Redirect takip ederek bilinmeyen hosta benchmark isteği göndermek
- Shell komutu oluştururken kullanıcı girdisini doğrudan birleştirmek

### 13.3 Redaksiyon seviyeleri

| Seviye | Kullanım | İçerik |
|---|---|---|
| `private` | Yerel teşhis | Ayrıntılı fakat secret içermeyen veri |
| `support` | Hata bildirimi | Yol, kullanıcı ve ağ bilgileri redakte |
| `public` | GitHub/X paylaşımı | Yalnızca genel donanım sınıfı ve benchmark |

### 13.4 Tehdit modeli testleri

- Hostname rapora sızıyor mu?
- Windows kullanıcı dizini stack trace içinde görünüyor mu?
- `.env`, PEM veya seed benzeri değerler taranıyor mu?
- Kötü amaçlı model adı HTML içine script enjekte edebiliyor mu?
- Kullanıcı tarafından verilen endpoint localhost dışına istek yaptırabiliyor mu?
- Symlink ile özel dosya rapora eklenebiliyor mu?
- Büyük/malformed adapter cevabı bellek tüketimine neden oluyor mu?
- İmza doğrulama yanlış DID codec'ini kabul ediyor mu?

## 14. Test stratejisi

### 14.1 Test katmanları

| Katman | Amaç | Fiziksel GPU gerekir mi? |
|---|---|---|
| Unit | Saf fonksiyonlar ve kurallar | Hayır |
| Schema/contract | JSON/YAML sözleşmeleri | Hayır |
| Fixture | Donanım ve runtime varyasyonları | Hayır |
| Integration | CLI–core–report akışı | Hayır, mock ile |
| Hardware integration | Gerçek sağlayıcı ölçümü | Evet, ilgili job'da |
| Web E2E | Kullanıcı akışı | Hayır |
| Security | Redaksiyon ve saldırı girdileri | Hayır |
| Manual acceptance | Gerçek Windows/Linux deneyimi | Role göre |

### 14.2 Zorunlu fixture seti

- `windows-nvidia-24gb.json`
- `linux-nvidia-16gb.json`
- `linux-amd-16gb.json`
- `cpu-only.json`
- `unsupported-gpu.json`
- `missing-driver.json`
- `low-memory-validator.json`
- `slow-disk-validator.json`
- `unstable-network.json`
- `malformed-provider-output.json`
- `secret-leak-trap.json`

`secret-leak-trap` fixture'ı bilerek sahte hostname, kullanıcı adı, IP, token ve PEM işareti içerir. `public` raporda bunlardan hiçbiri bulunmamalıdır.

### 14.3 Tek komut kalite kapıları

Repo oluşturulduğunda aşağıdaki komutlar standartlaştırılacaktır:

```text
make test-unit
make test-contract
make test-integration
make test-security
make test-web
make test-all
make lint
make typecheck
make build
```

Windows için aynı işlemler platformdan bağımsız task runner veya PowerShell scriptleri üzerinden sunulmalıdır. Make bulunmaması Windows kullanıcılarının test çalıştırmasını engellememelidir.

## 15. Aşamalı geliştirme planı

Her aşama önceki aşamanın kabul kriterlerini gerektirir. Bir aşama tamamlanmadan sonraki aşamanın çekirdek koduna geçilmez. Deneysel çalışmalar ayrı branch veya feature flag altında tutulabilir.

---

### Aşama 0 — Kararlar, depo iskeleti ve kalite kapıları

**Hedef:** Kod yazılmadan önce depo yapısını, dil sürümlerini, lisansı, kalite kurallarını ve resmîlik sınırlarını sabitlemek.

**Teslimatlar:**

- Git deposu ve temel klasör yapısı
- `README.md` ve `README.tr.md`
- `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`
- `docs/architecture.md`
- `docs/limitations.md`
- Python ve web için boş fakat çalışan test iskeleti
- Windows/Ubuntu CI matrisi
- Dependabot veya eşdeğer bağımlılık güncelleme politikası
- Conventional Commits ve SemVer kararı
- Üründe görünür “unofficial community project” bildirimi

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S0-T01 | Temiz checkout sonrası Python kurulum | Başarılı |
| S0-T02 | Temiz checkout sonrası web kurulum | Başarılı |
| S0-T03 | `lint` kalite kapısı | Uyarısız başarılı |
| S0-T04 | `typecheck` | Hatasız |
| S0-T05 | Boş/smoke test paketi | Windows ve Ubuntu'da başarılı |
| S0-T06 | Lisans ve zorunlu belge kontrolü | Eksik dosya yok |

**Çıkış kriterleri:**

- CI her iki işletim sisteminde yeşildir.
- README projenin FLOP Labs ürünü olmadığını açıkça söyler.
- Kurulum komutları temiz bir makinede doğrulanmıştır.
- Secret scanning ve dependency review etkinleştirilmiştir.

**Önerilen sürüm:** `v0.0.1`

---

### Aşama 1 — Kaynak profilleri ve veri şemaları

**Hedef:** Donanım veya UI geliştirilmeden önce veri sözleşmelerini ve FLOP kaynak profili sistemini bitirmek.

**Teslimatlar:**

- `flop-teaser-0.1.yaml`
- Profil JSON Schema
- Readiness report JSON Schema
- Benchmark report JSON Schema
- Receipt JSON Schema
- Profil yükleyici ve SHA-256 hesaplayıcı
- Kaynak URL, erişim tarihi ve `draft/provisional/final` durumları
- Geçersiz profil için anlaşılır hata modeli

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S1-T01 | Geçerli teaser profili yükleme | Başarılı |
| S1-T02 | Eksik kaynak URL'si | Şema reddeder |
| S1-T03 | Negatif RAM/VRAM değeri | Şema reddeder |
| S1-T04 | Aynı dosya için profil hash'i | Her çalışmada aynı |
| S1-T05 | Profil içeriği değişince hash | Değişir |
| S1-T06 | Bilinmeyen ek alan | Politika doğrultusunda reddedilir |
| S1-T07 | Örnek readiness raporu | Yayınlanan şemayı doğrular |
| S1-T08 | Örnek receipt | Yayınlanan şemayı doğrular |

**Çıkış kriterleri:**

- Bütün fixture raporları şemadan geçer.
- Bilerek bozuk fixture'ların tamamı beklenen hata koduyla reddedilir.
- Şema sürümleme politikası `docs/schema-versioning.md` içinde yazılıdır.

**Önerilen sürüm:** `v0.1.0-alpha.1`

---

### Aşama 2 — Pasif sistem ve donanım tespiti

**Hedef:** Ağ erişimi veya ağır yük oluşturmadan sistemin temel kapasitesini güvenli biçimde tespit etmek.

**Teslimatlar:**

- OS ve mimari tespiti
- CPU logical/physical core tespiti
- Toplam/kullanılabilir RAM
- Disk türü ve kapasitesi — güvenilir olduğu ölçüde
- GPU provider arayüzü
- NVIDIA provider
- AMD/unknown için güvenli fallback
- `flopbench probe --format json`
- `--fixture` modu
- Private/public çıktı ayrımı

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S2-T01 | NVIDIA 24 GB fixture | GPU ve VRAM doğru normalize edilir |
| S2-T02 | NVIDIA 16 GB fixture | 16 GB değeri kaybolmadan raporlanır |
| S2-T03 | CPU-only fixture | Çökmez, `no-supported-gpu` verir |
| S2-T04 | Sürücü eksik | `unknown` veya `unsupported`, stack trace yok |
| S2-T05 | Malformed provider cevabı | Kontrollü hata ve non-zero exit |
| S2-T06 | Public rapor | Hostname, kullanıcı, IP, seri numarası yok |
| S2-T07 | Probe ağ izleme | Hiçbir dış bağlantı kurulmaz |
| S2-T08 | Probe tekrar çalıştırma | Statik fixture çıktısı deterministik |

**Manuel kabul:**

- Bir Windows NVIDIA sistemi
- Bir Ubuntu sistemi
- Bir GPU'suz sistem veya fixture eşdeğeri

**Çıkış kriterleri:**

- Probe 30 saniye içinde tamamlanır.
- Fiziksel GPU olmadan bütün CI testleri geçer.
- Desteklenmeyen donanım uygulamayı çökertmez.
- Public redaksiyon güvenlik testleri sıfır sızıntıyla geçer.

**Önerilen sürüm:** `v0.1.0`

---

### Aşama 3 — Miner ve validator readiness motoru

**Hedef:** Probe verisini sürümlü profil şartlarıyla karşılaştırıp açıklanabilir sonuç üretmek.

**Teslimatlar:**

- Miner kontrol motoru
- Validator kontrol motoru
- `pass/warn/fail/unknown/unsupported` kararları
- Resmî profil sonucu ile topluluk kontrolünün ayrılması
- Darboğaz açıklamaları
- `flopbench check miner`
- `flopbench check validator`
- JSON ve terminal çıktısı

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S3-T01 | 24 GB GPU, 16 GB profil | VRAM `pass` |
| S3-T02 | Tam 16 GB GPU | Sınır değeri `pass` |
| S3-T03 | 15.99 GB normalize edilmiş değer | Yuvarlama politikasına göre `fail` |
| S3-T04 | VRAM bilinmiyor | `unknown`, otomatik `fail` değil |
| S3-T05 | Validator 8 core/64 GB/2 TB | Profil şartları `pass` |
| S3-T06 | Yetersiz RAM | Yalnız RAM kontrolü `fail` |
| S3-T07 | HDD/NVMe tespit edilemiyor | Disk türü `unknown` |
| S3-T08 | Taslak profil kullanımı | UI ve JSON'da `draft` görünür |
| S3-T09 | Topluluk testi | Resmî sonuçla aynı etikete karışmaz |

**Çıkış kriterleri:**

- Bütün kararların makine tarafından okunabilir `reason_code` değeri vardır.
- UI olmadan CLI sonucu anlaşılırdır.
- Eşik sınır testleri ve birim dönüşümleri doğrulanmıştır.
- “Eligible”, “airdrop score” veya “official score” ifadesi üretilmez.

**Önerilen sürüm:** `v0.2.0`

---

### Aşama 4 — Validator aktif sağlık testleri

**Hedef:** Pasif kapasite bilgisini disk, ağ ve saat gibi ölçülebilir sağlık testleriyle tamamlamak.

**Teslimatlar:**

- Geçici çalışma dizininde güvenli disk testi
- Disk throughput ve latency ölçümü
- NTP/saat sapması kontrolü — kullanıcı çalıştırırsa
- Ağ latency/jitter/paket kaybı adaptörü
- Test süre ve kaynak sınırları
- Aktif test öncesi kullanıcı onayı
- Test sonunda geçici dosyaların temizlenmesi

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S4-T01 | Hızlı disk fixture | Ölçüm ve birim doğru |
| S4-T02 | Yavaş disk fixture | `warn/fail` nedeni açıklanır |
| S4-T03 | Yazma izni yok | Kontrollü `skipped/unsupported` |
| S4-T04 | Kullanıcı iptal ediyor | Test başlamaz, dosya oluşmaz |
| S4-T05 | Test yarıda kesiliyor | Geçici dosya temizlenir |
| S4-T06 | Ağ tamamen kapalı | Çökmez, ağ sonucu `unknown` |
| S4-T07 | Yüksek jitter fixture | Doğru p95 ve uyarı |
| S4-T08 | NTP kaynağı erişilemiyor | Sahte başarı üretmez |

**Çıkış kriterleri:**

- Aktif testler açık onay olmadan başlamaz.
- Testler kullanıcı dosyalarına dokunmaz.
- Geçici dosyalar güvenli, sınırlandırılmış bir konumda tutulur.
- Ağ testi hedefi ve veri gönderimi ekranda açıkça görünür.

**Önerilen sürüm:** `v0.3.0`

---

### Aşama 5 — Inference benchmark çekirdeği

**Hedef:** Sağlayıcıdan bağımsız, tekrarlanabilir ve GPU'suz CI ile doğrulanabilir benchmark motoru oluşturmak.

**Teslimatlar:**

- Benchmark adapter protokolü
- Deterministik mock adapter
- OpenAI-compatible yerel endpoint adapter'ı
- En az bir yerel runtime adapter'ı
- Warmup ve measured run ayrımı
- TTFT, tokens/s, latency, error rate
- p50/p95 hesapları
- İptal, timeout ve kısmi hata yönetimi
- Sürümlü prompt/workload seti
- Model ve workload digest'i

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S5-T01 | Deterministik mock benchmark | Beklenen sabit metrikler |
| S5-T02 | Warmup çalışmaları | Ana istatistiğe dahil edilmez |
| S5-T03 | Üç başarılı çalışma | p50/p95 doğru |
| S5-T04 | Bir timeout | Error rate'e dahil edilir |
| S5-T05 | Stream yarıda kesiliyor | Kısmi sonuç açıkça işaretlenir |
| S5-T06 | Negatif/NaN süre | Reddedilir |
| S5-T07 | Farklı prompt seti | Digest değişir |
| S5-T08 | Aynı fixture | Canonical rapor deterministik |
| S5-T09 | Kullanıcı iptali | Adapter ve subprocess kapanır |
| S5-T10 | Dış endpoint allowlist dışında | İstek reddedilir |

**Gerçek donanım kabul testi:**

- Kısa benchmark en az bir NVIDIA sistemde çalıştırılır.
- Ölçüm sırasında ham runtime çıktısı ile rapor karşılaştırılır.
- Peak VRAM ve token sayımı en az bir bağımsız gözlemle doğrulanır.

**Çıkış kriterleri:**

- Benchmark mock adapter ile bütün CI platformlarında geçer.
- Hata yaşayan istekler sessizce atılmaz.
- Rapor runtime/model/workload sürümlerini içerir.
- Tahmini FLOP metriği `estimated` olarak etiketlenir.

**Önerilen sürüm:** `v0.4.0`

---

### Aşama 6 — Raporlama, redaksiyon ve dışa aktarma

**Hedef:** Teknik sonuçları güvenli, paylaşılabilir ve yeniden doğrulanabilir hale getirmek.

**Teslimatlar:**

- Private/support/public redaksiyon profilleri
- Canonical JSON export
- İnsan okunabilir HTML raporu
- Terminal özet görünümü
- Rapor diff aracı
- Aynı profile göre iki benchmark karşılaştırması
- Uyumsuz raporlarda karşılaştırma uyarıları
- Report digest ve provenance bölümü

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S6-T01 | Secret leak trap → public | Tüm gizli değerler yok |
| S6-T02 | Aynı rapor iki kez export | Aynı canonical digest |
| S6-T03 | Alan sırası değişmiş input | Aynı canonical digest |
| S6-T04 | Bir metrik değişmiş | Digest değişir |
| S6-T05 | Model adı HTML script içeriyor | Escape edilir, çalışmaz |
| S6-T06 | Farklı workload raporları | Doğrudan sıralanmaz |
| S6-T07 | HTML offline açılış | Dış kaynağa ihtiyaç duymaz |
| S6-T08 | Public rapor şema doğrulama | Başarılı |

**Çıkış kriterleri:**

- Redaksiyon modülü güvenlik testlerinde %100 dal kapsamına ulaşır.
- Public rapor kullanıcının açık önizlemesinden geçmeden yazılmaz.
- HTML raporu ağ bağlantısı olmadan açılır.
- Karşılaştırma metodolojisi belgeye eklenmiştir.

**Önerilen sürüm:** `v0.5.0`

---

### Aşama 7 — Yerel API ve web dashboard

**Hedef:** CLI yeteneklerini güvenli ve erişilebilir bir yerel arayüzde sunmak.

**Teslimatlar:**

- Sadece loopback üzerinde çalışan API
- Readiness dashboard
- Miner/validator ayrı görünümler
- Benchmark grafik ve zaman çizelgeleri
- Rapor gizlilik önizlemesi
- Kaynak profil ve `draft` göstergesi
- No-GPU ve unsupported durum tasarımları
- Klavye ile kullanılabilir temel akış
- Dark/light veya yüksek kontrast desteği

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S7-T01 | API varsayılan bind adresi | Yalnız `127.0.0.1`/`::1` |
| S7-T02 | Dış interface bind denemesi | Açık onay/flag olmadan reddedilir |
| S7-T03 | Miner fixture render | Beklenen kartlar görünür |
| S7-T04 | CPU-only fixture render | Anlaşılır boş durum |
| S7-T05 | Taslak profil | Görünür `draft` etiketi |
| S7-T06 | Malicious model name | XSS oluşmaz |
| S7-T07 | Klavye navigasyonu | Ana akış tamamlanabilir |
| S7-T08 | Public report preview | Redakte edilen alanlar görünür |
| S7-T09 | Tarayıcı yenileme | Aktif benchmark yanlışlıkla tekrar başlamaz |

**Çıkış kriterleri:**

- E2E testleri Chromium tabanlı tarayıcıda yeşildir.
- API dış ağa varsayılan olarak açılamaz.
- UI, `unknown` sonucu `fail` gibi renklendirmez.
- Temel erişilebilirlik taraması kritik hata vermez.

**Önerilen sürüm:** `v0.6.0`

---

### Aşama 8 — DID imzalı report receipt

**Hedef:** Raporu değiştirmeden, ayrı ve offline doğrulanabilir bir DID imza kanıtı oluşturmak.

**Teslimatlar:**

- RFC 8785/JCS canonicalization kararı
- SHA-256 report digest
- Ed25519/did:key doğrulayıcı
- Harici/interaktif signer arayüzü
- `flopbench receipt prepare`
- `flopbench receipt verify`
- İmzalama öncesi insan okunabilir özet
- Private key okumayan verify akışı
- Mevcut DID'i koruma ve yeni anahtar üretmeme uyarısı

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S8-T01 | Geçerli Ed25519 fixture | Doğrulama başarılı |
| S8-T02 | Raporun bir baytı değişmiş | Doğrulama başarısız |
| S8-T03 | DID değişmiş | Doğrulama başarısız |
| S8-T04 | Yanlış multicodec prefix | Reddedilir |
| S8-T05 | Geçersiz base58/base64url | Kontrollü hata |
| S8-T06 | Parola CLI argümanında | Komut reddeder |
| S8-T07 | Verify işlemi | Private key dosyası istemez |
| S8-T08 | İmza iptali | Receipt oluşmaz |
| S8-T09 | Web UI | Private key upload alanı içermez |

**Çıkış kriterleri:**

- Resmî Ed25519 test vector'ları geçer.
- Aynı report digest başka DID ile doğrulanmaz.
- Anahtar veya parola log, process argümanı ya da rapora sızmaz.
- Güvenlik modeli bağımsız belgeyle açıklanmıştır.

**Önerilen sürüm:** `v0.7.0`

---

### Aşama 9 — PoUI session ve challenge simülatörü

**Hedef:** FLOP'un önerdiği inference yaşam döngüsünü öğretmek ve ilerideki adaptörler için durum makinesi oluşturmak.

**Teslimatlar:**

- Session request şeması
- Model digest, latency sınırı, compute estimate, confidentiality ve mock fee alanları
- Agent/miner/validator aktörleri
- Session durum makinesi
- Başarılı inference senaryosu
- Yanlış model, gecikme, canned answer ve timeout senaryoları
- Validator sampling ve full re-run mock'u
- Challenge sonucu
- Açıkça simüle edilmiş stake/slashing muhasebesi
- Web üzerinde görsel akış

**Önerilen durumlar:**

```text
created
offered
accepted
running
submitted
validating
settled
challenged
rejected
timed_out
cancelled
```

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S9-T01 | Normal akış | `created → settled` |
| S9-T02 | Geçersiz durum geçişi | Reddedilir |
| S9-T03 | Model digest uyuşmazlığı | Challenge oluşur |
| S9-T04 | Latency sınırı aşımı | Politika uyarınca timeout/challenge |
| S9-T05 | Miner yarıda iptal | Session açık kalmaz |
| S9-T06 | Validator örneği eşleşiyor | Settled |
| S9-T07 | Validator örneği eşleşmiyor | Full re-run mock |
| S9-T08 | Simülasyon çıktısı | Her alanda `simulated: true` |
| S9-T09 | Aynı seed ve fixture | Aynı olay günlüğü |
| S9-T10 | Gerçek token/stake çağrısı | Kod yolunda bulunmaz |

**Çıkış kriterleri:**

- Her durum geçişi bir olay kaydı üretir.
- Simüle edilen ücret veya slashing gerçek FLOP değeri gibi gösterilmez.
- UI ve README bunun resmî protokol implementasyonu olmadığını söyler.
- Durum makinesi testlerinde bütün geçişler kapsanır.

**Önerilen sürüm:** `v0.8.0`

---

### Aşama 10 — Paketleme, güvenlik sertleştirme ve release candidate

**Hedef:** Geliştirici makinesi dışında kurulabilen, güncellenebilen ve güvenle yayımlanabilen bir sürüm hazırlamak.

**Teslimatlar:**

- Python wheel/sdist
- Windows kurulum ve kaldırma doğrulaması
- Linux kurulum ve kaldırma doğrulaması
- Kilitli bağımlılıklar
- SBOM
- Release checksum
- Güvenlik taraması
- Lisans uyumluluk raporu
- Performans regresyon testleri
- Migration ve schema compatibility testleri
- Kullanıcı dokümantasyonu

**Testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S10-T01 | Temiz Windows sandbox kurulumu | Başarılı |
| S10-T02 | Temiz Ubuntu sandbox kurulumu | Başarılı |
| S10-T03 | Kaldırma | Kullanıcı raporları silinmez |
| S10-T04 | Bozuk config | Güvenli varsayılana döner veya açık hata |
| S10-T05 | Eski v1 raporu yeni sürümde açma | Uyumlu veya açık migration mesajı |
| S10-T06 | Dependency audit | Kritik açık yok |
| S10-T07 | Secret scan | Bulgu yok |
| S10-T08 | Checksum doğrulama | Yayın artifact'ları eşleşir |
| S10-T09 | Offline probe/report | İnternetsiz çalışır |

**Çıkış kriterleri:**

- `test-all`, `lint`, `typecheck` ve `build` yeşildir.
- Kritik/yüksek güvenlik açığı yoktur.
- Temiz iki işletim sisteminde kurulum belgeleri doğrulanmıştır.
- Release artifact'ları checksum ve SBOM içerir.

**Önerilen sürüm:** `v0.9.0-rc.1`

---

### Aşama 11 — `v1.0.0` genel yayın

**Hedef:** İyi belgelenmiş, güvenli varsayılanlara sahip ve bağımsız kullanılabilir ilk kararlı sürümü yayımlamak.

**Teslimatlar:**

- `v1.0.0` GitHub release
- Demo GIF/video
- Örnek miner, validator ve agent raporları
- İngilizce README ve Türkçe README
- Architecture, privacy, security, methodology, limitations belgeleri
- Public roadmap ve issue template'leri
- Signed contribution proof
- Canlı fakat yalnız örnek fixture kullanan demo — yayımlanacaksa

**Yayın öncesi kabul testleri:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S11-T01 | Temiz Windows makinede kurulum | Belgedeki adımlarla başarılı |
| S11-T02 | Probe ve miner check | Rapor şemaya uygun üretilir |
| S11-T03 | Mock benchmark | Deterministik sonuç üretir |
| S11-T04 | Public report preview | Gizli alan görülmez |
| S11-T05 | HTML export | İnternetsiz açılır |
| S11-T06 | Receipt prepare/verify | Doğru raporda başarılı |
| S11-T07 | PoUI normal ve challenge senaryosu | İki akış da beklenen sonuca ulaşır |
| S11-T08 | Kaldırma | Kullanıcı raporları korunur |
| S11-T09 | Aynı uçtan uca akışın Ubuntu'da tekrarı | Windows ile aynı şema ve davranış |

**Çıkış kriterleri:**

- Release checklist'in tüm maddeleri iki kişi tarafından kontrol edilmiştir.
- README'deki bütün komutlar temiz ortamda çalıştırılmıştır.
- Link checker başarısız bağlantı bulmamıştır.
- Güvenlik bildirim adresi ve yanıt politikası yayımlanmıştır.
- Ürün hiçbir yerde resmî FLOP aracı veya eligibility checker olarak tanıtılmamıştır.

**Sürüm:** `v1.0.0`

---

### Aşama 12 — Resmî testnet adaptörü (blokeli gelecek aşama)

**Başlangıç koşulu:** FLOP Labs tarafından kamuya açık, sürümlü testnet istemcisi veya API sözleşmesi yayımlanmış olmalıdır.

**Bu koşul sağlanmadan yapılmayacaklar:**

- Endpoint tahmini
- Uydurma session transaction alanları
- Faucet otomasyonu
- Token bakiye veya reward tahmini
- Gerçek testnet desteği varmış gibi demo

**Koşul sağlandıktan sonraki teslimatlar:**

- Resmî dokümana bağlı testnet adapter'ı
- API sürüm tespiti
- Read-only health check
- Dry-run session request
- Kullanıcı onaylı gerçek request
- Receipt içe aktarma
- Rate-limit ve retry politikası
- Test token ve mainnet ayrımı

**Zorunlu testler:**

| Kimlik | Test | Beklenen sonuç |
|---|---|---|
| S12-T01 | Resmî testnet fixture/vektörleri | Resmî beklenen sonuçlarla eşleşir |
| S12-T02 | Yanlış chain/network kimliği | İstek gönderilmeden reddedilir |
| S12-T03 | Mainnet'e varsayılan gönderim | Engellenir |
| S12-T04 | Timeout sonrası davranış | Kör retry yapılmaz; sonuç belirsiz işaretlenir |
| S12-T05 | Duplicate session | İkinci gönderim engellenir veya güvenle idempotent olur |
| S12-T06 | Faucet/write işlemi | İnsan onayı olmadan başlamaz |
| S12-T07 | Adapter devre dışı | Çekirdek FlopBench çalışmaya devam eder |
| S12-T08 | API sürümü desteklenmiyor | Açık uyumsuzluk mesajı, write yok |
| S12-T09 | Test token/mainnet token ayrımı | Ağ ve varlıklar arayüzde karışmaz |

**Çıkış kriterleri:**

- Adapter yalnızca yayımlanmış resmî sözleşmeye dayanır ve kaynak sürümünü kaydeder.
- Resmî test vektörleri ile sözleşme testleri eksiksiz geçer.
- Testnet yazma işlemlerinin tamamı açık kullanıcı onayı ve ağ kimliği gösterir.
- Adapter başarısız veya kullanılamazken probe, benchmark, rapor ve simülatör çalışır.
- Mainnet desteği ayrı bir güvenlik incelemesi yapılmadan etkinleştirilmez.

**Önerilen sürüm:** Resmî testnet sürümüne göre `v1.x.0`

## 16. Aşamalar arası bağımlılık

```text
Aşama 0  Depo ve kalite
   ↓
Aşama 1  Şema ve profiller
   ↓
Aşama 2  Donanım probe
   ↓
Aşama 3  Readiness motoru
   ├──────────────→ Aşama 4  Aktif validator testleri
   └──────────────→ Aşama 5  Inference benchmark
                         ↓
                    Aşama 6  Raporlama
                         ↓
                    Aşama 7  Web dashboard
                         ↓
                    Aşama 8  DID receipt
                         ↓
                    Aşama 9  PoUI simulator
                         ↓
                    Aşama 10 RC
                         ↓
                    Aşama 11 v1.0.0
                         ↓
                    Aşama 12 Resmî testnet adapter'ı
```

## 17. Gereksinim–test izlenebilirlik matrisi

| Gereksinim | Ana testler |
|---|---|
| Varsayılan yerel çalışma | S2-T07, S7-T01, S10-T09 |
| FLOP profil sürümleme | S1-T01–S1-T06, S3-T08 |
| GPU'suz çalışma | S2-T03, S5-T01 |
| Miner readiness | S3-T01–S3-T04 |
| Validator readiness | S3-T05–S3-T07, S4 testleri |
| Tekrarlanabilir benchmark | S5-T01, S5-T07, S5-T08 |
| Gizlilik/redaksiyon | S2-T06, S6-T01, S7-T08 |
| XSS ve zararlı girdi koruması | S6-T05, S7-T06 |
| DID receipt doğrulama | S8-T01–S8-T09 |
| PoUI simülasyon sınırı | S9-T08, S9-T10 |
| Platformlar arası paketleme | S10-T01, S10-T02 |
| Testnet belirsizliği yönetimi | Aşama 12 başlangıç koşulu |

## 18. Definition of Done

Bir özellik yalnızca aşağıdaki koşulların tamamı sağlandığında bitmiş sayılır:

- Gereksinimi ve kapsam dışı davranışı yazılmıştır.
- Birim testleri eklenmiştir.
- En az bir başarısızlık/edge-case testi vardır.
- Gerekliyse JSON Schema veya tipler güncellenmiştir.
- İngilizce kullanıcı dokümanı güncellenmiştir.
- Kullanıcı davranışı değişiyorsa Türkçe belge de güncellenmiştir.
- Güvenlik ve gizlilik etkisi değerlendirilmiştir.
- Loglarda hassas veri bulunmadığı kontrol edilmiştir.
- Windows ve Ubuntu CI başarılıdır.
- Changelog kaydı eklenmiştir.
- Mock/fixture olmadan zor doğrulanan davranış için manuel test kaydı vardır.
- `draft`, `estimated` veya `simulated` veri doğru etiketlenmiştir.

## 19. Risk kaydı

| Risk | Olasılık | Etki | Önlem |
|---|---:|---:|---|
| FLOP parametrelerinin değişmesi | Yüksek | Yüksek | Sürümlü profil, kaynak URL ve hash |
| Testnet'in gecikmesi | Orta/Yüksek | Orta | Testnetten bağımsız benchmark ve simulator |
| Resmî API'nin tasarımdan farklı olması | Yüksek | Yüksek | Adapter izolasyonu, çekirdekte uydurma API yok |
| GPU sağlayıcı farklılıkları | Yüksek | Orta | Provider eklenti modeli ve fixture seti |
| Yanlış performans karşılaştırması | Orta | Yüksek | Workload/model/runtime uyumluluk kontrolü |
| Gizli sistem bilgisinin sızması | Orta | Çok yüksek | Redaksiyon profilleri ve secret leak testleri |
| DID anahtarının yanlış kullanımı | Düşük/Orta | Çok yüksek | Harici signer, interaktif onay, web upload yasağı |
| Projenin resmî sanılması | Orta | Yüksek | Görünür disclaimer ve marka sınırı |
| Airdrop aracı olarak yanlış pazarlanması | Orta | Yüksek | Eligibility/reward özelliklerini kapsam dışı tutmak |
| Benchmark sırasında sistemin aşırı ısınması | Orta | Yüksek | Süre sınırı, sıcaklık kesme noktası, açık onay |
| Dış endpoint üzerinden SSRF | Orta | Yüksek | Allowlist, redirect yasağı ve ağ testleri |
| Bağımlılık tedarik zinciri riski | Orta | Yüksek | Kilit dosyaları, SBOM, audit ve minimum bağımlılık |

## 20. Marka ve iletişim kuralları

### 20.1 Kullanılacak ifade

> FlopBench is an independent, community-built readiness and benchmarking tool inspired by the public FLOP Network draft.

### 20.2 Kullanılmayacak ifadeler

- Official FLOP benchmark
- Official FLOP eligibility checker
- Guaranteed airdrop tool
- FLOP validator client
- FLOP miner software
- Proof that the user will receive tokens

### 20.3 Görsel kimlik

Tasarım FLOP'un compute ve agent ekonomisi fikrini yansıtabilir; ancak resmî logo veya marka unsurları izin verilmeden ürünün kendi markasıymış gibi kullanılmamalıdır. FlopBench ayrı bir kelime işareti ve ayrı uygulama simgesi kullanmalıdır.

Önerilen görsel dil:

- Koyu teknik zemin
- Compute blokları ve inference akışları
- Agent → Miner → Validator bağlantı çizgileri
- Latency pulse ve GPU grid görselleri
- Erişilebilir durum renkleri; yalnız renge bağlı anlam yok
- “Airdrop dashboard” görünümünden kaçınma

## 21. Dokümantasyon planı

| Belge | İçerik |
|---|---|
| `README.md` | İngilizce ürün tanımı, hızlı başlangıç, disclaimer |
| `README.tr.md` | Türkçe kullanım ve güvenlik özeti |
| `architecture.md` | Bileşenler ve güven sınırları |
| `protocol-mapping.md` | Hangi alan hangi resmî kaynaktan geliyor |
| `benchmark-methodology.md` | Ölçüm ve karşılaştırma yöntemi |
| `security-model.md` | Anahtar, ağ ve girdi tehditleri |
| `privacy.md` | Toplanan/toplanmayan alanlar ve redaksiyon |
| `limitations.md` | Resmî olmayan ve simüle edilen bölümler |
| `schema-versioning.md` | Rapor/profil migration kuralları |
| `adapter-development.md` | Yeni runtime/testnet adaptörü ekleme |

## 22. İlk issue/backlog listesi

Repo oluşturulduğunda ilk işler şu sırayla issue haline getirilmelidir:

1. Repository governance and disclaimer
2. Python project skeleton and quality tooling
3. Web project skeleton and quality tooling
4. Windows/Ubuntu CI matrix
5. FLOP profile schema
6. Teaser v0.1 source profile
7. Readiness report schema
8. Benchmark report schema
9. Hardware provider interface
10. Fixture-based provider
11. Windows basic probe
12. Linux basic probe
13. NVIDIA NVML provider
14. Public redaction policy
15. Miner readiness rules
16. Validator readiness rules
17. Mock inference adapter
18. Benchmark statistics engine
19. Canonical report export
20. Web readiness dashboard
21. Receipt canonicalization and offline verification
22. PoUI state machine
23. Packaging and release pipeline

Her issue ilgili aşama ve test kimlikleriyle etiketlenmelidir. Örnek: `stage:2`, `area:probe`, `tests:S2-T01,S2-T02`.

## 23. Release kontrol listesi

- [ ] Sürüm numarası SemVer ile uyumlu
- [ ] Changelog güncel
- [ ] Bütün CI job'ları yeşil
- [ ] Windows temiz kurulum testi tamam
- [ ] Ubuntu temiz kurulum testi tamam
- [ ] README komutları yeniden çalıştırıldı
- [ ] Public fixture'larda gizli alan yok
- [ ] Dependency audit kritik bulgu vermiyor
- [ ] Secret scan temiz
- [ ] SBOM üretildi
- [ ] SHA-256 checksum üretildi
- [ ] JSON Schema dosyaları artifact'a dahil
- [ ] Kullanılan FLOP profilinin kaynağı ve durumu güncel
- [ ] `draft/provisional/simulated` etiketleri görünür
- [ ] Güvenlik ve gizlilik belgeleri güncel
- [ ] Demo gerçek token, claim veya eligibility iddiası içermiyor
- [ ] Git tag imzalandı veya doğrulanabilir release kaydı oluşturuldu

## 24. Projenin başarı tanımı

FlopBench aşağıdaki durumda başarılı sayılır:

1. Testnet henüz açılmamış olsa bile kullanıcıya gerçek ve tekrar üretilebilir donanım/inference bilgisi sağlar.
2. Miner, validator ve agent rollerini tek üründe fakat birbirine karıştırmadan temsil eder.
3. FLOP teaser'daki geçici parametreleri kaynak ve sürüm bilgisiyle gösterir.
4. Hiçbir private key, wallet bilgisi veya kişisel cihaz tanımlayıcısını varsayılan olarak toplamaz.
5. GPU olmayan CI üzerinde kapsamlı biçimde test edilebilir.
6. Resmî testnet API'si yayımlandığında çekirdek mimariyi bozmadan adapter eklenebilir.
7. Kullanıcılar raporları karşılaştırırken hangi metriklerin ölçülmüş, tahmin edilmiş veya simüle edilmiş olduğunu anlayabilir.
8. Repo çalışan kod, testler, güvenlik modeli ve tekrarlanabilir örneklerle ciddi bir açık kaynak mühendislik ürünü görünümüne ulaşır.

## 25. Uygulamaya başlama kararı

Bu künye onaylandıktan sonra uygulama **Aşama 0** ile başlamalıdır. İlk kod hedefi GPU benchmark'ı değil; depo iskeleti, kalite kapıları, kaynak profili ve veri şemaları olmalıdır. Bu sıra, ileride sonuç formatını veya güvenlik modelini yeniden yazma riskini azaltır.

İlk geliştirme sırasında aşağıdaki kararlar ayrıca netleştirilmelidir:

- GitHub organizasyonu ve kesin repo adı
- Apache-2.0 lisansının kesin onayı
- Python ve Node kesin sürümleri
- İlk desteklenecek yerel inference runtime'ı
- İlk gerçek donanım test cihazları
- Web uygulamasının yalnız yerel mi yoksa fixture tabanlı public demo da mı sunacağı

Bu kararlar Aşama 0 sonunda birer Architecture Decision Record olarak kaydedilmelidir.
