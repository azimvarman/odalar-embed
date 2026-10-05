from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import yahoo  # noqa: E402
from engine.config import data_dir, load_rules  # noqa: E402
from engine.geritest import geri_test, geri_test_ozet  # noqa: E402
from engine.grafik import ciz  # noqa: E402
from engine.run import gunluk, tara, tek  # noqa: E402
from engine.skor import degerlendir, gecmis_yolu, ozet  # noqa: E402
from engine.tez import TFLER, YONLER, sinav  # noqa: E402

st.set_page_config(page_title="BIST Tez Paneli", layout="wide")
st.title("BIST tez paneli")
st.caption("Yatırım tavsiyesi değil. Yapı etiketi: AL/SAT + TF + vade. Tezini buradan sıkıştır.")

DATA = data_dir()
CSV = DATA / "sinyal.csv"
cfg = load_rules()

ANA_KOLON = ["sembol", "fiyat", "kural", "AL", "AL_TF", "AL_vade", "SAT", "SAT_TF", "SAT_vade",
             "iptal", "hedef", "rr", "risk", "konum", "dom_tf", "giris_tf", "ema_tap", "ema_tap_pct",
             "proj_dist", "cizgi_touch", "cizgi_kirik", "destek_dist", "direnc_dist",
             "rvol20", "rvol5", "rvol_seans", "hacim_ok"]


def oku() -> pd.DataFrame:
    if not CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(CSV)


def meta() -> dict:
    p = DATA / "meta.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def renk_al(v):
    return {"AL": "background-color:#d4efdf", "YOK": "background-color:#fdebd0"}.get(v, "")


def renk_sat(v):
    return "background-color:#f5b7b1" if v == "SAT" else ""


sekme = st.tabs(["📋 Tarama", "📈 Hisse", "🧪 Tez sınavı", "🎯 Skor kartı", "⏪ Geri test"])

# ---------------------------------------------------------------- Tarama
with sekme[0]:
    c1, c2, c3 = st.columns([1, 1, 3])
    run = c1.button("Evreni tara", type="primary")
    yenile = c2.checkbox("önbelleği yok say", help=f"Önbellek {cfg['veri']['cache_dk']} dk geçerli")
    m = meta()
    if m:
        c3.write(f"Son tarama: **{m.get('zaman', '?')}** · {m.get('hisse')} hisse · "
                 f"{m.get('hata')} hata · {m.get('sure_sn')} sn")
    if run:
        bar = st.progress(0.0, text="başlıyor")
        df = tara(progress=lambda i, n, s: bar.progress(i / n, text=f"{i}/{n} {s}"), yenile=yenile)
        bar.empty()
        st.success(f"{len(df)} hisse tarandı")
    df = oku()
    if df.empty:
        st.info("Önce tara. Seans sonu (18:15 sonrası) daha temiz rvol verir.")
    else:
        f1, f2, f3, f4, f5 = st.columns(5)
        al_f = f1.multiselect("AL", sorted(df["AL"].dropna().unique()))
        sat_f = f2.multiselect("SAT", sorted(df["SAT"].dropna().unique()))
        tf_f = f3.multiselect("dom TF", sorted(df["dom_tf"].dropna().unique()))
        k_f = f4.multiselect("kural", sorted(df["kural"].dropna().unique()))
        ara = f5.text_input("sembol ara").strip().upper()
        view = df.copy()
        if al_f:
            view = view[view.AL.isin(al_f)]
        if sat_f:
            view = view[view.SAT.isin(sat_f)]
        if tf_f:
            view = view[view.dom_tf.isin(tf_f)]
        if k_f:
            view = view[view.kural.isin(k_f)]
        if ara:
            view = view[view.sembol.str.contains(ara)]

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("satır", len(view))
        m2.metric("AL", int((view.AL == "AL").sum()))
        m3.metric("SAT", int((view.SAT == "SAT").sum()))
        m4.metric("hacimsiz yapı", int((view.AL == "YOK").sum()))
        m5.metric("çakışma", int((view.cakisma == "evet").sum()))

        tum = st.toggle("tüm kolonlar", value=False)
        goster = view if tum else view[[c for c in ANA_KOLON if c in view.columns]]
        st.dataframe(goster.style.map(renk_al, subset=["AL"]).map(renk_sat, subset=["SAT"]),
                     width="stretch", hide_index=True, height=560)
        st.download_button("CSV indir", view.to_csv(index=False).encode("utf-8"),
                           "sinyal.csv", "text/csv")
        hp = DATA / "hatalar.csv"
        if hp.exists():
            h = pd.read_csv(hp)
            if len(h):
                with st.expander(f"Atlanan hisseler ({len(h)})"):
                    st.dataframe(h, hide_index=True)

# ---------------------------------------------------------------- Hisse
with sekme[1]:
    df = oku()
    liste = sorted(df.sembol.tolist()) if len(df) else []
    a1, a2, a3 = st.columns([1, 1, 2])
    secim = a1.selectbox("Hisse", [""] + liste, key="hisse_sec")
    elle = a2.text_input("veya sembol yaz", key="hisse_elle").strip().upper()
    sym = elle or secim
    bar_n = a3.slider("gösterilecek bar", 120, 1250, 400, step=20)
    emalar = st.multiselect("EMA şeridi", [8, 13, 21, 34, 55, 89, 144, 233],
                            default=[21, 55, 89, 233])
    if sym:
        try:
            with st.spinner(f"{sym} hesaplanıyor"):
                rec, d, h = tek(sym, cfg)
            st.plotly_chart(ciz(rec, d, bar=bar_n, emalar=emalar,
                                baslik=f"{rec['sembol']} — {rec['kural']} · AL {rec['AL']} {rec['AL_TF']} "
                                       f"{rec['AL_vade']} · SAT {rec['SAT']} {rec['SAT_TF']}"),
                            width="stretch")
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("fiyat", rec["fiyat"])
            k2.metric("konum", rec["konum"])
            k3.metric("dom TF → giriş", f"{rec['dom_tf']} → {rec['giris_tf']}")
            k4.metric(f"tap EMA{rec['ema_tap']}", f"%{rec['ema_tap_pct']}", f"{rec['ema_tap_olay']} olay")
            k5.metric("ışın mesafe", "-" if rec["proj_dist"] is None else f"%{rec['proj_dist']}",
                      "KIRIK" if rec["cizgi_kirik"] else None, delta_color="inverse")
            k6.metric("rvol20", rec["rvol20"], rec["hacim_neden"], delta_color="off")
            st.markdown("**Gerekçe:** " + rec["gerekce"].replace(" | ", " · "))
            if rec["risk"]:
                st.warning("Risk: " + rec["risk"])
            with st.expander("Kart (tüm alanlar)"):
                st.json({k: v for k, v in rec.items() if not k.startswith("_")})
            with st.expander("Fib EMA saygı tablosu (olay, %)"):
                st.dataframe(pd.DataFrame(
                    [dict(span=k, olay=v[0], saygi=v[1]) for k, v in rec["_tap_tablo"].items()]),
                    hide_index=True)
            if h is not None and len(h):
                with st.expander("1H grafik"):
                    st.plotly_chart(ciz(dict(sembol=rec["sembol"]), h, bar=300, emalar=emalar,
                                        baslik=f"{rec['sembol']} 1H"), width="stretch")
        except Exception as e:
            st.error(f"{sym}: {e}")

# ---------------------------------------------------------------- Tez
with sekme[2]:
    df = oku()
    if df.empty:
        st.info("Önce tara.")
    else:
        t1, t2, t3 = st.columns([1, 2, 2])
        tez_hisse = t1.selectbox("Hisse", [""] + sorted(df.sembol.tolist()), key="tez_hisse")
        tez_yon = t2.radio("Tez", YONLER, horizontal=True)
        tez_tf = t3.radio("Tez TF", TFLER, horizontal=True, index=1)
        if tez_hisse:
            r = df[df.sembol == tez_hisse].iloc[0].to_dict()
            sonuc, nedenler = sinav(r, tez_yon, tez_tf)
            renk = {"tutuyor": "green", "kısmen": "orange", "tutmuyor": "red"}[sonuc]
            st.markdown(f"### {tez_hisse} “{tez_tf} {tez_yon}” → :{renk}[**{sonuc}**]")
            for n in nedenler:
                st.write("•", n)
            if r.get("iptal") == r.get("iptal"):  # NaN değilse
                st.write(f"• iptal: 2 kapanış **{r['iptal']}** altı · hedef: {r.get('hedef')} · R/R: {r.get('rr')}")
            if r.get("risk") == r.get("risk") and r.get("risk"):
                st.warning("Risk: " + str(r["risk"]))
            st.caption("Gerekçe: " + str(r.get("gerekce", "")))

# ---------------------------------------------------------------- Skor
with sekme[3]:
    st.write("Her tarama `data/gecmis.csv`'ye yazılır. Burada geçmiş etiketlerin 5/10/20 bar "
             "sonraki getirisi ölçülür — kuralların sende ne kadar tuttuğunu gör.")
    if not gecmis_yolu().exists():
        st.info("Henüz günlük yok. Birkaç gün tara (veya zamanlayıcı çalışsın).")
    elif st.button("Skor kartını hesapla"):
        gecmis = pd.read_csv(gecmis_yolu())
        uf = cfg["skor"]["ufuklar"]
        def fiyat_getir(s):
            d = yahoo.cached(f"{s}.IS", "1d", cfg["veri"]["gunluk_aralik"])
            return d if d is not None else gunluk(s, cfg)

        with st.spinner("ileri getiriler"):
            deg = degerlendir(gecmis, fiyat_getir, uf)
        if deg.empty:
            st.info("Değerlendirilecek AL/SAT yok.")
        else:
            st.subheader("Kural bazında isabet")
            st.dataframe(ozet(deg, uf), hide_index=True, width="stretch")
            st.subheader("Tek tek etiketler")
            st.dataframe(deg.sort_values("tarih", ascending=False), hide_index=True, width="stretch")

# ---------------------------------------------------------------- Geri test
with sekme[4]:
    st.write("Walk-forward: geçmişte her N barda yalnız o güne kadarki veriyle kart üretilir, "
             "etiketin sonraki getirisi ölçülür. 1H kuralları dahil değil.")
    g1, g2, g3 = st.columns(3)
    df = oku()
    gs = g1.selectbox("Hisse", [""] + (sorted(df.sembol.tolist()) if len(df) else []), key="gt_hisse")
    adim = g2.number_input("adım (bar)", 1, 20, 5)
    pencere = g3.number_input("pencere (bar)", 100, 1000, 500, step=50)
    if gs and st.button("Geri testi çalıştır"):
        d = gunluk(gs, cfg)
        if d is None:
            st.error("veri yok")
        else:
            pb = st.progress(0.0)
            sonuc = geri_test(gs, d, cfg, adim=int(adim), pencere=int(pencere),
                              ufuklar=cfg["skor"]["ufuklar"],
                              progress=lambda i, n: pb.progress(i / n))
            pb.empty()
            st.subheader("Özet (taban = etiketsiz günler)")
            st.dataframe(geri_test_ozet(sonuc, cfg["skor"]["ufuklar"]), hide_index=True, width="stretch")
            with st.expander("Tüm adımlar"):
                st.dataframe(sonuc, hide_index=True, width="stretch")

st.caption("Kaynak: Yahoo finance chart API (gecikmeli, düzeltmeli). Eğitim / kişisel tez aracı.")
