# FlopBench

> Gelecekteki FLOP miner, validator ve AI agent katılımcıları için yerel öncelikli hazırlık, benchmark ve proof-of-inference çalışma alanı.

FlopBench, kamuya açık FLOP Network taslağından ilham alan **bağımsız bir topluluk projesidir**. FLOP Labs veya Flop Foundation'ın resmî ürünü, miner/validator istemcisi, eligibility checker, claim aracı ya da ödül garantisi değildir.

## Proje durumu

FlopBench şu anda Aşama 0 (`v0.0.1` geliştirme) durumundadır: depo iskeleti ve kalite kapıları. Donanım taraması, readiness kontrolleri, benchmark, rapor imzalama ve PoUI simülasyonu henüz uygulanmamıştır.

Normatif proje belgesi [`flopbench künye.md`](./flopbench%20k%C3%BCnye.md) dosyasıdır. FLOP'a ait geçici parametreler kod içine dağıtılmayacak; sürümlü ve kaynaklı profil dosyalarında tutulacaktır.

## Gereksinimler

- Python 3.14.6
- Node.js 24.17.0
- pnpm 11.19.0
- Git

Docker ve GNU Make isteğe bağlıdır. Bütün kalite görevleri Python/Nox, pnpm ve PowerShell üzerinden çalıştırılabilir.

## Geliştirici kurulumu

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements/dev.txt
pnpm install --frozen-lockfile
```

Linux üzerinde `.venv\Scripts\python` yerine `.venv/bin/python` kullanılır.

## Yerel dashboard

Aşama 0 dashboard'u yalnızca yerelde çalışır. Derlemek ve `http://127.0.0.1:4173` adresinde açmak için:

```powershell
pnpm --filter @flopbench/web build
pnpm --filter @flopbench/web preview
```

Önizleme sunucusu yalnızca loopback adresine bağlanır; genel internetten veya ağdaki başka cihazlardan erişilemez.

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
