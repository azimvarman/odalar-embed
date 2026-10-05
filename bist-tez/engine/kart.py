"""Karakter kartı: bir hissenin tek satırlık teknik kimliği.

Alt çizgiyle başlayan anahtarlar (`_isin`, `_seviyeler`...) CSV'ye yazılmaz;
grafik ve derleyici için taşınır.
"""
from __future__ import annotations

import pandas as pd

from . import hacim, tech
from .derleyici import derle, sinyal
from .seviye import en_yakin, yatay_seviyeler

GIRIS_TF = {"weekly": "daily", "daily": "4H", "4H": "1H", "1H": "1H"}


def _r(x, n=2):
    return None if x is None else round(float(x), n)


def kart(sym: str, d: pd.DataFrame, h: pd.DataFrame | None, cfg: dict, *,
         kapali: bool | None = None) -> dict:
    c = d["Close"]
    last = float(c.iloc[-1])
    a = tech.atr(d)
    atr_last = float(a.iloc[-1])
    if kapali is None:
        kapali = hacim.seans_kapali(d.index[-1])

    # --- konum: Fib şeridine göre
    e89 = float(tech.ema(c, 89).iloc[-1])
    e233 = float(tech.ema(c, 233).iloc[-1])
    konum = "uzun_alti" if last < e233 else ("orta_alti" if last < e89 else "orta_ustu")

    # --- dominant TF
    scores = {"weekly": tech.tf_quality(tech.weekly(d))["score"],
              "daily": tech.tf_quality(d)["score"]}
    near, h1_iptal, rvol_seans = "", None, None
    if h is not None and len(h) > 80:
        scores["4H"] = tech.tf_quality(tech.h4(h))["score"]
        scores["1H"] = tech.tf_quality(h, 80, 160)["score"]
        ah = float(tech.atr(h).iloc[-1])
        hc = h["Close"]
        hl = float(hc.iloc[-1])
        ne = tech.ema_near(hc, hl, ah, cfg["ema"]["yakin_atr"])
        near = ",".join(str(x) for x in ne)
        derin = [n for n in ne if n in (89, 144, 233)]
        if derin:
            h1_iptal = float(tech.ema(hc, max(derin)).iloc[-1]) - cfg["risk"]["iptal_atr"] * ah
        if not kapali:
            rvol_seans = hacim.seans_rvol(h)
    dom = max(scores, key=scores.get)

    # --- hisseye özel tap EMA
    e = cfg["ema"]
    tap = tech.ema_saygi(c, a, tol=e["tap_tol_atr"], ileri=e["ileri_bar"], min_olay=e["min_olay"])
    tap_deger = float(tech.ema(c, tap["span"]).iloc[-1])

    # --- süper çizgi
    ic = cfg["isin"]
    ray = tech.destek_isini(d, atr_last, tol_atr=ic["tol_atr"], min_aralik=ic["min_aralik"],
                            min_touch=ic["min_touch"], dist_min=ic["dist_min"],
                            dist_max=ic["dist_max"], kirik_bar=ic["kirik_bar"])

    # --- yatay seviyeler
    sc = cfg["seviye"]
    sev = yatay_seviyeler(d, atr_last, order=sc["order"], tol_atr=sc["tol_atr"],
                          min_touch=sc["min_touch"], lookback=sc["lookback"])
    destek, direnc = en_yakin(sev, last)

    # --- hacim
    rvol20, rvol5 = hacim.gunluk_rvol(d, kapali)
    ray_rvol = ray.get("ray_rvol") if ray else None
    h_ok, h_neden = hacim.hacim_ok(rvol20, rvol5, ray_rvol, rvol_seans, cfg)

    rec = dict(
        sembol=sym.replace(".IS", ""),
        tarih=d.index[-1].strftime("%Y-%m-%d"),
        fiyat=round(last, 3),
        atr=round(atr_last, 3),
        konum=konum,
        dom_tf=dom,
        giris_tf=GIRIS_TF.get(dom, "daily"),
        tf_skor=" ".join(f"{k}:{v:.0f}" for k, v in scores.items()),
        ema_tap=tap["span"],
        ema_tap_pct=round(tap["oran"], 1),
        ema_tap_olay=tap["olay"],
        ema_tap_deger=round(tap_deger, 3),
        proj_now=None if not ray else round(ray["now"], 3),
        proj_dist=None if not ray else round(ray["dist"], 2),
        cizgi_touch=None if not ray else ray["touches"],
        cizgi_ihlal=None if not ray else ray["viol"],
        cizgi_kirik=bool(ray["kirik"]) if ray else False,
        cizgi_orijin=None if not ray else d.index[ray["i0"]].strftime("%Y-%m-%d"),
        destek=None if not destek else round(destek["seviye"], 3),
        destek_dist=None if not destek else round((last - destek["seviye"]) / last * 100, 2),
        direnc=None if not direnc else round(direnc["seviye"], 3),
        direnc_dist=None if not direnc else round((direnc["seviye"] - last) / last * 100, 2),
        direnc_touch=None if not direnc else direnc["touch"],
        h1_ema_near=near,
        rvol20=_r(rvol20),
        rvol5=_r(rvol5),
        rvol_seans=_r(rvol_seans),
        hacim_ok=h_ok,
        hacim_neden=h_neden,
        seans="kapalı" if kapali else "açık",
        _isin=ray,
        _seviyeler=sev,
        _h1_iptal=h1_iptal,
        _tap_tablo=tap["tablo"],
    )
    kural, gerekce = derle(rec, cfg)
    rec["kural"] = kural
    rec.update(sinyal(rec, cfg, gerekce))
    return rec


def csv_satiri(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if not k.startswith("_")}
