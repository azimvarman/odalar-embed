"""Mum grafik + Fib EMA şeridi + süper çizgi + yatay seviyeler + hacim (plotly)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .tech import ema

EMA_RENK = {8: "#f2c94c", 13: "#f2994a", 21: "#eb5757", 34: "#bb6bd9",
            55: "#2f80ed", 89: "#2d9cdb", 144: "#27ae60", 233: "#6fcf97"}


def ciz(rec: dict, d: pd.DataFrame, *, bar: int = 400, emalar=(21, 55, 89, 233),
        ileri: int = 15, baslik: str | None = None) -> go.Figure:
    n = len(d)
    bas = max(0, n - bar)
    v = d.iloc[bas:]
    x = v.index

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22],
                        vertical_spacing=0.02)
    fig.add_trace(go.Candlestick(x=x, open=v["Open"], high=v["High"], low=v["Low"],
                                 close=v["Close"], name="fiyat", showlegend=False), 1, 1)

    for span in emalar:
        e = ema(d["Close"], span).iloc[bas:]
        w = 2.4 if span == rec.get("ema_tap") else 1.1
        fig.add_trace(go.Scatter(x=x, y=e, mode="lines", name=f"EMA{span}",
                                 line=dict(width=w, color=EMA_RENK.get(span))), 1, 1)

    ray = rec.get("_isin")
    if ray:
        i_bas = max(ray["i0"], bas)
        idx = np.arange(i_bas, n)
        y = ray["intercept"] + ray["slope"] * idx
        gelecek = pd.bdate_range(d.index[-1] + pd.Timedelta(days=1), periods=ileri, tz=d.index.tz)
        y_ileri = ray["intercept"] + ray["slope"] * np.arange(n, n + ileri)
        renk = "#e74c3c" if ray.get("kirik") else "#16a085"
        fig.add_trace(go.Scatter(x=list(d.index[idx]) + list(gelecek),
                                 y=list(y) + list(y_ileri), mode="lines",
                                 name=f"süper çizgi ({ray['touches']} temas)",
                                 line=dict(color=renk, width=2.2, dash="solid")), 1, 1)
        tol = ray.get("tol", 0)
        fig.add_trace(go.Scatter(x=list(d.index[idx]) + list(gelecek),
                                 y=list(y - tol) + list(y_ileri - tol), mode="lines",
                                 name="tolerans", showlegend=False,
                                 line=dict(color=renk, width=0.8, dash="dot")), 1, 1)
        ti = [i for i in ray["touch_idx"] if i >= bas]
        if ti:
            fig.add_trace(go.Scatter(x=d.index[ti], y=d["Low"].iloc[ti], mode="markers",
                                     name="temas", marker=dict(size=9, color=renk,
                                                               symbol="circle-open", line=dict(width=2))), 1, 1)

    fiyat = float(d["Close"].iloc[-1])
    for s in rec.get("_seviyeler") or []:
        uzak = abs(s["seviye"] - fiyat) / fiyat
        if uzak > 0.25:
            continue
        renk = "rgba(39,174,96,0.55)" if s["seviye"] <= fiyat else "rgba(231,76,60,0.55)"
        fig.add_hline(y=s["seviye"], line=dict(color=renk, width=1, dash="dash"),
                      annotation_text=f"{s['seviye']:.2f} ×{s['touch']}",
                      annotation_position="right", row=1, col=1)

    for ad, renk in (("iptal", "#c0392b"), ("hedef", "#2980b9")):
        val = rec.get(ad)
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            fig.add_hline(y=val, line=dict(color=renk, width=1.5), annotation_text=ad,
                          annotation_position="left", row=1, col=1)

    renkler = np.where(v["Close"] >= v["Open"], "rgba(39,174,96,0.6)", "rgba(231,76,60,0.6)")
    fig.add_trace(go.Bar(x=x, y=v["Volume"], marker_color=renkler, name="hacim",
                         showlegend=False), 2, 1)
    sma = d["Volume"].rolling(20).mean().iloc[bas:]
    fig.add_trace(go.Scatter(x=x, y=sma, mode="lines", name="hacim SMA20",
                             line=dict(color="#7f8c8d", width=1)), 2, 1)

    fig.update_layout(height=680, margin=dict(l=10, r=70, t=40, b=10),
                      title=baslik or rec.get("sembol"), xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.02, x=0, font=dict(size=10)),
                      hovermode="x unified")
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig
