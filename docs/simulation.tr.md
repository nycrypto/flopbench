# PoUI eğitim simülasyonu

FlopBench Aşama 9, inference session akışını deterministik ve yerel bir eğitim
çalışması olarak modeller. Resmî FLOP protokolü uygulaması değildir. Ağ, cüzdan,
testnet, token, stake, ödül veya gerçek slashing işlemi yapmaz.

## Senaryo çalıştırma

```powershell
flopbench simulate run --scenario success --seed 9
flopbench simulate run --scenario validator-mismatch --seed 9 --output simulation.json
```

Senaryolar: `success`, `wrong-model`, `high-latency`, `canned-answer`, `timeout`,
`miner-cancel`, `validator-match` ve `validator-mismatch`. Aynı doğrulanmış istek
ve seed, aynı canonical olay günlüğünü bayt düzeyinde tekrar üretir.

## Yaşam döngüsü

Normal akış:

```text
created -> offered -> accepted -> running -> submitted -> validating -> settled
```

Politika ve doğrulama yolları `challenged`, `rejected`, `timed_out` veya
`cancelled` durumlarında kapanabilir. Oluşturma ve her geçiş; aktör, önceki durum,
sonraki durum, kod, deterministik kimlik ve UTC simülasyon zamanı içeren kararlı
bir olay üretir. Geçersiz geçişler reddedilir.

Agent isteği oluşturup kabul eder, miner sahte inference sonucunu sunar ve
validator örnekler. Validator uyuşmazlığı açıkça bir mock full re-run çalıştırır.
Yanlış model, yüksek gecikme ve canned-answer yolları reddedilmeden önce challenge
açar.

## Simülasyon sınırı

Simülasyon çıktısındaki her nesne `"simulated": true` içerir. Muhasebe yalnız
`mock-credit`, compute ise yalnız `mock-compute-unit` ile gösterilir. Bunlar eğitim
sayaçlarıdır; FLOP, itibari para, token, stake, ödül, uygunluk veya ekonomik tahmin
değildir.

Yerel dashboard aynı senaryoları kısa bir olay zaman çizgisiyle gösterir. Resmî
olmayan simülasyon uyarısı çalıştırma düğmesinden önce daima görünür.
