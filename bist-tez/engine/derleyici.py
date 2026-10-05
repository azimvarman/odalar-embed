"""Kural derleyici: karakter kartı → kural → AL/SAT (+TF, vade, iptal, hedef, gerekçe).

Sıra önemlidir: ilk eşleşen kural kazanır. Eşikler `rules/sablon.yaml`'dan gelir.
"""
from __future__ import annotations

import math


def _num(x, default=None):
    if x is None:
        return default
    try:
        f = float(x)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(f) else f


def derle(rec: dict, cfg: dict) -> tuple[str, list[str]]:
    konum = rec["konum"]
    dist_raw = _num(rec.get("proj_dist"))
    dist = abs(dist_raw) if dist_raw is not None else 99.0
    tap = _num(rec.get("ema_tap_pct"), 0.0)
    touch = int(_num(rec.get("cizgi_touch"), 0))
    kirik = bool(rec.get("cizgi_kirik"))
    near = [x for x in str(rec.get("h1_ema_near") or "").split(",") if x]
    t, tr = cfg["tepki"], cfg["trend"]
    g: list[str] = []

    if konum == "uzun_alti" and not kirik:
        if dist <= t["dist_sik"] and touch >= t["min_touch"]:
            g.append(f"EMA233 altı, ışına %{dist:.1f} yakın, {touch} temas → tepki bölgesi")
            return "TEPKI_ZONE", g
        if dist <= t["dist_gevsek"] and touch >= t["min_touch_gevsek"]:
            g.append(f"EMA233 altı, ışına %{dist:.1f} (geniş zone), {touch} temas")
            return "TEPKI_ZONE_GEVSEK", g
    if konum == "uzun_alti" and kirik and dist <= t["dist_gevsek"]:
        g.append("ışın son kapanışlarda kırıldı — tepki kuralı iptal")

    if konum in ("orta_ustu", "orta_alti") and rec.get("dom_tf") == "weekly" and tap >= tr["tap_min"]:
        g.append(f"haftalık rejim baskın, EMA{rec.get('ema_tap')} saygı %{tap:.0f}")
        return "TREND_HAFTALIK", g
    if konum == "orta_ustu" and tap >= tr["tap_min"] and dist <= tr["isin_dist"] and not kirik:
        g.append(f"EMA89 üstü, EMA{rec.get('ema_tap')} saygı %{tap:.0f}, ışın %{dist:.1f} altta")
        return "TREND_DAILY_ISIN", g
    if konum == "orta_ustu" and tap >= tr["tap_min"]:
        g.append(f"EMA89 üstü, EMA{rec.get('ema_tap')} saygı %{tap:.0f} (ışın uzak/yok)")
        return "TREND_EMA_SADE", g
    derin = [x for x in near if x in ("89", "144", "233")]
    if derin:
        g.append(f"1H fiyat EMA{'/'.join(derin)} üzerinde yığılmış")
        return "1H_EMA_YIGIN", g
    g.append("tanımlı kurulum yok")
    return "IZLE", g


AL_HARITA = {
    "TREND_HAFTALIK": ("weekly", "uzun"),
    "TREND_DAILY_ISIN": ("daily", "orta"),
    "TEPKI_ZONE": ("daily", "kisa"),
    "TEPKI_ZONE_GEVSEK": ("daily", "kisa"),
    "TREND_EMA_SADE": ("daily", "kisa"),
    "1H_EMA_YIGIN": ("1H/4H", "kisa"),
}


def _al_iptal(rec: dict, kural: str, cfg: dict) -> float | None:
    atr = _num(rec.get("atr"), 0.0)
    k = cfg["risk"]["iptal_atr"]
    tol = atr * cfg["isin"]["tol_atr"]
    if kural in ("TEPKI_ZONE", "TEPKI_ZONE_GEVSEK", "TREND_DAILY_ISIN"):
        pn = _num(rec.get("proj_now"))
        if pn is not None:
            return pn - tol
    if kural in ("TREND_HAFTALIK", "TREND_EMA_SADE", "TREND_DAILY_ISIN"):
        ev = _num(rec.get("ema_tap_deger"))
        if ev is not None:
            return ev - k * atr
    if kural == "1H_EMA_YIGIN":
        return _num(rec.get("_h1_iptal"))
    return None


def sinyal(rec: dict, cfg: dict, gerekce: list[str] | None = None) -> dict:
    kural = rec["kural"]
    ok = bool(rec.get("hacim_ok"))
    konum = rec["konum"]
    dist = _num(rec.get("proj_dist"))
    fiyat = _num(rec.get("fiyat"), 0.0)
    g = list(gerekce or [])
    risk: list[str] = []

    al = sat = "-"
    al_tf = sat_tf = al_vade = sat_vade = "-"
    iptal = hedef = rr = sat_iptal = None

    if kural in AL_HARITA:
        if ok:
            al = "AL"
            al_tf, al_vade = AL_HARITA[kural]
            iptal = _al_iptal(rec, kural, cfg)
            hedef = _num(rec.get("direnc"))
            if iptal is not None and hedef is not None and fiyat > iptal:
                rr = (hedef - fiyat) / (fiyat - iptal)
            g.append(f"hacim ✓ ({rec.get('hacim_neden', '')})")
        else:
            al = "YOK"
            g.append("yapı var ama hacim teyidi yok → AL yazılmaz")

    sc = cfg["sat"]
    if rec.get("cizgi_kirik"):
        sat, sat_tf, sat_vade = "SAT", "daily", "kisa"
        pn = _num(rec.get("proj_now"))
        if pn is not None:
            sat_iptal = pn + _num(rec.get("atr"), 0.0) * cfg["isin"]["tol_atr"]
        g.append(f"süper çizgi {cfg['isin']['kirik_bar']} kapanıştır altında → kırılım")
    elif konum == "uzun_alti" and dist is not None and dist <= sc["dist_max"]:
        sat, sat_tf, sat_vade = "SAT", "daily", "kisa"
        g.append(f"EMA233 altı ve ışının %{abs(dist):.1f} altında")
    elif konum == "uzun_alti" and rec.get("dom_tf") == "weekly":
        sat, sat_tf, sat_vade = "SAT", "weekly", "uzun"
        g.append("EMA233 altı ve haftalık rejim baskın → uzun vadeli zayıflık")

    dd = _num(rec.get("direnc_dist"))
    if al == "AL" and dd is not None and dd < cfg["risk"]["direnc_yakin"]:
        risk.append(f"direnç %{dd:.1f} yakında")
    if al == "AL" and rr is not None and rr < 1:
        risk.append(f"R/R {rr:.2f} < 1")
    if rec.get("seans") == "açık":
        risk.append("seans açık — günlük bar kesinleşmedi")
    cakisma = al == "AL" and sat == "SAT"
    if cakisma:
        risk.append("AL+SAT çakışması")

    return dict(
        AL=al, AL_TF=al_tf, AL_vade=al_vade,
        SAT=sat, SAT_TF=sat_tf, SAT_vade=sat_vade,
        cakisma="evet" if cakisma else "hayir",
        iptal=None if iptal is None else round(iptal, 3),
        hedef=None if hedef is None else round(hedef, 3),
        rr=None if rr is None else round(rr, 2),
        sat_iptal=None if sat_iptal is None else round(sat_iptal, 3),
        risk="; ".join(risk),
        gerekce=" | ".join(g),
    )
