# Folder Snapshot

Bir klasördeki dosyaların yollarını ve SHA-256 özetlerini JSON olarak kaydeder. Yedek almadan önce ve sonra iki kayıt oluşturup hangi dosyaların eklendiğini, kaldırıldığını veya değiştiğini görebilirsin. Aynı içeriğe sahip klasörler farklı konumlarda da karşılaştırılabilir.

## Kullanım

Python 3.12 veya üzeri yeterli. Komutları depo kökünde çalıştır.

```powershell
python folder_snapshot.py create ./belgeler once.json --exclude '.git' --exclude '*.tmp'
python folder_snapshot.py create ./belgeler sonra.json --exclude '.git' --exclude '*.tmp'
python folder_snapshot.py diff once.json sonra.json
python folder_snapshot.py diff once.json sonra.json --json
```

`--exclude` seçeneği birden çok kez verilebilir. Desenler, köke göre `/` ayraçlı yolla eşleşir. Bir klasör yolu eşleşirse altındaki dosyalar da atlanır.

Manifestleri taranan klasörün dışında sakla veya desenle hariç tut. Araç yeni kaydı ancak yazma tamamlandığında hedef adında görünür kılar ve var olan manifestin üzerine yazmaz. POSIX sistemlerde hedef dosya sistemi sabit bağlantıları desteklemelidir. Sembolik bağlantılar ve Windows birleşim noktaları atlanır. Kayıt dosya içeriğini ve yolları kapsar. Boş klasör, zaman damgası ve izin değişiklikleri karşılaştırmaya girmez.

`diff` çıkış kodları otomasyonlarda kullanılabilir. `0` fark olmadığını, `1` dosya farkı bulunduğunu, `2` işlem hatasını gösterir.

## Testler

```powershell
python -m unittest discover -v
```
