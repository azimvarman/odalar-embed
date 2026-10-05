# BIST Tez Paneli — derin hat

Yatırım tavsiyesi değildir. Bu belge, uygulamanın **neden böyle kurulduğunu**, hangi fikirlerin **hangi GitHub / yöntemden** alındığını, hangilerinin **bilerek atıldığını** ve her katmanın **ne işe yaradığını** anlatır.

Amaç: kullanıcının kendi cümlesini (“bu hisse daily’de çıkacak”) teknik yapıya karşı sıkıştırmak. Motor “al” demez; **tutuyor / kısmen / tutmuyor** der.

---

## 1. Problem tanımı (nereden geldi)

Başlangıç isteği üç parçaydı:

1. Hisse tarihini tarayıp **hisseye özel EMA** bulmak (evrensel 20/50 değil).
2. Fib EMA şeridinde (8–13–21–34–55–89–144–233–367) **çok yıllık ortalama dönüşünü** görmek.
3. Grafikte elle çekilen **eski tarihli yükselen destek** (“süper çizgi”) — yıllar önce değdiği yere tekrar değmesi — bunu algoritmanın **önceden görmesi**.

Sonra kısıtlar netleşti:

- Tek hissede (FROTO) takılı kalma. Evren: BIST yüksek hacimli.
- Her hissenin kuralı başka. Önce **karakter kartı**, sonra kural.
- Dominant TF girdi değil, **analiz çıktısı** (daily / weekly / 4H / 1H).
- GitHub’dan repo klonlamak yok: her repodan **5–10 işe yarar parça**, 100 parçalık sistem.
- Çıktıda AL/SAT görünsün ama vade ve TF yazılsın; uzun AL ile kısa tepki karışmasın.
- Hacim teyidi olmadan yapı “sinyal” sayılmasın.

Uygulama bu kısıtların Docker + tarayıcı hali.

---

## 2. Mimari özet

```
Yahoo chart API
    → daily 5y + 1H 2y
        → teknik katman (EMA, ATR, ADX-lite, fractal pivot, ışın, rvol)
            → karakter kartı
                → kural derleyici (YAML eşik)
                    → AL / SAT + TF + vade
                        → Streamlit panel + tez sınavı
```

Tek konteyner: `python:3.12-slim` + Streamlit `:8501`.  
Kalıcı çıktı: `data/sinyal.csv` (volume).  
Eşikler: `rules/sablon.yaml` (kodu yeniden derlemeden değişir).

---

## 3. GitHub / literatür — alınan parçalar

Tam repo gömülmedi. Aşağıdaki isimler **fikir kaynağı**; kod yerelde yeniden yazıldı (pandas/numpy). `trendln` gibi paketler ortamda index hatası verdi, numpy dizisine indirgenmiş mantık kullanıldı.

### 3.1 Fib EMA şeridi

- Kaynak sınıfı: klasik Fibonacci lookback + ribbon (TradingView “Fib EMA”, birçok `pandas_ta` örneği).
- Span: `8, 13, 21, 34, 55, 89, 144, 233` (367 isteğe bağlı; daily’de çok yavaş, kartta 233 “uzun” kabul).
- Kullanım:
  - Konum: fiyat `< EMA233` → `uzun_alti`; `< EMA89` → `orta_alti`; aksi `orta_ustu`.
  - **EMA saygı istatistiği (v2):** olay = fiyatın EMA’nın `0.45 * ATR` bandına *ilk* girdiği bar
    (aynı temasın ardışık barları tek olay; ilk `span` bar ısınma olarak atlanır).
    Başarı = 5 bar sonra fiyat **geldiği tarafta** (üstten geldiyse hâlâ üstte → destek tuttu).
    v1’de ardışık barlar ayrı sayılıyor ve başarı “karşı tarafa geçiş” olarak ölçülüyordu;
    bu, trend kuralındaki “EMA destek” yorumuyla çelişiyordu.
  - En yüksek yüzdeli span (en az 30 olay) = **hisseye özel tap EMA** (grid search, optimize paket değil).
  - Panelde tüm span’ların (olay, %) tablosu görünür.

Alınan parça: “tek EMA değil, şerit + hisse bazlı tap skoru”.  
Atılan: genetik algoritma ile 200 span tarama (ezber, walk-forward’suz).

### 3.2 Pivot / zigzag dipler

- Kaynak sınıfı: `zigzag`, `peakutils`, TradingView pivot, `trendln.get_extrema`.
- Uygulama: `order` pencereli fractal low (bar i, ±order komşuluğunun minimumu).
- Daily `order=10`, yetersizse `5`.

Alınan: extrema listesi.  
Atılan: tam zigzag amplitude filtresi (eşik hisse ATR’sine bağlandı, ayrı lib yok).

### 3.3 Multi-touch rising support (“süper çizgi”)

- Kaynak sınıfı:
  - `trendln.calc_support_resistance` (pivot çiftinden doğru).
  - `Trendline-Detection-Engine` tipi touch + ihlal skoru.
  - Elle çizilen trendline pratikleri (en az 3 değme, eski orijin).
- Algoritma:
  1. Orijin: son %75’ten **önceki** dipler (çok yeni çizgi “süper” sayılmaz).
  2. İkinci nokta: orijinden en az 40 bar sonra, dip ≥ orijin * 0.97 (yükselen).
  3. Doğru: `y = intercept + slope * i`.
  4. Bugünkü projeksiyon: `now = intercept + slope * last_i`.
  5. Dist: `(fiyat - now) / now`.
  6. Touch: dip, doğru ± `0.55 ATR` içindeyse say.
  7. İhlal: orijinden bugüne **tüm kapanışlar** taranır; doğru − toleransın altına iniş
     *epizotları* sayılır (v1 yalnız pivot barlarına bakıyordu).
  8. Skor: `4*touch - 1.2*ihlal - 10*|dist|`.
  9. Yakın fiyatlı çiftleri ele (aynı çizginin kopyası).
- Filtre: dist `[-10%, +40%]` dışı çizgi “şimdi işe yaramaz” (çok altında kırılmış veya çok üstte ilgisiz).
- **Canlı iptal (v2):** son `kirik_bar` (2) kapanış doğru − toleransın altındaysa `cizgi_kirik=True`.
  Kırık çizgide TEPKI kuralları çalışmaz, `SAT daily kısa` yazılır ve geri alım seviyesi (`sat_iptal`) verilir.
- Grafikte çizgi orijinden bugüne + 15 bar ileri çizilir, temaslar işaretlenir; kırıksa kırmızı.

Bu, kullanıcının FROTO 1H’de mavi daireden çektiği yeşil çizginin **sınıfı**: eski dip → ileri uzayan destek ışını.  
Pitchfork / Andrews median **bilerek yok** (ayrı parça).

### 3.4 Yatay S/R cluster

- Kaynak: `agglomerative clustering` / day0market tarzı pivot kümeleri.
- **v2’de eklendi** (`engine/seviye.py`): son 500 barın fractal tepe+dipleri (order 5) fiyata göre
  sıralanır, küme ortalamasına `0.6 * ATR` yakın olanlar birleşir, en az 3 temaslı kümeler seviye olur.
- Kart: en yakın `destek` / `direnc` ve % mesafeleri. Direnç AL’ın **hedefi** olur; R/R buradan hesaplanır.
  AL varken direnç %2’den yakınsa risk uyarısı.

### 3.5 TF keşfi (dominant timeframe)

- Kaynak sınıfı: ADX + EMA stack + whipsaw sayımı (birçok “regime filter” reposu, tek lib değil).
- Skor: `0.6*ADX + 0.35*stack% - 1.2*whip`.
- Adaylar: weekly (W-FRI resample), daily, **4H** (1H’den 10–14 / 14–18 kutuları), 1H.
- `dom_tf = argmax(skor)`.
- Giriş TF’si: weekly → daily, daily → 4H, 4H → 1H (`giris_tf` alanı). Tüm skorlar `tf_skor` alanında.

### 3.6 Hacim teyidi

- Kaynak: klasik relative volume (`volume / SMA(20)`), “volume confirms breakout” blog/repo kalıbı.
- Kurallar (`sablon.yaml`):
  - `rvol20 >= 1.10` **veya**
  - son 5 tam gün `rvol5 >= 1.05` **veya**
  - ışın temaslarının ort. rvol ≥ 1.15 **ve** gün ≥ 0.85
- Seans açıkken bugünkü bar eksik → rvol **son kapalı gün** üzerinden (13:30’da 0.4 rvol tuzak).
- **Saat profili rvol (v2):** seans açıkken bugünün şu saate kadarki birikimli hacmi /
  son 20 günün aynı saate kadarki ortalaması (`rvol_seans ≥ 1.10` de teyit sayılır).
- Yapı var hacim yoksa kural `*_HACIM_YOK`, AL yazılmaz (`YOK`).

Atılan: VWAP kurumsal footprint, order book (veri yok).

### 3.7 Alınmayan / bilinçli dışarıda

| Fikir | Neden yok |
|---|---|
| LSTM / Transformer fiyat tahmini | Tez testini “kehanet”e çevirir |
| “%90 winrate” backtest ekranı | Walk-forward’suz yalan |
| Broker emir API | Ürün tez konsolu |
| Ham `trendln` paketi | DatetimeIndex çökmesi |
| Genetika ile EMA evrimi | Overfit |
| 40 repo clone | 5–10 parça kuralı |

---

## 4. Karakter kartı alanları

Her hisse bir satır:

| Alan | Anlam |
|---|---|
| `fiyat` | Son kapanış (veya son bar) |
| `konum` | uzun_alti / orta_alti / orta_ustu |
| `dom_tf` | weekly / daily / 1H |
| `ema_tap`, `ema_tap_pct` | En iyi Fib span ve 5 bar dönüş % |
| `proj_now`, `proj_dist` | Daily süper çizgi bugünkü değeri ve % mesafe |
| `cizgi_touch` | Işın dokunuş sayısı |
| `h1_ema_near` | 1H’de ATR içindeki EMA’lar |
| `rvol20`, `rvol5`, `rvol_seans`, `hacim_ok`, `hacim_neden` | Hacim |
| `cizgi_ihlal`, `cizgi_kirik`, `cizgi_orijin` | Işın ihlal epizotu, canlı kırılım, orijin tarihi |
| `destek`, `direnc` (+ `_dist`, `direnc_touch`) | Yatay seviyeler |
| `giris_tf`, `tf_skor` | Giriş TF’si, tüm TF skorları |
| `kural` | Derleyici çıktısı |
| `AL/SAT`, `*_TF`, `*_vade` | Etiket |
| `iptal`, `hedef`, `rr`, `sat_iptal` | AL iptal seviyesi (2 kapanış altı), hedef (direnç), risk/ödül |
| `risk`, `gerekce` | Okunur uyarılar ve kuralın neden yandığı |
| `cakisma` | Aynı satırda AL+SAT |

---

## 5. Derleyici (kural → etiket)

Sıra önemli; ilk eşleşen kazanır.

1. `uzun_alti` + `|dist|≤3` + touch≥4 → `TEPKI_ZONE`  
   AL daily **kısa** (dönüş değil, tepki).
2. `uzun_alti` + `|dist|≤5.5` + touch≥6 → `TEPKI_ZONE_GEVSEK`  
   AL daily kısa, zone geniş.
3. `orta_*` + `dom_tf=weekly` + tap≥57 → `TREND_HAFTALIK`  
   AL weekly **uzun**.
4. `orta_ustu` + tap≥57 + `|dist|≤3.5` → `TREND_DAILY_ISIN`  
   AL daily **orta**.
5. `orta_ustu` + tap≥57 (ışın uzak) → `TREND_EMA_SADE`  
   AL daily kısa, zayıf.
6. 1H’de 89/144/233 teması → `1H_EMA_YIGIN`  
   AL 1H/4H kısa.
7. Aksi `IZLE`.

Hacim `ok` değilse AL = `YOK`.

v2 ekleri: ışın kırıksa (1), (2), (4) çalışmaz. Her AL’a iptal seviyesi:
TEPKI/DAILY_ISIN → ışın − tolerans; HAFTALIK/EMA_SADE → tap EMA − 0.5 ATR; 1H → 1H derin EMA − 0.5 ATR(1H).

**SAT** (ayrı, kaba):

- Işın `kirik` (2 kapanış) → SAT daily kısa (v2, öncelikli).
- `uzun_alti` ve `dist ≤ -5` → SAT daily kısa (ışın kırılmış olabilir).
- `uzun_alti` ve weekly dom → SAT weekly uzun.

Çakışma: AL ve SAT birlikteyse tez “çıkacak” onaylanmaz.

---

## 6. Tez sınavı (panel)

Kullanıcı: hisse + yön + TF.

- “çıkacak” + weekly + AL uzun → **tutuyor**
- “çıkacak” + daily + AL orta → **tutuyor**
- “çıkacak” + AL kısa → **kısmen** (tepki ≠ çıkış)
- “çıkacak” + SAT var → **tutmuyor**
- “dönecek” + TEPKI_ZONE AL → **tutuyor**
- “kırılacak” + SAT aynı TF → **tutuyor**
- v2: AL+SAT çakışması → “çıkacak” **tutmuyor**; hacimsiz yapı (`AL=YOK`) → **tutmuyor**;
  ışın kırık → “dönecek” **tutmuyor**; uzun AL + daily tez → **kısmen** (giriş TF’sinde teyit bekle).
  Her sonuç neden listesiyle gelir.

FROTO örneği (kurulum anı mantığı): 1H EMA233 yığın + hacim ONAY → AL kısa 1H. Daily ışın ~%4–5 yukarı. “Daily çıkacak” → **kısmen / tutmuyor**. Elle çizilen çizgi sınıfı doğru; iddia (kırılıp gidecek) ayrı.

---

## 7. Veri

- Kaynak: `query1.finance.yahoo.com/v8/finance/chart/{SYM}.IS`
- Daily `range=5y interval=1d`
- Intraday `range=730d interval=1h`
- BIST saat dilimi: `Europe/Istanbul`
- Sembol listesi YAML. Ölü ticker (CIMER) sessizce düşer.
- Yahoo limit / 502 olursa tarama yarım kalır; tekrar dene.

Borsa İstanbul resmi feed yok. Fiyat/hacim gecikmeli.
v2: OHLC `adjclose/close` oranıyla düzeltilir (`veri.adjust`), böylece temettü/split ışını kaydırmaz.
İndirmeler `data/cache/` altında `cache_dk` (30 dk) saklanır; indirme başarısızsa eski önbellek kullanılır.
Tarama 4 paralel istekle yapılır (`veri.paralel`).

---

## 8. Docker / çalışma

```
bist-tez/
  Dockerfile          python:3.12-slim, TZ Istanbul, streamlit 8501, healthcheck
  docker-compose.yml  panel + zamanlayici (18:20), volume data + rules
  engine/             config yahoo tech seviye hacim kart derleyici tez skor geritest grafik run zamanla
  app/panel.py        Streamlit (Tarama, Hisse, Tez, Skor, Geri test)
  rules/sablon.yaml   evren + tüm eşikler
  tests/              pytest, sentetik veri
  data/               sinyal.csv gecmis.csv meta.json hatalar.csv cache/
```

NAS notları (Kurum925):

- Home yoktu (`/var/services/homes/azimvarman` yok) → `/tmp` kullanıldı.
- `unzip` yok → `python3 -m zipfile`.
- Docker soketi `azimvarman` için kapalı → `sudo docker compose`.
- `/tmp` reboot’ta silinir. Kalıcı: `/volume1/.../bist-tez` + compose oradan.

Tarama ilk seferde ~2–4 dk (38 hisse × 2 interval, 4 paralel); önbellek tazeyken saniyeler.

---

## 9. Derin hat — tasarım kararları

1. **Önce kart, sonra kural.** Evrensel “EMA21 al” yok. FROTO kuralı TUPRS kuralı değil.
2. **TF çıktıdır.** “Hep daily bak” yok. Haftalık yığılan hisse daily’de kırbaçlanır.
3. **Tepki ≠ trend.** `uzun_alti` AL her zaman kısa. Bunu uzun çıkış diye yutmamak için vade alanı var.
4. **Hacim veto.** Yapı tek başına yeşil olmasın.
5. **Işın projeksiyonu daily bar index.** Takvim günü değil işlem barı. 1H’ye “aynı now fiyatı” ile taşınır; slope*5 ≈ 5 seans ileri (kaba).
6. **5–10 parça kuralı.** Repo evreni şişirmez. Yeni parça (yatay cluster, 2 bar iptal, saatlik rvol profili) ayrı PR gibi eklenir.
7. **Panel emir değil.** Yeşil AL = “bu etiket şu an yanıyor”. Kullanıcı tezini buraya getirir.

---

## 10. Eksikler — durum (v2)

| Parça | Durum |
|---|---|
| Yatay S/R cluster | ✅ `seviye.py`, destek/direnç + hedef + R/R |
| 2 kapanışlık canlı iptal | ✅ `cizgi_kirik`, AL `iptal` seviyesi, SAT `sat_iptal` |
| Saat profiline göre seans-içi rvol | ✅ `rvol_seans` |
| 5/10/20 bar hit-rate skor kartı | ✅ `gecmis.csv` + Skor kartı sekmesi + `python -m engine skor` |
| Walk-forward geri test | ✅ Geri test sekmesi (daily/weekly kurallar; 1H dahil değil) |
| Kalıcı volume + gece tarama | ✅ `zamanlayici` servisi, 18:20 hafta içi |
| Mum grafik + ışın overlay | ✅ plotly, EMA şeridi, temaslar, seviyeler, iptal/hedef |
| 4H TF | ✅ dom TF adayı |
| Pitchfork | ⛔ bilinçli dışarıda (ayrı parça) |

Sıradaki adaylar: geri test sonuçlarından hisse bazlı eşik önerisi (yalnız öneri, otomatik
optimizasyon değil — overfit), Telegram/e-posta bildirimi, BIST resmi kapanış verisi.

## 11. Sorumluluk

Kod ve panel eğitim / kişisel tez doğrulama aracıdır. AL/SAT yatırım tavsiyesi, emir veya getiri vaadi değildir. Veri üçüncü parti (Yahoo) ve hatalı olabilir.
