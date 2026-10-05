"""Tez sınavı: kullanıcının cümlesi (hisse + yön + TF) etiketlere karşı.

Sonuç: tutuyor / kısmen / tutmuyor + neden listesi. Motor "al" demez.
"""
from __future__ import annotations

import math

YONLER = ("çıkacak", "dönecek", "kırılacak / düşecek")
TFLER = ("weekly", "daily", "1H/4H")
_SIRA = {"1H/4H": 0, "1H": 0, "4H": 0, "daily": 1, "weekly": 2}


def _v(r, k, d=None):
    v = r.get(k, d) if hasattr(r, "get") else d
    if isinstance(v, float) and math.isnan(v):
        return d
    return v


def _tf_eslesir(etiket_tf: str, tez_tf: str) -> bool:
    return str(etiket_tf) == tez_tf or (tez_tf == "1H/4H" and str(etiket_tf) in ("1H", "4H", "1H/4H"))


def sinav(r, yon: str, tf: str) -> tuple[str, list[str]]:
    al, sat = _v(r, "AL", "-"), _v(r, "SAT", "-")
    al_tf, al_vade = _v(r, "AL_TF", "-"), _v(r, "AL_vade", "-")
    sat_tf = _v(r, "SAT_TF", "-")
    kural = str(_v(r, "kural", "IZLE"))
    kirik = str(_v(r, "cizgi_kirik", False)).lower() in ("true", "1", "evet")
    cakisma = _v(r, "cakisma") == "evet"
    n: list[str] = [f"kural: {kural}", f"AL: {al} {al_tf} {al_vade} · SAT: {sat} {sat_tf}"]

    if yon == "çıkacak":
        if cakisma:
            return "tutmuyor", n + ["aynı satırda AL ve SAT var — 'çıkacak' onaylanmaz"]
        if sat == "SAT" and _SIRA.get(sat_tf, 1) >= _SIRA.get(tf, 1):
            return "tutmuyor", n + [f"{sat_tf} SAT etiketi tezin TF'sini kapsıyor"]
        if al == "AL":
            if al_vade == "uzun" and tf == "weekly":
                return "tutuyor", n + ["haftalık uzun AL — tez ile aynı TF"]
            if al_vade == "orta" and tf == "daily":
                return "tutuyor", n + ["daily orta vadeli AL — tez ile aynı TF"]
            if al_vade == "uzun" and tf == "daily":
                return "kısmen", n + ["trend haftalık; daily çıkış için giriş TF'sinde teyit bekle"]
            if al_vade == "orta" and tf == "weekly":
                return "kısmen", n + ["daily trend var ama haftalık rejim onaylamıyor"]
            if al_vade == "kisa":
                return "kısmen", n + ["bu AL kısa tepki etiketi — uzun çıkış değil"]
            return "kısmen", n + ["AL var ama TF tezle uyuşmuyor"]
        if al == "YOK":
            return "tutmuyor", n + ["yapı var, hacim teyidi yok"]
        if sat == "SAT":
            return "kısmen", n + [f"AL yok; {sat_tf} SAT var ama tezden kısa TF'de"]
        return "tutmuyor", n + ["AL etiketi yok"]

    if yon == "dönecek":
        if kirik:
            return "tutmuyor", n + ["süper çizgi kırık — dönüş bölgesi geçersiz"]
        if kural.startswith("TEPKI") and al == "AL":
            return "tutuyor", n + ["fiyat süper çizgi tepki bölgesinde, hacim teyitli"]
        if kural.startswith("TEPKI"):
            return "kısmen", n + ["tepki bölgesi var, hacim teyidi yok"]
        if al == "AL" and al_vade == "kisa":
            return "kısmen", n + ["kısa AL var ama tepki bölgesi kuralı değil"]
        return "tutmuyor", n + ["tepki kurulumu yok"]

    # kırılacak / düşecek
    if sat == "SAT" and _tf_eslesir(sat_tf, tf):
        return "tutuyor", n + [f"{sat_tf} SAT — tez ile aynı TF"]
    if kirik and tf == "daily":
        return "tutuyor", n + ["süper çizgi daily kapanışlarla kırıldı"]
    if sat == "SAT":
        return "kısmen", n + [f"SAT var ama TF farklı ({sat_tf})"]
    if al == "AL":
        return "tutmuyor", n + ["aksine AL etiketi yanıyor"]
    return "tutmuyor", n + ["SAT etiketi yok"]
