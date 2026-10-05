"""Teknik katman: EMA şeridi, ATR, ADX-lite, TF kalitesi, fractal pivot, destek ışını."""
from __future__ import annotations

import numpy as np
import pandas as pd

FIB = (8, 13, 21, 34, 55, 89, 144, 233)

OHLCV = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean()


def adx_lite(df: pd.DataFrame, n: int = 14) -> float:
    h, l = df["High"], df["Low"]
    up, dn = h.diff(), -l.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = atr(df, n).replace(0, np.nan)
    pdi = 100 * pd.Series(plus, index=df.index).ewm(span=n, adjust=False).mean() / tr
    mdi = 100 * pd.Series(minus, index=df.index).ewm(span=n, adjust=False).mean() / tr
    dx = (100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)).fillna(0)
    return float(dx.ewm(span=n, adjust=False).mean().iloc[-1])


def tf_quality(df: pd.DataFrame, stack_win: int = 60, whip_win: int = 120) -> dict:
    """Rejim skoru: 0.6*ADX + 0.35*stack% - 1.2*whip."""
    if df is None or len(df) < 80:
        return dict(adx=0.0, stack=0.0, whip=99.0, score=-999.0)
    c = df["Close"]
    adx = adx_lite(df)
    e8, e21, e55 = ema(c, 8), ema(c, 21), ema(c, 55)
    stacked = (((e8 > e21) & (e21 > e55)) | ((e8 < e21) & (e21 < e55))).iloc[-stack_win:].mean() * 100
    cross = (e8 > e21)
    whip = float((cross != cross.shift(1)).iloc[1:].iloc[-whip_win:].sum())
    return dict(adx=round(adx, 1), stack=round(float(stacked), 1), whip=whip,
                score=round(adx * 0.6 + float(stacked) * 0.35 - whip * 1.2, 1))


def weekly(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("W-FRI").agg(OHLCV).dropna(subset=["Close"])


def h4(df: pd.DataFrame) -> pd.DataFrame:
    """1H → 4H. BIST seansı 10:00–18:00; 02:00 ofsetiyle kutular 10–14 ve 14–18 olur."""
    if df is None or not len(df):
        return df
    out = df.resample("4h", origin="start_day", offset="2h").agg(OHLCV)
    return out.dropna(subset=["Close"])


def _fractal(s: pd.Series, order: int, fn: str) -> list[int]:
    if len(s) < 2 * order + 1:
        return []
    w = getattr(s.rolling(2 * order + 1, center=True), fn)()
    mask = (s == w).to_numpy().copy()
    mask[:order] = False
    mask[len(s) - order:] = False
    return np.flatnonzero(mask).tolist()


def fractal_lows(low: pd.Series, order: int = 8) -> list[int]:
    return _fractal(low, order, "min")


def fractal_highs(high: pd.Series, order: int = 8) -> list[int]:
    return _fractal(high, order, "max")


def ema_saygi(close: pd.Series, atrs: pd.Series, spans=FIB, tol: float = 0.45,
              ileri: int = 5, min_olay: int = 30) -> dict:
    """Hisseye özel tap EMA.

    Olay: fiyat EMA'nın `tol*ATR` bandına *ilk* girdiği bar (aynı temasın ardışık
    barları tek olay sayılır). Başarı: `ileri` bar sonra fiyat geldiği taraftaysa
    (üstten geldiyse hâlâ üstte → destek tuttu; alttan geldiyse hâlâ altta → direnç
    tuttu). Oran = EMA'ya "saygı" yüzdesi. En yüksek oranlı span seçilir.
    """
    c = close.to_numpy(dtype=float)
    a = atrs.to_numpy(dtype=float)
    n_bar = len(c)
    tablo: dict[int, tuple[int, float]] = {}
    best = dict(span=34, olay=0, oran=0.0)
    for n in spans:
        e = ema(close, n).to_numpy()
        side = np.sign(c - e)
        touch = np.abs(c - e) <= a * tol
        idx = np.flatnonzero(touch[1:] & ~touch[:-1]) + 1
        idx = idx[(idx >= n) & (idx + ileri < n_bar)]
        ps = side[idx - 1]
        ok = ps != 0
        idx, ps = idx[ok], ps[ok]
        t = int(len(idx))
        w = int((side[idx + ileri] == ps).sum()) if t else 0
        wr = w / t * 100 if t else 0.0
        tablo[n] = (t, round(wr, 1))
        if t >= min_olay and wr >= best["oran"]:
            best = dict(span=n, olay=t, oran=wr)
    best["tablo"] = tablo
    return best


def destek_isini(df: pd.DataFrame, atr_last: float, *, tol_atr: float = 0.55,
                 min_aralik: int = 40, min_touch: int = 3, dist_min: float = -10.0,
                 dist_max: float = 40.0, kirik_bar: int = 2) -> dict | None:
    """Çok temaslı yükselen destek ("süper çizgi").

    Orijin eski bir fractal dip (serinin ilk %75'i), ikinci nokta en az `min_aralik`
    bar sonra ve orijinin ≥ %97'si. Doğru bugüne uzatılır; temas = fractal dip doğruya
    `tol_atr*ATR` yakın; ihlal = kapanışın doğrunun altına indiği *epizot* sayısı.
    Skor = 4*temas − 1.2*ihlal − 10*|dist|.
    """
    low, close = df["Low"], df["Close"]
    lows = fractal_lows(low, 10)
    if len(lows) < 3:
        lows = fractal_lows(low, 5)
    if len(lows) < 3:
        return None
    lows_a = np.asarray(lows)
    lo, c = low.to_numpy(dtype=float), close.to_numpy(dtype=float)
    last_i = len(c) - 1
    last_px = c[-1]
    tol = atr_last * tol_atr
    origins = lows_a[lows_a < last_i * 0.75][-18:]
    later = lows_a[lows_a > last_i * 0.25]
    best = None
    for i0 in origins:
        p0 = lo[i0]
        cands = later[(later - i0 >= min_aralik) & (lo[later] >= p0 * 0.97)][-8:]
        piv = lows_a[lows_a >= i0]
        seg = np.arange(i0, last_i + 1)
        for i1 in cands:
            slope = (lo[i1] - p0) / (i1 - i0)
            intercept = p0 - slope * i0
            now = intercept + slope * last_i
            if now <= 0:
                continue
            dist = (last_px - now) / now * 100
            if dist < dist_min or dist > dist_max:
                continue
            tmask = np.abs(lo[piv] - (intercept + slope * piv)) <= tol
            touches = int(tmask.sum())
            if touches < min_touch:
                continue
            below = c[seg] < intercept + slope * seg - tol
            viol = int(below[0]) + int(np.sum(below[1:] & ~below[:-1]))
            score = touches * 4 - viol * 1.2 - abs(dist) / 100 * 10
            if best is None or score > best["score"]:
                best = dict(now=float(now), dist=float(dist), touches=touches, viol=viol,
                            score=float(score), i0=int(i0), i1=int(i1),
                            slope=float(slope), intercept=float(intercept),
                            touch_idx=piv[tmask].astype(int).tolist(), tol=float(tol))
    if best is None:
        return None
    k = max(1, kirik_bar)
    son = np.arange(last_i - k + 1, last_i + 1)
    line = best["intercept"] + best["slope"] * son
    best["kirik"] = bool(np.all(c[son] < line - tol))
    vol = df["Volume"].astype(float)
    rvol = (vol / vol.rolling(20).mean()).to_numpy()
    vals = [rvol[i] for i in best["touch_idx"][-3:] if np.isfinite(rvol[i])]
    best["ray_rvol"] = round(float(np.mean(vals)), 2) if vals else None
    return best


def ema_near(close: pd.Series, last: float, atr_last: float, k: float = 0.5,
             spans=FIB) -> list[int]:
    return [n for n in spans if abs(last - float(ema(close, n).iloc[-1])) <= atr_last * k]
