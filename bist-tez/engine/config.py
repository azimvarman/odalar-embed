"""Yol ve kural ayarları.

`rules/sablon.yaml` eksik alan içerse bile motor çalışsın diye her eşik burada
varsayılanla tanımlı; YAML yalnızca üzerine yazar.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("BIST_DATA", ROOT / "data"))
RULES = Path(os.environ.get("BIST_RULES", ROOT / "rules" / "sablon.yaml"))
TZ = "Europe/Istanbul"

DEFAULTS: dict = {
    "evren_cekirdek": [],
    "evren_ek": [],
    "veri": {
        "gunluk_aralik": "5y",
        "saatlik_aralik": "730d",
        "cache_dk": 30,          # aynı gün içinde tekrar taramada Yahoo'ya gitme
        "paralel": 4,            # eşzamanlı istek; Yahoo 429 verirse düşür
        "adjust": True,          # temettü/split düzeltmeli fiyat (adjclose)
        "min_bar": 260,
    },
    "hacim": {
        "rvol20_min": 1.10,
        "rvol5_min": 1.05,
        "ray_rvol_min": 1.15,
        "ray_rvol_gun_min": 0.85,
        "seans_rvol_min": 1.10,  # seans açıkken saat profiline göre rvol
    },
    "tepki": {
        "dist_sik": 3.0,
        "dist_gevsek": 5.5,
        "min_touch": 4,
        "min_touch_gevsek": 6,
    },
    "trend": {
        "tap_min": 57,
        "isin_dist": 3.5,
    },
    "sat": {
        "dist_max": -5.0,
    },
    "isin": {
        "tol_atr": 0.55,
        "min_aralik": 40,
        "min_touch": 3,
        "dist_min": -10.0,
        "dist_max": 40.0,
        "kirik_bar": 2,          # kaç kapanış altında kalırsa ışın "kırık"
    },
    "ema": {
        "tap_tol_atr": 0.45,
        "ileri_bar": 5,
        "min_olay": 30,
        "yakin_atr": 0.5,
    },
    "seviye": {
        "order": 5,
        "tol_atr": 0.6,
        "min_touch": 3,
        "lookback": 500,
    },
    "risk": {
        "direnc_yakin": 2.0,     # % — AL var ama tavan bu kadar yakınsa uyar
        "iptal_atr": 0.5,
    },
    "zamanlama": {
        "saatler": ["18:20"],
        "gunler": [0, 1, 2, 3, 4],
    },
    "skor": {
        "ufuklar": [5, 10, 20],
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_rules(path: Path | str | None = None) -> dict:
    p = Path(path) if path else RULES
    raw = {}
    if p.exists():
        with open(p, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    return _merge(DEFAULTS, raw)


def evren(cfg: dict) -> list[str]:
    syms = list(cfg.get("evren_cekirdek") or []) + list(cfg.get("evren_ek") or [])
    out, seen = [], set()
    for s in syms:
        s = str(s).strip().upper()
        if not s:
            continue
        if not s.endswith(".IS"):
            s += ".IS"
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def data_dir() -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    return DATA
