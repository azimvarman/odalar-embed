"""Gece taraması: hafta içi seans sonu (varsayılan 18:20) otomatik tarar.

Konteynerde ayrı servis olarak çalışır (`docker-compose.yml` → zamanlayici).
cron gerektirmez; saat dilimi Europe/Istanbul.
"""
from __future__ import annotations

import logging
import time

import pandas as pd

from .config import TZ, load_rules

log = logging.getLogger("bist.zamanla")


def sonraki(now: pd.Timestamp, saatler: list[str], gunler: list[int]) -> pd.Timestamp:
    adaylar = []
    for gun in range(0, 8):
        tarih = (now + pd.Timedelta(days=gun)).normalize()
        if tarih.weekday() not in gunler:
            continue
        for s in saatler:
            hh, mm = (int(x) for x in str(s).split(":"))
            t = tarih + pd.Timedelta(hours=hh, minutes=mm)
            if t > now:
                adaylar.append(t)
    return min(adaylar)


def calistir_bir_kez() -> None:
    from .run import tara
    t0 = time.time()
    df = tara()
    log.info("tarama bitti: %d hisse, %.0f sn, AL=%d SAT=%d", len(df), time.time() - t0,
             int((df.get("AL") == "AL").sum()) if len(df) else 0,
             int((df.get("SAT") == "SAT").sum()) if len(df) else 0)


def main() -> None:
    while True:
        cfg = load_rules()  # her döngüde oku: YAML değişikliği yeniden başlatma istemez
        z = cfg["zamanlama"]
        now = pd.Timestamp.now(tz=TZ)
        hedef = sonraki(now, z["saatler"], z["gunler"])
        log.info("sonraki tarama: %s", hedef.isoformat(timespec="minutes"))
        while (kalan := (hedef - pd.Timestamp.now(tz=TZ)).total_seconds()) > 0:
            time.sleep(min(kalan, 300))
        try:
            calistir_bir_kez()
        except Exception:
            log.exception("tarama hatası")
        time.sleep(61)
