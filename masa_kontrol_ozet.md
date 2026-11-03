# Masa Kontrol Projesi: Devir Özeti

> Bu dosya, önceki sohbette öğrenilen her şeyin özetidir. Yeni sohbete bu dosyayla birlikte **`abdullah.ino`** dosyasını da ekleyin. Yeni kod bu dosya temel alınarak yazılacak.

---

## 1. Sistem nedir?

İki motorlu (sol/sağ), WiFi'dan telefonla kontrol edilen elektrikli bir masa.

- Konum **süreye göre** hesaplanıyor. Motorlarda sensör yok. Hall sensör arandı ama bulunamadı ve kablolar mühürlendi.
- Tam hareket süresi: **13 saniye** (`MAX_POS = 13000` ms).
- 5 hafıza, sağ/sol ayrı kalibrasyon, "İKİSİ (Manuel)" kalibrasyon butonları ve konum sıfırlama var.
- Masa vidalı ve kapalı, kablolara erişilemiyor. **ESP dışarıda**, USB ile erişilebiliyor.
- Kullanıcı **yeni modül eklemek istemiyor**, mevcut donanımla devam edilecek.

## 2. Donanım

| Parça | Bilgi |
|---|---|
| Kontrol kartı | **ESP32-C3 Super Mini** |
| Motor sürücü | **2 × BTS7960 (43A)** |
| Motor gücü | **24V 15A 360W** adaptör (ayrı) |
| ESP gücü | **USB** (ayrı adaptör) |
| Priz | ESP ve motor adaptörü **aynı grup prizde** |
| Ağ | Ev WiFi'ı (bilgiler `abdullah.ino` içinde). Cihaz IP: **192.168.1.107** |

## 3. Pinler (fiziksel olarak doğrulandı)

ESP üzerinde, USB girişinden aşağı doğru sayılarak tek tek okundu:

| Sol sıra | 5V | G | 3V3 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|
| Durum | dolu | **BOŞ** | dolu | dolu | boş | boş | boş | boş |

| Sağ sıra | 5 | 6 | 7 | 8 | 9 | 10 | 20 | 21 |
|---|---|---|---|---|---|---|---|---|
| Durum | boş | dolu | dolu | boş | boş | dolu | boş | boş |

**Motor pinleri:**

| Motor | Yukarı | Aşağı | Güven |
|---|---|---|---|
| Sağ (MOTOR2) | **GPIO 4** | **GPIO 10** | Yüksek: tüm sürümlerde aynı |
| Sol (MOTOR1) | **GPIO 7** | **GPIO 6** | Pinler kesin, **yön tahmin** |

- `abdullah.ino`'da sol motor 5 (yukarı) / 6 (aşağı) idi. Cihazda 5 boş, 7 dolu. Sonuç: **5 → 7 taşınmış**, yön ataması korunmuş varsayılıyor.
- ⚠️ **Sol motorun yönü doğrulanmalı.** Yanlışsa masa tablası bükülür. Yeni kod yüklenince ilk test **sadece sol kalibrasyon butonuyla**, kısa süreli yapılmalı.

**Muhtemel diğer bağlantılar:**
- ESP **5V** → BTS7960'ların **VCC** girişi
- ESP **3V3** → BTS7960'ların **R_EN / L_EN** girişleri. Bu iyi bir düzen: ESP kapanırsa sürücüler de kapanır.

## 4. ⚠️ Bilinen sorunlar ve riskler

1. **GND bağlı değil.** ESP'nin G pini boş, iki adaptör arasında ortak toprak yok.
   - Sistem şu an çalışıyor. Büyük ihtimalle tesadüfi bir toprak yolu var.
   - Olası etkiler: komutların ara ara yanlış algılanması, motorun geç durması, ESP'nin resetlenmesi, dengesizliğe katkı.
   - Çözüm (kullanıcı şu an yapamıyor): ESP **G** pininden 24V adaptörün **V−** vidasına tek kablo. **V+ ya da FG'ye bağlanmamalı.**
   - **ESP bilgisayara takılırken 24V adaptörün fişi mutlaka çekilmeli.**
2. **Geçmiş olay:** ESP ile motorlar ayrı kaynaktayken ESP'nin elektriği gitti, motor durmadı ve yanacak kadar ısındı. Fiş çekilerek çözüldü. Şimdi ikisi aynı grup prizde.
3. **Motorlarda uç sınır anahtarı yok.** Motor dibe ya da tepeye dayanırsa zorlanıp ısınır. **"Uca dayanana kadar sür" tarzı kalibrasyon kesinlikle yapılmamalı.** Kullanıcı masayı dibe indirmemeye dikkat ediyor.
4. **Dengesizlik zamanla birikiyor.** Ağırlık ortada, sebep iki motorun hız farkı ve süreye dayalı hesap.
5. **Yumuşak kalkış/duruş yok.** Motora anında 255 PWM veriliyor, sarsıntı var.
6. **Watchdog yok.** Buton dışına kayınca, WiFi kopunca ya da telefon kilitlenince motor durmuyor (`onmouseup` gelmezse).
7. **Kalibrasyon hareketlerinin sınırı yok.**
8. `handleGotoMem` içinden `handleUp` çağrıldığı için aynı isteğe iki kez cevap gidiyor. Uç noktada `/up` ya da `/down` gelirse hiç cevap gönderilmiyor.

## 5. Kod dosyalarının geçmişi

| Sıra | Dosya | Özellik |
|---|---|---|
| 1 | `esp32c3_actuator.ino` (ilk) | Tek motor çifti (pin 2/8), **en alt / en üst ayarla** butonları, uçta motoru durdurmuyor (hata) |
| 2 | `esp32c3_actuator.ino` = `esp32masa.ino` | İki motor (sol 2/8, sağ 4/10), uçta duruyor, ama **flash'a her döngüde yazıyor** (hata) |
| 3 | **`abdullah.ino`** | Hafızalar, sağ/sol kalibrasyon, sol motor **5/6**, flash yazımı düzeltilmiş |
| 4 | **Cihazdaki "ANA" sürümü** | Kaynak kodu bulunamadı. `abdullah.ino` + "İKİSİ (Manuel)" butonları (`/c_up`, `/c_dn`) + sol motor **7/6** + birkaç yazı değişikliği |

**İlgisiz dosyalar:** `ana.ino` (T-Rex oyunu, ESP32-C6), `laser_test_nodemcu.ino` (IR kumanda + DHT11 "Tavas Pro Hub"), `Lazer_Metre_Cift_I2C.ino` (ESP8266 + VL53L1X), `sensortest.ino` (ADXL343 örneği), `vl53l0x_multi_extended.ino` (Adafruit örneği).

**Cihazdan doğrulanan:** `http://192.168.1.107/data` → `{"pos":0,"pct":0,"st":0,"cal":0}`. 4 alan, `abdullah.ino` ile aynı yapı.

**Cihazdaki sayfanın farkları** (`abdullah.ino`'ya göre):
- Başlık "Masa Kontrol (ANA)"
- "HAFIZA YÖNETİMİ", "Yukarı Gidiyor...", "Aşağı İniyor...", "DURDUR (ACİL)"
- Kalibrasyonda 3 sütun: SOL MOTOR / **İKİSİ (Manuel)** (`/c_up`, `/c_dn`) / SAĞ MOTOR
- `select` için stil, sıfırlama onay metni farklı

**Eski sürümlerde olup kaybolan iyi fikirler:** `onmouseleave` ile durma, `e.preventDefault()`, `WiFi.setTxPower(WIFI_POWER_8_5dBm)` (C3 Super Mini anten sorunu için), en alt / en üst ayarla butonları.

## 6. Yapılacaklar (sırayla)

### Adım 1: Yedek al (henüz yapılmadı)

1. ⚠️ **24V motor adaptörünün fişini çek.**
2. ESP'nin USB kablosunu bilgisayara tak.
3. *Aygıt Yöneticisi → Bağlantı Noktaları (COM ve LPT)* bölümünden COM numarasını bul (ör. COM5).
4. esptool Arduino IDE ile gelir: `%LOCALAPPDATA%\Arduino15\packages\esp32\tools\esptool_py\<sürüm>\esptool.exe`
5. O klasörde adres çubuğuna `cmd` yaz, sonra:
   ```
   esptool.exe --chip esp32c3 --port COM5 flash_id
   esptool.exe --chip esp32c3 --port COM5 --baud 460800 read_flash 0 0x400000 masa_yedek.bin
   ```
6. Dosya boyutu **4.194.304 bayt** olmalı. USB belleğe ya da Drive'a kopyala.
7. Bağlanamazsa: **BOOT** basılı tut → **RST**'ye bas, bırak → BOOT'u bırak → tekrar dene.
8. esptool 5.x'te komutlar `read-flash`, `write-flash`, `flash-id` şeklinde de yazılabilir.
9. Geri yükleme: `esptool.exe --chip esp32c3 --port COM5 write_flash 0 masa_yedek.bin`

### Adım 2: Yeni kodu yaz (`abdullah.ino` temel alınacak)

**Korunacaklar:**
- Pinler: sol **7/6**, sağ **4/10**
- Sayfa düzeni, 5 hafıza, kalibrasyon ve İKİSİ butonları, `/data` JSON yapısı
- Preferences namespace `"masa"`, anahtarlar `"pos"` ve `"mems"` (mevcut kayıtlı konum ve hafızalar korunsun)
- `MAX_POS = 13000` başlangıç değeri

**Eklenecekler:**
- **Watchdog:** Buton basılıyken tarayıcı komutu ~150 ms'de bir tekrarlasın. ESP ~400 ms komut almazsa dursun.
- **Pointer Events** (`pointerdown`, `pointerup`, `pointercancel`, `lostpointercapture`) + `setPointerCapture`. Ayrıca `blur` ve `visibilitychange` olunca dur.
- **Kalibrasyon hareketlerine süre sınırı.**
- **En alt / en üst ayarla:** Yazılımsal sınırlar, motor uçlara dayanmasın.
- **Yumuşak kalkış/duruş (rampa)** ve **20 kHz PWM** (`ledcAttach`/`ledcWrite`, core 3.x; 2.x uyumluluğu da düşünülsün).
- **Motor başına hız düzeltme katsayısı** ve **yukarı/aşağı için ayrı süre katsayısı.**
- Rampa sırasında konum hesabı hıza göre yapılsın.
- **OTA** (kablosuz güncelleme), `WiFi.setTxPower(WIFI_POWER_8_5dBm)`.
- `setup()`'ın en başında motor pinleri LOW yapılsın, WiFi'dan önce.
- Bölüm 4.8'deki küçük hatalar düzeltilsin. Hafıza değerleri `/data` üzerinden güncellensin. Bağlantı yoksa ekranda gösterilsin.
- Flash'a sadece durunca yazılsın.

### Adım 3: İlk test

1. Önce **sağ** kalibrasyon ▲ butonuna çok kısa basılıp sağ tarafın kalktığı doğrulanır.
2. Sonra **sol** kalibrasyon ▲ butonuna çok kısa basılır. Sol taraf **inerse** sol motorun pinleri koda ters yazılır (7 ↔ 6).
3. Ancak bundan sonra normal YUKARI/AŞAĞI denenir.

### Adım 4: Hız düzeltmesi için ölçüm

1. Masayı kalibrasyonla düzle.
2. Orta konumdan **10 sn yukarı** sür, sağ ve sol yüksekliği metreyle ölç.
3. **10 sn aşağı** sür, tekrar ölç.
4. Farka göre motor katsayıları ayarlanır.

## 7. Notlar

- Kullanıcı Türkçe konuşuyor, adım adım ve sade anlatım tercih ediyor.
- Kod yazmadan önce kullanıcıdan "yaz" onayı beklenmeli.
- Kullanıcı daha önce açıkça istemeden kod yazılmasını durdurmuştu.
