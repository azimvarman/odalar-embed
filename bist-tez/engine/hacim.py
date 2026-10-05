"""Hacim teyidi.

Seans açıkken günlük bar eksiktir (13:30'da rvol 0.4 tuzağı). Bu yüzden:
- günlük rvol son *kapalı* gün üzerinden,
- ek olarak saat profili rvol: bugün şu saate kadarki birikimli hacim /
  son 20 günün aynı saate kadarki ortalama birikimli hacmi.
"""
from __future__ import annotations

import pandas as pd

from .config import TZ

SEANS_SONU_SAAT = 18


def seans_kapali(son_bar: pd.Timestamp, now: pd.Timestamp | None = None) -> bool:
    now = now or pd.Timestamp.now(tz=TZ)
    if son_bar.tzinfo is None:
        son_bar = son_bar.tz_localize(TZ)
    return son_bar.normalize() < now.normalize() or now.hour >= SEANS_SONU_SAAT


def gunluk_rvol(d: pd.DataFrame, kapali: bool) -> tuple[float | None, float | None]:
    vol = d["Volume"].astype(float)
    rvol = vol / vol.rolling(20).mean()
    use = rvol if kapali else rvol.iloc[:-1]
    use = use.dropna()
    r20 = float(use.iloc[-1]) if len(use) else None
    r5 = float(use.iloc[-5:].mean()) if len(use) >= 5 else None
    return r20, r5


def seans_rvol(h: pd.DataFrame | None, gun: int = 20) -> float | None:
    if h is None or len(h) < 50:
        return None
    idx = h.index
    tod = idx.hour * 60 + idx.minute
    lim = tod[-1]
    gunler = idx.normalize()
    son = gunler[-1]
    cum = h["Volume"].astype(float)[tod <= lim].groupby(gunler[tod <= lim]).sum()
    if son not in cum.index:
        return None
    ref = cum.drop(son).iloc[-gun:]
    if len(ref) < gun // 2 or ref.mean() <= 0:
        return None
    return float(cum.loc[son] / ref.mean())


def hacim_ok(rvol20, rvol5, ray_rvol, rvol_seans, cfg: dict) -> tuple[bool, str]:
    h = cfg["hacim"]
    if rvol20 is not None and rvol20 >= h["rvol20_min"]:
        return True, f"rvol20 {rvol20:.2f} ≥ {h['rvol20_min']}"
    if rvol5 is not None and rvol5 >= h["rvol5_min"]:
        return True, f"rvol5 {rvol5:.2f} ≥ {h['rvol5_min']}"
    if rvol_seans is not None and rvol_seans >= h["seans_rvol_min"]:
        return True, f"seans rvol {rvol_seans:.2f} ≥ {h['seans_rvol_min']}"
    if (ray_rvol is not None and ray_rvol >= h["ray_rvol_min"]
            and rvol20 is not None and rvol20 >= h["ray_rvol_gun_min"]):
        return True, f"ışın temas rvol {ray_rvol:.2f} + gün {rvol20:.2f}"
    return False, "hacim teyidi yok"
