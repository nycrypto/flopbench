# Receipt imzalama güvenlik modeli

FlopBench receipt'leri, rapor dışa aktarımının canonical SHA-256 özetine offline
doğrulanabilir bir Ed25519 kanıtı ekler. Kanıt yalnız receipt içindeki `did:key`
ile eşleşen private key'in kullanıldığını gösterir. Kişi kimliği, donanım
sahipliği, raporun doğruluğu, FLOP uygunluğu, ödül veya güvenilir zaman kanıtı
değildir.

## Güven sınırı

FlopBench bir signer değildir ve anahtar yönetimi özelliği içermez. Private key
veya anahtar parolası üretmez, içe aktarmaz, yükletmez, okumaz, saklamaz, loglamaz
ve almaz. Kullanıcı mevcut DID'ini ve signer aracını bütün FlopBench
süreçlerinin dışında tutar.

Üç adımlı sözleşme şöyledir:

1. `flopbench receipt prepare REPORT --did DID --output request.json` rapor
   dışa aktarımını ve DID'i doğrular, sonra sınırlı bir imza isteği üretir.
2. Haricî Ed25519 signer `payload_base64url` alanını çözer, tam olarak bu
   baytları imzalar ve canonical, padding içermeyen tek base64url imza döndürür.
3. `flopbench receipt create request.json --signature SIGNATURE --output
   receipt.json` dosyayı yazmadan önce imzayı doğrular. Daha sonra `flopbench
   receipt verify REPORT receipt.json` yalnız public veri kullanır.

`--signature` verilmezse işlem iptal edilir ve receipt yazılmaz. `--password`,
`--private-key` ve `--key-file` seçenekleri yoktur ve reddedilir.

## İmzalanan baytlar

Haricî signer, `flopbench-receipt-signing-payload-v1` nesnesinin RFC 8785/JCS
canonical UTF-8 baytlarını imzalar. Payload şu alanları birbirine bağlar:

- rapor şeması;
- rapor dışa aktarımındaki canonical `document` nesnesinin SHA-256 özeti;
- mevcut `did:key` tanımlayıcısı;
- `jcs-rfc8785` ve `Ed25519` algoritma tanımları;
- yerel olarak beyan edilen UTC `signed_at` değeri.

İmza isteği aynı baytları canonical, padding içermeyen base64url biçiminde ve
insan/araç karşılaştırması için SHA-256 özetiyle taşır. Bağlı alanlardan herhangi
biri değişirse imzalanan baytlar da değişir.

## Kodlama kuralları

- DID yöntemi yalnız `did:key`.
- Multibase yalnız `z` base58btc.
- Multicodec: `0xed 0x01` varint baytları (`ed25519-pub`) ve tam 32 public-key
  baytı.
- İmza: tam 64 bayt ve tam 86 karakter canonical, padding içermeyen base64url.
- Çözümleme ve doğrulama offline yapılır; registry veya DID resolver çağrılmaz.

Bu tercihler Technocore'un Ed25519 DID biçimiyle uyumludur. Technocore oda
nonce'u, sıra numarası, sunucu zamanı ve mesajlara özel imza dizileri FlopBench
receipt'inin parçası değildir.

## Dosya ve hata yönetimi

İmza isteği ve receipt, bilinmeyen alanları reddeden katı JSON nesneleridir.
Girdiler 64 KiB ile sınırlıdır; sembolik bağlantılar ve normal olmayan dosyalar
reddedilir; mevcut çıktı dosyalarının üzerine yazılmaz ve bozuk girdi secret
değerleri yankılamadan kararlı hata döndürür. Rapor dışa aktarımları mevcut 8 MiB
sınırını ve iç JCS digest kontrolünü korur.

Bağımsız Ed25519 doğrulama kaynağı olarak RFC 8032 bölüm 7.1 vektörleri
kullanılır. Dashboard kasıtlı olarak private-key yükleme alanı içermez.

## Kaynaklar

- [RFC 8032: Edwards-Curve Digital Signature Algorithm](https://www.rfc-editor.org/rfc/rfc8032)
- [W3C did:key yöntemi](https://w3c-ccg.github.io/did-key-spec/)
- [Technocore kimlik doğrulama ve imza modeli](https://technocore.chat/auth.md)
