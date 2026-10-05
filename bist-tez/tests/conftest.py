from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sentetik_gunluk(n=1250, seed=7, egim=0.08, taban=100.0, son_mesafe=None) -> pd.DataFrame:
    """Yükselen bir destek çizgisine (taban + egim*i) periyodik olarak değen seri.

    Fiyat çizginin üstünde salınır; her ~120 barda bir çizgiye iner.
    `son_mesafe` verilirse son kapanış çizgiden bu oranda (ör. 0.01 = %1 üstte) olur.
    """
    rng = np.random.default_rng(seed)
    i = np.arange(n)
    line = taban + egim * i
    faz = (i % 120) / 120
    yukari = 25 * np.sin(np.pi * faz) ** 2
    close = line * (1 + 0.004 * rng.standard_normal(n)) + yukari + 1.5
    if son_mesafe is not None:
        hedef = line[-1] * (1 + son_mesafe)
        close[-6:] = np.linspace(close[-7], hedef, 7)[1:]
    high = close * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.006, n)))
    # dip barlarında low tam çizgiye değsin
    dip = (i % 120 == 0) & (i > 0)
    low[dip] = line[dip]
    open_ = np.r_[close[0], close[:-1]]
    vol = rng.lognormal(13, 0.3, n)
    idx = pd.bdate_range("2021-01-04", periods=n, tz="Europe/Istanbul")
    return pd.DataFrame(dict(Open=open_, High=np.maximum.reduce([high, open_, close]),
                             Low=np.minimum.reduce([low, open_, close]), Close=close,
                             Volume=vol), index=idx)


def sentetik_saatlik(gun=120, seed=3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    gunler = pd.bdate_range("2026-01-05", periods=gun, tz="Europe/Istanbul")
    idx = [g + pd.Timedelta(hours=h) for g in gunler for h in range(10, 18)]
    n = len(idx)
    close = 100 + np.cumsum(rng.normal(0, 0.3, n))
    vol = rng.lognormal(10, 0.2, n)
    return pd.DataFrame(dict(Open=close, High=close + 0.3, Low=close - 0.3, Close=close,
                             Volume=vol), index=pd.DatetimeIndex(idx))


@pytest.fixture
def cfg():
    from engine.config import load_rules
    return load_rules()


@pytest.fixture
def gunluk():
    return sentetik_gunluk()


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    import engine.config as c
    monkeypatch.setattr(c, "DATA", tmp_path / "data")
    return tmp_path / "data"
