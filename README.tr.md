# FlopBench

> Gelecekteki FLOP miner, validator ve AI agent katılımcıları için yerel öncelikli hazırlık, benchmark ve proof-of-inference çalışma alanı.

FlopBench, kamuya açık FLOP Network taslağından ilham alan **bağımsız bir topluluk projesidir**. FLOP Labs veya Flop Foundation'ın resmî ürünü, miner/validator istemcisi, eligibility checker, claim aracı ya da ödül garantisi değildir.

## Proje durumu

FlopBench Aşama 8'i (`v0.7.0`) tamamladı. Katı veri sözleşmeleri, pasif donanım tespiti, açıklanabilir readiness kontrolleri, onay kapılı sınırlı sağlık testleri, inference benchmark'ları, gizlilik duyarlı raporlar, haricî imzalı DID receipt'leri ve güvenli iki dilli yerel dashboard mevcuttur. Aşama 9 PoUI simülasyonu geliştirilmektedir. [Dashboard belgesine](./docs/dashboard.tr.md), [receipt güvenlik modeline](./docs/receipt-security.tr.md) ve [Aşama 8 kabul kaydına](./docs/stage-8-acceptance.md) bakın.

Normatif proje belgesi [`flopbench künye.md`](./flopbench%20k%C3%BCnye.md) dosyasıdır. FLOP'a ait geçici parametreler kod içine dağıtılmayacak; sürümlü ve kaynaklı profil dosyalarında tutulacaktır.

## Gereksinimler

- Python 3.14.6
- Node.js 24.17.0
- pnpm 11.19.0
- Git

Docker ve GNU Make isteğe bağlıdır. Bütün kalite görevleri Python/Nox, pnpm ve PowerShell üzerinden çalıştırılabilir.

Benchmark davranışı, metrik tanımları ve endpoint güvenlik kuralları [`docs/benchmarks.md`](./docs/benchmarks.md) içinde belgelenmiştir.

## Geliştirici kurulumu

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements/dev.txt
pnpm install --frozen-lockfile
```

Linux üzerinde `.venv\Scripts\python` yerine `.venv/bin/python` kullanılır.

## Yerel dashboard

Dashboard'u derleyip bütünleşik yerel API ile `http://127.0.0.1:4173` adresinde başlatmak için:

```powershell
pnpm --filter @flopbench/web build
flopbench serve
```

Servis yalnızca açık loopback adreslerini kabul eder; genel internetten veya ağdaki başka cihazlardan erişilemez. Arayüz Türkçe ve İngilizce çalışır, ilk ziyarette tarayıcı dilini kullanır ve açık dil/tema tercihini yalnız tarayıcıda saklar.

## Pasif donanım probe'u

Ağ erişimi olmadan private veya redakte edilmiş public probe çalıştırmak için:

```powershell
flopbench probe --format json --privacy private
flopbench probe --format json --privacy public
flopbench probe --fixture fixtures/hardware/cpu-only.json --format json
```

Public çıktı hostname, kullanıcı adı, IP adresi, yerel yol, OS build bilgisi,
GPU seri numarası ve PCI bus kimliğini kaldırır. Ayrıntılar için
[`docs/privacy.md`](./docs/privacy.md) belgesine bakın.

## Readiness kontrolleri

Canlı donanımı veya deterministik bir fixture'ı sürümlü kaynak profiliyle
karşılaştırmak için:

```powershell
flopbench check miner
flopbench check validator
flopbench check miner --fixture fixtures/hardware/linux-nvidia-16gb.json --format json
```

Kaynak profil kararları ile FlopBench topluluk sağlık kontrolleri ayrı alan ve
terminal bölümlerinde tutulur. Her karar kararlı bir reason code taşır;
`unknown` ve `unsupported` donanım yetersizliğine çevrilmez. Birlikte gelen
profil görünür biçimde `draft` olarak işaretlenir. Ayrıntılar için
[`docs/readiness.md`](./docs/readiness.md) belgesine bakın.

## Aktif validator sağlık testleri

Gösterilen disk limitini, ağ hedefini ve gönderilecek veriyi inceleyip planı
terminalden veya açık bayrakla onaylayın:

```powershell
flopbench doctor validator
flopbench doctor validator --approve --disk-bytes 1048576 --format json
flopbench doctor validator --network-target 127.0.0.1:443 --ntp-server 127.0.0.1
```

Hedef açıkça verilmedikçe ağ veya saat testi çalışmaz. Disk dosyaları yalnızca
izole geçici dizinde tutulur; başarı, hata, zaman aşımı veya iptal sonrasında
silinir. Ayrıntılar için [`docs/active-tests.md`](./docs/active-tests.md)
belgesine bakın.

## Haricî imzalı receipt'ler

Mevcut bir Ed25519 DID için kesin JCS baytlarını hazırlayın, FlopBench dışında
çalışan bir araçla imzalayın, sonra receipt'i oluşturup doğrulayın:

```powershell
flopbench receipt prepare report.json --did did:key:z6Mk... --output request.json
flopbench receipt create request.json --signature BASE64URL_SIGNATURE --output receipt.json
flopbench receipt verify report.json receipt.json
```

FlopBench private key, seed, PEM, anahtar dosyası veya parola kabul etmez.
Geçerli receipt yalnız DID anahtarının kullanıldığını kanıtlar. Ayrıntılar için
[receipt güvenlik modeline](./docs/receipt-security.tr.md) bakın.

## Kalite kapıları

```powershell
.\scripts\tasks.ps1 lint
.\scripts\tasks.ps1 typecheck
.\scripts\tasks.ps1 test-unit
.\scripts\tasks.ps1 test-contract
.\scripts\tasks.ps1 test-web
.\scripts\tasks.ps1 test-all
.\scripts\tasks.ps1 build
```

Make bulunan ortamlarda eşdeğer `make lint`, `make typecheck`, `make test-all` ve `make build` komutları da kullanılabilir.

## Gizlilik ve ağ varsayılanları

FlopBench yerel önceliklidir. Gelecekteki probe ve rapor komutları varsayılan olarak sistem verisini ağ üzerinden göndermeyecektir. Özel anahtarlar, cüzdan seed'leri, hostname, kullanıcı adı, IP/MAC adresleri, seri numaraları ve yerel yollar korunan veridir; varsayılan public rapora alınmaz.

## Lisans

Apache License 2.0 ile lisanslanmıştır. Ayrıntılar için [LICENSE](./LICENSE) dosyasına bakın.
