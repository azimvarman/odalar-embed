"""Walk-forward geri test.

Geçmişte her `adim` barda yalnızca o güne kadarki veriyle kart + derleyici çalışır,
etiketin sonraki 5/10/20 bar getirisi ölçülür. Geleceğe bakış yok: pivot, ışın,
EMA ve hacim kesilmiş seriden hesaplanır.

Sınır: 1H veri Yahoo'da yalnız ~2 yıl olduğundan `1H_EMA_YIGIN` ve seans rvol
geri testte yer almaz (yalnız daily/weekly kurallar).
"""
from __future__ import annotations

import pandas as pd

from .kart import kart
from .skor import ileri_getiri, ozet


def geri_test(sym: str, d: pd.DataFrame, cfg: dict, *, adim: int = 5, pencere: int = 500,
              ufuklar=(5, 10, 20), min_bar: int = 260, progress=None) -> pd.DataFrame:
    n = len(d)
    bas = max(min_bar, n - pencere)
    adimlar = list(range(bas, n - 1, adim))
    rows = []
    for j, t in enumerate(adimlar):
        if progress:
            progress(j + 1, len(adimlar))
        sub = d.iloc[:t + 1]
        try:
            r = kart(sym, sub, None, cfg, kapali=True)
        except Exception:
            continue
        base = dict(tarih=r["tarih"], sembol=r["sembol"], fiyat=r["fiyat"], kural=r["kural"],
                    konum=r["konum"], dom_tf=r["dom_tf"], AL=r["AL"], SAT=r["SAT"])
        for yon in ("AL", "SAT"):
            if r[yon] != yon:
                continue
            ip = r.get("iptal") if yon == "AL" else r.get("sat_iptal")
            gt = ileri_getiri(d, r["tarih"], r["fiyat"], ufuklar, ip, yon)
            rows.append(dict(base, yon=yon, tf=r[f"{yon}_TF"], vade=r[f"{yon}_vade"], **gt))
        if r["AL"] != "AL" and r["SAT"] != "SAT":
            rows.append(dict(base, yon="-", tf="-", vade="-",
                             **ileri_getiri(d, r["tarih"], r["fiyat"], ufuklar)))
    return pd.DataFrame(rows)


def geri_test_ozet(sonuc: pd.DataFrame, ufuklar=(5, 10, 20)) -> pd.DataFrame:
    """Sinyalli satırların özeti + kıyas için 'etiketsiz' satırların ortalaması."""
    if sonuc is None or sonuc.empty:
        return pd.DataFrame()
    sin = sonuc[sonuc["yon"].isin(["AL", "SAT"])]
    oz = ozet(sin, ufuklar)
    taban = sonuc[sonuc["yon"] == "-"]
    if len(taban):
        s = dict(kural="(etiketsiz taban)", yon="-", adet=len(taban))
        for k in ufuklar:
            v = taban.get(f"g{k}", pd.Series(dtype=float)).dropna()
            s[f"n{k}"] = int(len(v))
            s[f"isabet{k}%"] = round((v > 0).mean() * 100, 1) if len(v) else None
            s[f"ort{k}%"] = round(v.mean(), 2) if len(v) else None
        oz = pd.concat([oz, pd.DataFrame([s])], ignore_index=True)
    return oz
