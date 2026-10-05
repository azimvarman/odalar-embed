"""Hit-rate skor kartı.

- `gunluk_kaydet`: her taramanın etiketlerini `data/gecmis.csv`'ye ekler (gün+hisse tekil).
- `ileri_getiri`: bir etiketin 5/10/20 bar sonraki getirisi ve iptal seviyesinin
  vurulup vurulmadığı.
- `ozet`: kural × yön bazında isabet yüzdesi. Kendini ölçmek için.
"""
from __future__ import annotations

import pandas as pd

from .config import data_dir

GECMIS_ALAN = ["tarih", "sembol", "fiyat", "kural", "AL", "AL_TF", "AL_vade",
               "SAT", "SAT_TF", "SAT_vade", "iptal", "hedef", "dom_tf", "konum"]


def gecmis_yolu():
    return data_dir() / "gecmis.csv"


def gunluk_kaydet(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=GECMIS_ALAN)
    yeni = df[[c for c in GECMIS_ALAN if c in df.columns]].copy()
    yol = gecmis_yolu()
    if yol.exists():
        eski = pd.read_csv(yol)
        yeni = pd.concat([eski, yeni], ignore_index=True)
    yeni = yeni.drop_duplicates(["tarih", "sembol"], keep="last").sort_values(["tarih", "sembol"])
    tmp = yol.with_suffix(".tmp")
    yeni.to_csv(tmp, index=False)
    tmp.replace(yol)
    return yeni


def ileri_getiri(d: pd.DataFrame, tarih, giris: float | None, ufuklar=(5, 10, 20),
                 iptal: float | None = None, yon: str = "AL") -> dict:
    """`tarih` günü kapanışından sonraki k. barın getirisi (%)."""
    t = pd.Timestamp(tarih)
    idx = d.index
    if idx.tz is not None and t.tzinfo is None:
        t = t.tz_localize(idx.tz)
    pos = int(idx.searchsorted(t.normalize(), side="right")) - 1
    out: dict = {}
    if pos < 0:
        return out
    c = d["Close"].to_numpy()
    lo = d["Low"].to_numpy()
    hi = d["High"].to_numpy()
    g = float(giris) if giris else float(c[pos])
    for k in ufuklar:
        j = pos + k
        if j < len(c):
            out[f"g{k}"] = round((c[j] / g - 1) * 100, 2)
            if iptal is not None:
                seg = lo[pos + 1:j + 1] if yon == "AL" else hi[pos + 1:j + 1]
                out[f"iptal{k}"] = bool((seg < iptal).any()) if yon == "AL" else bool((seg > iptal).any())
    return out


def degerlendir(gecmis: pd.DataFrame, fiyat_getir, ufuklar=(5, 10, 20)) -> pd.DataFrame:
    """Her AL/SAT satırına ileri getiri ekle. `fiyat_getir(sembol) -> günlük df`."""
    if gecmis is None or gecmis.empty:
        return pd.DataFrame()
    rows = []
    sinyalli = gecmis[(gecmis["AL"] == "AL") | (gecmis["SAT"] == "SAT")]
    for sym, grp in sinyalli.groupby("sembol"):
        d = fiyat_getir(sym)
        if d is None or d.empty:
            continue
        for _, r in grp.iterrows():
            for yon in ("AL", "SAT"):
                if r.get(yon) != yon:
                    continue
                ip = r.get("iptal") if yon == "AL" else None
                ip = None if ip is None or pd.isna(ip) else float(ip)
                gt = ileri_getiri(d, r["tarih"], r.get("fiyat"), ufuklar, ip, yon)
                rows.append(dict(tarih=r["tarih"], sembol=sym, kural=r["kural"], yon=yon,
                                 tf=r.get(f"{yon}_TF"), vade=r.get(f"{yon}_vade"),
                                 fiyat=r.get("fiyat"), **gt))
    return pd.DataFrame(rows)


def ozet(deg: pd.DataFrame, ufuklar=(5, 10, 20)) -> pd.DataFrame:
    if deg is None or deg.empty:
        return pd.DataFrame()
    satir = []
    for (kural, yon), g in deg.groupby(["kural", "yon"]):
        s = dict(kural=kural, yon=yon, adet=len(g))
        for k in ufuklar:
            col = f"g{k}"
            if col not in g or g[col].notna().sum() == 0:
                s[f"isabet{k}%"] = None
                s[f"ort{k}%"] = None
                s[f"n{k}"] = 0
                continue
            v = g[col].dropna()
            hit = (v > 0) if yon == "AL" else (v < 0)
            s[f"n{k}"] = int(len(v))
            s[f"isabet{k}%"] = round(hit.mean() * 100, 1)
            s[f"ort{k}%"] = round(v.mean() if yon == "AL" else -v.mean(), 2)
        satir.append(s)
    return pd.DataFrame(satir).sort_values(["yon", "adet"], ascending=[True, False])
