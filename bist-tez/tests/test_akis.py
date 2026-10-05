"""Uçtan uca: sahte Yahoo → tara → CSV → günlük → skor; geri test; zamanlayıcı."""
import json

import pandas as pd
import pytest

from conftest import sentetik_gunluk, sentetik_saatlik
from engine import hacim, run, yahoo
from engine.config import _merge, evren
from engine.geritest import geri_test, geri_test_ozet
from engine.kart import csv_satiri, kart
from engine.skor import degerlendir, gecmis_yolu, ileri_getiri, ozet
from engine.zamanla import sonraki


@pytest.fixture
def sahte_yahoo(monkeypatch):
    def history(sym, interval, range_, **kw):
        if sym == "OLU.IS":
            return None
        seed = sum(map(ord, sym))
        return sentetik_gunluk(seed=seed) if interval == "1d" else sentetik_saatlik(seed=seed)
    monkeypatch.setattr(yahoo, "history", history)


def test_evren_normalize():
    assert evren({"evren_cekirdek": ["froto", "FROTO.IS", "thyao"], "evren_ek": None}) == \
        ["FROTO.IS", "THYAO.IS"]


def test_merge_varsayilan_korur():
    m = _merge({"a": {"x": 1, "y": 2}}, {"a": {"y": 3}})
    assert m == {"a": {"x": 1, "y": 3}}


def test_tara_uctan_uca(cfg, sahte_yahoo, tmp_data):
    cfg["evren_cekirdek"] = ["AAA", "BBB", "OLU"]
    cfg["evren_ek"] = []
    adimlar = []
    df = run.tara(progress=lambda i, n, s: adimlar.append(i), cfg=cfg)
    assert len(df) == 2
    assert sorted(adimlar) == [1, 2, 3]
    for c in ("kural", "AL", "SAT", "iptal", "gerekce", "proj_dist", "direnc"):
        assert c in df.columns
    assert (tmp_data / "sinyal.csv").exists()
    h = pd.read_csv(tmp_data / "hatalar.csv")
    assert h.sembol.tolist() == ["OLU"]
    assert json.loads((tmp_data / "meta.json").read_text())["hisse"] == 2
    assert gecmis_yolu().exists()
    # aynı gün tekrar tarama günlükte çoğaltmaz
    run.tara(cfg=cfg)
    assert len(pd.read_csv(gecmis_yolu())) == 2


def test_kart_alanlari(cfg):
    d = sentetik_gunluk(son_mesafe=0.01)
    rec = kart("TEST.IS", d, sentetik_saatlik(), cfg, kapali=True)
    assert rec["konum"] in ("uzun_alti", "orta_alti", "orta_ustu")
    assert rec["dom_tf"] in ("weekly", "daily", "4H", "1H")
    assert rec["cizgi_touch"] >= 4
    assert abs(rec["proj_dist"] - 1.0) < 3
    assert not any(k.startswith("_") for k in csv_satiri(rec))


def test_seans_rvol():
    h = sentetik_saatlik(gun=40)
    # son günün sadece ilk 3 saati, 2 kat hacimle
    son = h.index.normalize()[-1]
    h = h[(h.index.normalize() < son) | (h.index.hour < 13)].copy()
    h.loc[h.index.normalize() == son, "Volume"] *= 2
    r = hacim.seans_rvol(h)
    assert 1.6 < r < 2.4


def test_seans_kapali():
    t = pd.Timestamp("2026-10-05", tz="Europe/Istanbul")
    assert hacim.seans_kapali(t, t + pd.Timedelta(hours=18, minutes=30))
    assert not hacim.seans_kapali(t, t + pd.Timedelta(hours=13))
    assert hacim.seans_kapali(t - pd.Timedelta(days=1), t + pd.Timedelta(hours=13))


def test_ileri_getiri_ve_ozet():
    d = sentetik_gunluk(n=300)
    t = d.index[100]
    g = ileri_getiri(d, t.strftime("%Y-%m-%d"), None, (5, 10), iptal=0.0, yon="AL")
    beklenen = (d.Close.iloc[105] / d.Close.iloc[100] - 1) * 100
    assert g["g5"] == pytest.approx(beklenen, abs=0.01)
    assert g["iptal5"] is False

    gecmis = pd.DataFrame([dict(tarih=t.strftime("%Y-%m-%d"), sembol="X", fiyat=d.Close.iloc[100],
                                kural="K", AL="AL", AL_TF="daily", AL_vade="kisa", SAT="-",
                                iptal=None)])
    deg = degerlendir(gecmis, lambda s: d, (5, 10))
    oz = ozet(deg, (5, 10))
    assert oz.iloc[0]["adet"] == 1


def test_geri_test(cfg):
    d = sentetik_gunluk(n=700)
    sonuc = geri_test("TEST", d, cfg, adim=20, pencere=200)
    assert len(sonuc) > 0
    # geleceğe bakış yok: her satırın tarihi seriden
    assert set(sonuc.tarih) <= set(d.index.strftime("%Y-%m-%d"))
    oz = geri_test_ozet(sonuc)
    assert "kural" in oz.columns


def test_zamanlayici_sonraki():
    cuma_aksam = pd.Timestamp("2026-10-09 19:00", tz="Europe/Istanbul")
    t = sonraki(cuma_aksam, ["18:20"], [0, 1, 2, 3, 4])
    assert t == pd.Timestamp("2026-10-12 18:20", tz="Europe/Istanbul")
    ogle = pd.Timestamp("2026-10-06 12:00", tz="Europe/Istanbul")
    assert sonraki(ogle, ["18:20"], [0, 1, 2, 3, 4]).day == 6


def test_yahoo_parse_adjust():
    raw = {"chart": {"result": [{
        "timestamp": [1759730400, 1759816800, 1759816900],
        "indicators": {"quote": [{"open": [10, 11, 11], "high": [11, 12, 12], "low": [9, 10, 10],
                                  "close": [10, 12, 12.5], "volume": [100, None, 150]}],
                       "adjclose": [{"adjclose": [5, 6, 6.25]}]}}]}}
    df = yahoo.parse(raw, "1d", adjust=True)
    assert len(df) == 2                       # aynı güne düşen 2 satır tekilleşti
    assert df.Close.iloc[0] == pytest.approx(5)
    assert df.Close.iloc[-1] == pytest.approx(6.25)
    assert df.index.tz is not None
    assert yahoo.parse({"chart": {"result": None}}, "1d") is None


def test_grafik(cfg):
    from engine.grafik import ciz
    d = sentetik_gunluk()
    rec = kart("TEST.IS", d, None, cfg, kapali=True)
    fig = ciz(rec, d, bar=300)
    adlar = [t.name for t in fig.data]
    assert any("süper çizgi" in (a or "") for a in adlar)
