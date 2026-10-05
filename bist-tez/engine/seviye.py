"""Yatay destek/direnç kümeleri (pivot tepe + dip, ATR toleranslı gruplama)."""
from __future__ import annotations

import pandas as pd

from .tech import fractal_highs, fractal_lows


def yatay_seviyeler(df: pd.DataFrame, atr_last: float, *, order: int = 5,
                    tol_atr: float = 0.6, min_touch: int = 3,
                    lookback: int = 500) -> list[dict]:
    d = df.iloc[-lookback:]
    off = len(df) - len(d)
    hi = d["High"].to_numpy()
    lo = d["Low"].to_numpy()
    pts = [(float(hi[i]), i + off) for i in fractal_highs(d["High"], order)]
    pts += [(float(lo[i]), i + off) for i in fractal_lows(d["Low"], order)]
    pts.sort()
    tol = atr_last * tol_atr
    kumeler: list[dict] = []
    for p, i in pts:
        k = kumeler[-1] if kumeler else None
        if k is not None and abs(p - k["seviye"]) <= tol:
            k["fiyatlar"].append(p)
            k["idx"].append(i)
            k["seviye"] = sum(k["fiyatlar"]) / len(k["fiyatlar"])
        else:
            kumeler.append(dict(seviye=p, fiyatlar=[p], idx=[i]))
    out = []
    for k in kumeler:
        if len(k["fiyatlar"]) >= min_touch:
            out.append(dict(seviye=float(k["seviye"]), touch=len(k["fiyatlar"]),
                            son_i=int(max(k["idx"])), idx=sorted(k["idx"])))
    return out


def en_yakin(seviyeler: list[dict], fiyat: float) -> tuple[dict | None, dict | None]:
    """Fiyatın altındaki en yakın destek, üstündeki en yakın direnç."""
    alt = [s for s in seviyeler if s["seviye"] <= fiyat]
    ust = [s for s in seviyeler if s["seviye"] > fiyat]
    destek = max(alt, key=lambda s: s["seviye"]) if alt else None
    direnc = min(ust, key=lambda s: s["seviye"]) if ust else None
    return destek, direnc
