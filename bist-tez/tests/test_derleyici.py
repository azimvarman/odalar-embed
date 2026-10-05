import pytest

from engine.derleyici import derle, sinyal


def kart(**kw):
    base = dict(sembol="TEST", fiyat=100.0, atr=2.0, konum="orta_ustu", dom_tf="daily",
                ema_tap=21, ema_tap_pct=50.0, ema_tap_deger=98.0, proj_now=None,
                proj_dist=None, cizgi_touch=None, cizgi_kirik=False, h1_ema_near="",
                hacim_ok=True, hacim_neden="test", direnc=110.0, direnc_dist=10.0,
                seans="kapalı")
    base.update(kw)
    return base


def calistir(cfg, **kw):
    r = kart(**kw)
    r["kural"], g = derle(r, cfg)
    r.update(sinyal(r, cfg, g))
    return r


def test_tepki_zone(cfg):
    r = calistir(cfg, konum="uzun_alti", proj_dist=2.0, proj_now=98.0, cizgi_touch=5)
    assert r["kural"] == "TEPKI_ZONE"
    assert (r["AL"], r["AL_TF"], r["AL_vade"]) == ("AL", "daily", "kisa")
    assert r["iptal"] == pytest.approx(98.0 - 2.0 * 0.55)


def test_tepki_gevsek(cfg):
    r = calistir(cfg, konum="uzun_alti", proj_dist=-5.0, proj_now=105.0, cizgi_touch=6)
    assert r["kural"] == "TEPKI_ZONE_GEVSEK"
    # dist -5 → ışının altında → SAT da var → çakışma
    assert r["SAT"] == "SAT" and r["cakisma"] == "evet"


def test_kirik_isin_tepkiyi_iptal_eder_ve_sat_yazar(cfg):
    r = calistir(cfg, konum="uzun_alti", proj_dist=-2.0, proj_now=102.0, cizgi_touch=5,
                 cizgi_kirik=True)
    assert r["kural"] != "TEPKI_ZONE"
    assert r["SAT"] == "SAT" and r["SAT_TF"] == "daily"
    assert r["sat_iptal"] == pytest.approx(102.0 + 1.1)


def test_trend_haftalik(cfg):
    r = calistir(cfg, dom_tf="weekly", ema_tap_pct=60)
    assert r["kural"] == "TREND_HAFTALIK"
    assert (r["AL_TF"], r["AL_vade"]) == ("weekly", "uzun")


def test_trend_daily_isin_ve_rr(cfg):
    r = calistir(cfg, ema_tap_pct=60, proj_dist=2.0, proj_now=98.0, cizgi_touch=4)
    assert r["kural"] == "TREND_DAILY_ISIN"
    assert r["AL_vade"] == "orta"
    assert r["hedef"] == 110.0
    assert r["rr"] == pytest.approx((110 - 100) / (100 - r["iptal"]), abs=0.01)


def test_trend_ema_sade(cfg):
    r = calistir(cfg, ema_tap_pct=60)
    assert r["kural"] == "TREND_EMA_SADE"


def test_1h_yigin(cfg):
    r = calistir(cfg, h1_ema_near="21,89,144")
    assert r["kural"] == "1H_EMA_YIGIN" and r["AL_TF"] == "1H/4H"


def test_hacim_veto(cfg):
    r = calistir(cfg, dom_tf="weekly", ema_tap_pct=60, hacim_ok=False)
    assert r["AL"] == "YOK"
    assert "hacim" in r["gerekce"]


def test_izle(cfg):
    r = calistir(cfg)
    assert r["kural"] == "IZLE" and r["AL"] == "-" and r["SAT"] == "-"


def test_sat_haftalik(cfg):
    r = calistir(cfg, konum="uzun_alti", dom_tf="weekly")
    assert (r["SAT"], r["SAT_TF"], r["SAT_vade"]) == ("SAT", "weekly", "uzun")


def test_direnc_yakin_risk(cfg):
    r = calistir(cfg, ema_tap_pct=60, direnc=101.0, direnc_dist=1.0)
    assert "direnç" in r["risk"]


def test_nan_mesafe_guvenli(cfg):
    r = calistir(cfg, konum="uzun_alti", proj_dist=float("nan"), cizgi_touch=float("nan"))
    assert r["kural"] == "IZLE"
