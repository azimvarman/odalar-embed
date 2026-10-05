"""Evren taraması: veri → kart → derleyici → data/sinyal.csv (+ geçmiş günlüğü)."""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from . import yahoo
from .config import data_dir, evren, load_rules
from .kart import csv_satiri, kart
from .skor import gunluk_kaydet

log = logging.getLogger("bist.run")


def veri(sym: str, cfg: dict, yenile: bool = False):
    v = cfg["veri"]
    kw = dict(cache_dk=v["cache_dk"], yenile=yenile, adjust=v["adjust"])
    d = yahoo.history(sym, "1d", v["gunluk_aralik"], **kw)
    h = yahoo.history(sym, "1h", v["saatlik_aralik"], **kw)
    return d, h


def gunluk(sym: str, cfg: dict | None = None, yenile: bool = False):
    cfg = cfg or load_rules()
    if not sym.endswith(".IS"):
        sym += ".IS"
    v = cfg["veri"]
    return yahoo.history(sym, "1d", v["gunluk_aralik"], cache_dk=v["cache_dk"],
                         yenile=yenile, adjust=v["adjust"])


def tek(sym: str, cfg: dict | None = None, yenile: bool = False):
    """Tek hisse için tam kart (grafik için alt çizgili alanlarla) + ham veri."""
    cfg = cfg or load_rules()
    if not sym.endswith(".IS"):
        sym += ".IS"
    d, h = veri(sym, cfg, yenile)
    if d is None or len(d) < cfg["veri"]["min_bar"]:
        raise ValueError(f"{sym}: yetersiz günlük veri ({0 if d is None else len(d)} bar)")
    return kart(sym, d, h, cfg), d, h


SIRA_AL = {"AL": 0, "YOK": 1, "-": 2}
SIRA_SAT = {"SAT": 0, "-": 1}


def sirala(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return (df.assign(_a=df["AL"].map(SIRA_AL).fillna(3), _s=df["SAT"].map(SIRA_SAT).fillna(2))
              .sort_values(["_a", "_s", "sembol"]).drop(columns=["_a", "_s"]))


def tara(progress=None, cfg: dict | None = None, yenile: bool = False,
         kaydet: bool = True) -> pd.DataFrame:
    cfg = cfg or load_rules()
    syms = evren(cfg)
    n = len(syms)
    rows, hatalar = [], []
    t0 = time.time()

    def is_(sym):
        rec, _, _ = tek(sym, cfg, yenile)
        return csv_satiri(rec)

    with ThreadPoolExecutor(max_workers=max(1, int(cfg["veri"]["paralel"]))) as ex:
        futs = {ex.submit(is_, s): s for s in syms}
        for i, f in enumerate(as_completed(futs), 1):
            sym = futs[f]
            try:
                rows.append(f.result())
            except Exception as e:
                log.warning("%s atlandı: %s", sym, e)
                hatalar.append(dict(sembol=sym.replace(".IS", ""), hata=str(e)[:200]))
            if progress:
                progress(i, n, sym.replace(".IS", ""))

    df = sirala(pd.DataFrame(rows))
    if kaydet:
        out = data_dir()
        tmp = out / "sinyal.tmp"
        df.to_csv(tmp, index=False)
        tmp.replace(out / "sinyal.csv")
        pd.DataFrame(hatalar, columns=["sembol", "hata"]).to_csv(out / "hatalar.csv", index=False)
        meta = dict(zaman=pd.Timestamp.now(tz="Europe/Istanbul").isoformat(timespec="seconds"),
                    sure_sn=round(time.time() - t0, 1), hisse=len(df), hata=len(hatalar),
                    evren=n)
        (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        gunluk_kaydet(df)
    return df
