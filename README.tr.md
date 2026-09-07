# FlopBench

> Gelecekteki FLOP miner, validator ve AI agent katılımcıları için yerel öncelikli hazırlık, benchmark ve proof-of-inference çalışma alanı.

FlopBench, kamuya açık FLOP Network taslağından ilham alan **bağımsız bir topluluk projesidir**. FLOP Labs veya Flop Foundation'ın resmî ürünü, miner/validator istemcisi, eligibility checker, claim aracı ya da ödül garantisi değildir.

## Proje durumu

FlopBench Aşama 5'in (`v0.4.0`) inference benchmark kapanışındadır. Katı veri sözleşmeleri, pasif donanım tespiti, açıklanabilir readiness kontrolleri, onay kapılı sınırlı sağlık testleri ve mock/Ollama/OpenAI-compatible benchmark adapter'ları mevcuttur. Aşama 6 raporlaması, Aşama 7 işlevsel dashboard'u, rapor imzalama ve PoUI simülasyonu henüz uygulanmamıştır. Doğrulanmış kapsam ve kapı durumu için [Aşama 5 kabul kaydına](./docs/stage-5-acceptance.md) bakın.

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

Dashboard hâlâ yalnızca yerelde çalışan temel bir kabuktur; işlevsel dashboard Aşama 7'de planlanmıştır. Mevcut kabuğu derlemek ve `http://127.0.0.1:4173` adresinde açmak için:

```powershell
pnpm --filter @flopbench/web build
pnpm --filter @flopbench/web preview
```

Önizleme sunucusu yalnızca loopback adresine bağlanır; genel internetten veya ağdaki başka cihazlardan erişilemez.

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
