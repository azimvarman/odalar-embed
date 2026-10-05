"""Yahoo chart API — disk önbellekli, düzeltmeli fiyat.

- Aynı veriyi `cache_dk` içinde tekrar indirmez (tarama + grafik + geri test aynı dosyayı kullanır).
- İndirme başarısızsa eski önbelleğe düşer; tarama yarım kalmaz.
- `adjust=True` iken OHLC adjclose oranıyla düzeltilir (temettü/split yüzünden eski
  yıllarda ışının kayması azalır).
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from .config import TZ, data_dir

log = logging.getLogger("bist.yahoo")

URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    "?interval={interval}&range={range_}&events=div%7Csplit&includeAdjustedClose=true"
)


def _cache_path(sym: str, interval: str, range_: str) -> Path:
    d = data_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{sym}_{interval}_{range_}.pkl"


def parse(raw: dict, interval: str, adjust: bool = True) -> pd.DataFrame | None:
    res = (raw.get("chart") or {}).get("result")
    if not res:
        return None
    res = res[0]
    ts = res.get("timestamp") or []
    if not ts:
        return None
    ind = res.get("indicators") or {}
    q = (ind.get("quote") or [{}])[0]
    df = pd.DataFrame({
        "Open": q.get("open"), "High": q.get("high"),
        "Low": q.get("low"), "Close": q.get("close"),
        "Volume": q.get("volume"),
    }, dtype="float64")
    df.index = pd.to_datetime(ts, unit="s", utc=True).tz_convert(TZ)
    adj = (ind.get("adjclose") or [{}])[0].get("adjclose")
    if adjust and adj is not None and len(adj) == len(df):
        ratio = pd.Series(adj, index=df.index, dtype="float64") / df["Close"]
        ratio = ratio.where(ratio.notna() & (ratio > 0), 1.0)
        for c in ("Open", "High", "Low", "Close"):
            df[c] = df[c] * ratio
    df = df.dropna(subset=["Close"])
    df["Volume"] = df["Volume"].fillna(0.0)
    for c in ("Open", "High", "Low"):
        df[c] = df[c].fillna(df["Close"])
    if interval == "1d":
        # Yahoo canlı günü bazen farklı saatle ikinci satır olarak verir.
        df.index = df.index.normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "Tarih"
    return df


def _fetch(sym: str, interval: str, range_: str, deneme: int = 3) -> dict | None:
    req = urllib.request.Request(
        URL.format(sym=sym, interval=interval, range_=range_),
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )
    for i in range(deneme):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # ölü ticker; tekrar deneme anlamsız
            bekle = 4.0 * (i + 1) if e.code == 429 else 0.8 * (i + 1)
            log.warning("%s %s HTTP %s, %.1fs sonra tekrar", sym, interval, e.code, bekle)
            time.sleep(bekle)
        except Exception as e:  # ağ, zaman aşımı, bozuk JSON
            log.warning("%s %s hata: %s", sym, interval, e)
            time.sleep(0.8 * (i + 1))
    return None


def history(sym: str, interval: str, range_: str, *, cache_dk: float = 30,
            yenile: bool = False, adjust: bool = True) -> pd.DataFrame | None:
    path = _cache_path(sym, interval, range_)
    taze = path.exists() and (time.time() - path.stat().st_mtime) < cache_dk * 60
    if taze and not yenile:
        try:
            return pd.read_pickle(path)
        except Exception:
            pass
    raw = _fetch(sym, interval, range_)
    df = parse(raw, interval, adjust) if raw else None
    if df is not None and len(df):
        tmp = path.with_suffix(".tmp")
        df.to_pickle(tmp)
        tmp.replace(path)
        return df
    if path.exists():
        log.warning("%s %s indirilemedi, eski önbellek kullanılıyor", sym, interval)
        try:
            return pd.read_pickle(path)
        except Exception:
            return None
    return None


def cached(sym: str, interval: str, range_: str) -> pd.DataFrame | None:
    """Ağa çıkmadan yalnızca önbellekten oku (panel grafikleri için)."""
    path = _cache_path(sym, interval, range_)
    if not path.exists():
        return None
    try:
        return pd.read_pickle(path)
    except Exception:
        return None
