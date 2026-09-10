# Yerel dashboard

## Kapsam

Aşama 7 dashboard'u yerel readiness, deterministik mock benchmark ve public
rapor gizlilik önizlemesi için iki dilli bir çalışma yüzeyidir. İnternette
barındırılmaz ve resmî FLOP uygunluk skoru üretmez.

## Başlatma

Web dosyalarını derleyin ve bütünleşik loopback servisini başlatın:

```powershell
pnpm --filter @flopbench/web build
flopbench serve
```

`http://127.0.0.1:4173` adresini açın. Sunucu yalnızca açık loopback
adreslerini kabul eder. v1'de uzaktan bağlanma özelliği yoktur.

## Güvenlik sınırı

- Her sunucu sürecinde rastgele bir anahtar oluşturulur ve yalnızca aynı
  origin'deki dashboard belgesine eklenir.
- Health kontrolü dışındaki API istekleri bu anahtarı gerektirir.
- Host ve Origin doğrulaması DNS-rebinding ve siteler arası istek risklerini
  sınırlar.
- Yanıtlarda CSP, `no-store`, MIME sniffing koruması ve no-referrer politikası
  uygulanır.
- Fixture seçimi, kullanıcı tarafından verilen dosya yolları yerine sabit
  kimliklerle yapılır.
- Model adları ve rapor verileri HTML olarak değil metin olarak gösterilir.

## Davranış

Genel bakış, pasif public probe çalıştırır ve miner veya validator hazırlığını
birlikte gelen sürümlü profile göre değerlendirir. `unknown`, `skipped` ve
`unsupported` sonuçları `fail` sonucundan görsel olarak ayrı tutulur.

Dashboard açılışta veya tarayıcı yenilemesinde benchmark başlatmaz. Mock
benchmark yalnız kullanıcı düğmeyi etkinleştirdiğinde çalışır. Public rapor
önizlemesi, JCS özetinden önce paylaşım dışında bırakılan alan sınıflarını
gösterir.

Türkçe ve İngilizce eşit arayüz dilleridir. İlk ziyarette tarayıcı dili
kullanılır; açık dil ve açık/koyu tema tercihleri yalnızca tarayıcı yerel
depolamasında saklanır.

## Test

```powershell
pnpm --filter @flopbench/web test
pnpm --filter @flopbench/web build
pnpm --filter @flopbench/web e2e
```

E2E paketi Chromium kullanır ve temel WCAG 2.2 AA taraması içerir.
