import numpy as np
import pandas as pd

from conftest import sentetik_gunluk, sentetik_saatlik
from engine import tech
from engine.seviye import en_yakin, yatay_seviyeler


def test_fractal_lows_bulur():
    s = pd.Series([5, 4, 3, 4, 5, 4, 2, 4, 5, 6, 7])
    assert tech.fractal_lows(s, 2) == [2, 6]
    assert tech.fractal_highs(s, 2) == [4]


def test_destek_isini_gomulu_cizgiyi_bulur(gunluk):
    a = float(tech.atr(gunluk).iloc[-1])
    ray = tech.destek_isini(gunluk, a)
    assert ray is not None
    assert ray["touches"] >= 4
    assert abs(ray["slope"] - 0.08) < 0.02
    gercek_now = 100 + 0.08 * (len(gunluk) - 1)
    assert abs(ray["now"] - gercek_now) / gercek_now < 0.03
    assert ray["kirik"] is False


def test_isin_kirilinca_kirik_isaretlenir():
    d = sentetik_gunluk(son_mesafe=-0.06)
    a = float(tech.atr(d).iloc[-1])
    ray = tech.destek_isini(d, a)
    assert ray is not None and ray["kirik"] is True
    assert ray["dist"] < 0


def test_ema_saygi_tablosu(gunluk):
    r = tech.ema_saygi(gunluk["Close"], tech.atr(gunluk), min_olay=5)
    assert r["span"] in tech.FIB
    assert set(r["tablo"]) == set(tech.FIB)
    assert 0 <= r["oran"] <= 100


def test_ema_saygi_trendde_destek_tutar():
    # sürekli yükselen seri: EMA'ya üstten gelen dokunuşlar çoğunlukla tutmalı
    n = 1500
    rng = np.random.default_rng(1)
    c = pd.Series(100 * np.exp(np.cumsum(0.001 + 0.01 * rng.standard_normal(n))))
    a = pd.Series(np.full(n, float(c.diff().abs().mean())))
    r = tech.ema_saygi(c, a, spans=(55, 89), min_olay=5)
    assert r["oran"] > 50


def test_weekly_ve_h4():
    h = sentetik_saatlik()
    k4 = tech.h4(h)
    assert set(k4.index.hour) <= {10, 14}
    assert len(k4) == 2 * 120
    w = tech.weekly(sentetik_gunluk(n=300))
    assert (w.index.dayofweek == 4).all()


def test_tf_quality_kisa_seri():
    assert tech.tf_quality(sentetik_gunluk(n=50))["score"] == -999


def test_yatay_seviyeler():
    n = 400
    i = np.arange(n)
    close = 100 + 8 * np.sin(i / 10)  # 92–108 arası salınım
    idx = pd.bdate_range("2024-01-01", periods=n)
    d = pd.DataFrame(dict(Open=close, High=close + 0.2, Low=close - 0.2, Close=close,
                          Volume=1.0), index=idx)
    sev = yatay_seviyeler(d, 1.0, order=3)
    seviyeler = sorted(round(s["seviye"]) for s in sev)
    assert 92 in seviyeler or 91 in seviyeler
    assert 108 in seviyeler or 109 in seviyeler
    destek, direnc = en_yakin(sev, 100.0)
    assert destek["seviye"] < 100 < direnc["seviye"]
