# BIST tez paneli

**Yatırım tavsiyesi değildir.** BIST evrenini tarar; her hisse için karakter kartı
(Fib EMA şeridi, hisseye özel tap EMA, süper çizgi, yatay destek/direnç, hacim, baskın TF)
çıkarır, kural derleyicisiyle **AL/SAT + TF + vade + iptal + hedef** etiketi üretir.
Tezini ("FROTO daily'de çıkacak") panelde sınava sokarsın: **tutuyor / kısmen / tutmuyor**.

Tasarımın gerekçesi: [`docs/BIST-TEZ-DOKUMAN.md`](docs/BIST-TEZ-DOKUMAN.md).

## Kurulum (sunucu / NAS, Docker)

```bash
cd bist-tez
docker compose up -d --build        # NAS'ta: sudo docker compose up -d --build
```

- Panel: `http://SUNUCU_IP:8501` (Tailscale: `http://qnasxnas:8501`)
- İki servis kalkar:
  - `panel` — Streamlit arayüzü
  - `zamanlayici` — hafta içi 18:20'de otomatik tarar, sonucu `data/`'ya yazar
- Log: `docker compose logs -f zamanlayici`
- Durdur: `docker compose down`

`data/` ve `rules/` volume olarak bağlı: kurallar değişince yeniden build gerekmez,
tarama sonuçları ve sinyal günlüğü konteyner silinse de kalır.

> NAS notu: `/tmp` reboot'ta silinir. Projeyi `/volume1/docker/bist-tez` gibi kalıcı bir
> yere koy ve compose'u oradan çalıştır. `unzip` yoksa `python3 -m zipfile -e bist-tez.zip .`

## Yerelde (Docker'sız)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app/panel.py
pytest                      # 38 test, internet gerekmez (sentetik veri)
```

## Komut satırı

```bash
python -m engine tara [--yenile]           # evreni tara, data/sinyal.csv
python -m engine hisse FROTO               # tek hissenin tam kartı
python -m engine geritest FROTO --adim 5   # walk-forward geri test
python -m engine skor                      # günlükteki etiketlerin 5/10/20 bar isabeti
python -m engine zamanla                   # zamanlayıcı döngüsü
```

Docker içinde: `docker compose exec panel python -m engine hisse FROTO`

## Panel sekmeleri

| Sekme | Ne yapar |
|---|---|
| 📋 Tarama | Evreni tarar (paralel, önbellekli). Renkli AL/SAT tablosu, filtre, CSV indir, atlanan hisseler. |
| 📈 Hisse | Mum grafik + seçili Fib EMA'lar + süper çizgi (temas noktaları, 15 bar ileri projeksiyon) + yatay seviyeler + iptal/hedef çizgileri + hacim. Kart, gerekçe, risk, EMA saygı tablosu, 1H grafik. |
| 🧪 Tez sınavı | Hisse + yön + TF → tutuyor / kısmen / tutmuyor, nedenleriyle. İptal seviyesi ve R/R. |
| 🎯 Skor kartı | Her taramanın etiketi `data/gecmis.csv`'ye yazılır; burada 5/10/20 bar sonraki getiri ve kural bazında isabet %'si. |
| ⏪ Geri test | Tek hisse için walk-forward: geçmişte her N barda yalnız o güne kadarki veriyle etiket üretip sonrasını ölçer; "etiketsiz taban" ile kıyaslar. |

## Ayarlar — `rules/sablon.yaml`

Evren (`evren_cekirdek`, `evren_ek`), hacim/tepki/trend/SAT eşikleri, süper çizgi
toleransları, yatay seviye kümeleme, risk uyarıları, zamanlama saatleri. Her alanın
açıklaması dosyada. Eksik alan → `engine/config.py` varsayılanı.

## Çıktı dosyaları (`data/`)

| Dosya | İçerik |
|---|---|
| `sinyal.csv` | Son tarama (her hisse bir satır) |
| `gecmis.csv` | Tüm taramaların etiket günlüğü (gün+hisse tekil) |
| `meta.json` | Son tarama zamanı, süresi, hata sayısı |
| `hatalar.csv` | Atlanan hisseler ve nedeni |
| `cache/` | Yahoo önbelleği (silinebilir) |

## Proje yapısı

```
engine/
  config.py     varsayılan eşikler + YAML birleştirme
  yahoo.py      Yahoo chart API, disk önbelleği, adjclose düzeltmesi
  tech.py       EMA, ATR, ADX-lite, TF kalitesi, 4H/weekly, fractal, EMA saygı, süper çizgi
  seviye.py     yatay destek/direnç kümeleri
  hacim.py      günlük rvol, seans içi saat profili rvol, hacim teyidi
  kart.py       karakter kartı
  derleyici.py  kural → AL/SAT, TF, vade, iptal, hedef, R/R, risk, gerekçe
  tez.py        tez sınavı
  skor.py       sinyal günlüğü + isabet skor kartı
  geritest.py   walk-forward geri test
  grafik.py     plotly mum grafik
  run.py        paralel evren taraması
  zamanla.py    18:20 otomatik tarama
app/panel.py    Streamlit
tests/          pytest (sentetik veri)
```

## Notlar

- Port 8501 doluysa `docker-compose.yml` içinde `8502:8501`.
- Firewall'da 8501'i yalnız LAN/Tailscale'e aç.
- Yahoo 429/502 verirse `veri.paralel` değerini düşür; başarısız indirmede eski önbellek kullanılır.
- Veri gecikmeli ve üçüncü partidir; Borsa İstanbul resmi feed'i değildir.
