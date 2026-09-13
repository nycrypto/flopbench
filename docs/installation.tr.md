# Kurulum ve kaldırma

FlopBench Aşama 10, 64 bit Windows ve Ubuntu üzerinde Python 3.14.6'yı hedefler.
Dashboard ve kaynak profilleri wheel içine dahildir; kurulu paketi çalıştırmak
için Node.js gerekmez.

## Sürüm adayını doğrulama ve kurma

Aynı sürüm adayı paketindeki bütün dosyaları indirin. Ubuntu'da kurulumdan önce
o dizindeki hash'leri doğrulayın:

```bash
sha256sum --check SHA256SUMS
python3.14 -m pip install flopbench-0.9.0rc1-py3-none-any.whl
python3.14 -m flopbench.release verify --artifact-dir .
flopbench --version
flopbench probe --fixture cpu-only --privacy private
flopbench serve
```

Windows'ta wheel'i kurmadan önce `Get-FileHash -Algorithm SHA256 <artifact>`
çıktısını `SHA256SUMS` satırıyla karşılaştırın; kurulumdan sonra paketli tam-küme
doğrulayıcısını çalıştırın. Bütünleşik servis yalnız `127.0.0.1` adresine
bağlanır; kurulum dashboard'u internete açmaz.

`SHA256SUMS`; wheel, sdist, CycloneDX JSON SBOM ve deterministik lisans raporunun
tamamını kapsar. Doğrulama eksik, fazla, bozuk, sembolik bağlantı olan veya
değiştirilmiş artifact'i reddeder.

## Kaldırma ve kullanıcı verisi

```powershell
python -m pip uninstall flopbench
```

Kaldırma yalnız pakete ait dosyaları siler. Kullanıcının seçtiği dizine aktarılan
raporlar kullanıcıya aittir ve korunur. Önemli raporları normal şekilde
yedekleyin; FlopBench bir yedekleme hizmeti değildir.

## Çevrimdışı çalışma

Bağımlılıklar ve wheel kurulduktan sonra fixture/canlı probe ile yerel rapor
aktarımı ağ olmadan çalışır. Ollama ve OpenAI-compatible benchmark adaptörleri
açıkça yapılandırılan endpoint'i gerektirir. `probe` ve `report export` hiçbir
adaptöre bağlanmaz.

## Yapılandırma uyumluluğu

`flopbench serve --config config.json`, isteğe bağlı yerel uyumluluk
yapılandırmasını başlangıçtan önce doğrular. Yapılandırma yoksa gizlilik
öncelikli varsayılanlar kullanılır. Dosya en fazla 64 KiB boyutunda, normal bir
UTF-8 JSON dosyası olmalı ve
`flopbench-config-v1` ile eşleşmelidir; bilinmeyen veya uzaktan bind alanları açık
hata üretir. Mevcut `flopbench-benchmark-report-v1` raporları kaynak dosya yeniden
yazılmadan okunmaya devam eder.
