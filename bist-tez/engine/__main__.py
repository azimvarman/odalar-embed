"""Komut satırı.

    python -m engine tara [--yenile]
    python -m engine hisse FROTO
    python -m engine geritest FROTO [--adim 5 --pencere 500]
    python -m engine skor
    python -m engine zamanla
"""
from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tara")
    t.add_argument("--yenile", action="store_true", help="önbelleği yok say")
    hs = sub.add_parser("hisse")
    hs.add_argument("sembol")
    g = sub.add_parser("geritest")
    g.add_argument("sembol")
    g.add_argument("--adim", type=int, default=5)
    g.add_argument("--pencere", type=int, default=500)
    sub.add_parser("skor")
    sub.add_parser("zamanla")
    a = p.parse_args(argv)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 40)

    if a.cmd == "tara":
        from .run import tara
        df = tara(progress=lambda i, n, s: print(f"\r{i}/{n} {s:<8}", end="", flush=True),
                  yenile=a.yenile)
        print()
        cols = ["sembol", "fiyat", "kural", "AL", "AL_TF", "AL_vade", "SAT", "SAT_TF", "iptal", "hedef", "rr"]
        print(df[[c for c in cols if c in df.columns]].to_string(index=False))
    elif a.cmd == "hisse":
        from .kart import csv_satiri
        from .run import tek
        rec, _, _ = tek(a.sembol.upper())
        for k, v in csv_satiri(rec).items():
            print(f"{k:>14}: {v}")
    elif a.cmd == "geritest":
        from .config import load_rules
        from .geritest import geri_test, geri_test_ozet
        from .run import gunluk
        cfg = load_rules()
        d = gunluk(a.sembol.upper(), cfg)
        if d is None:
            print("veri yok")
            return 1
        sonuc = geri_test(a.sembol.upper(), d, cfg, adim=a.adim, pencere=a.pencere)
        print(geri_test_ozet(sonuc).to_string(index=False))
    elif a.cmd == "skor":
        from .config import load_rules
        from .run import gunluk
        from .skor import degerlendir, gecmis_yolu, ozet
        if not gecmis_yolu().exists():
            print("henüz günlük yok — önce tara")
            return 1
        cfg = load_rules()
        deg = degerlendir(pd.read_csv(gecmis_yolu()), lambda s: gunluk(s, cfg), cfg["skor"]["ufuklar"])
        print(ozet(deg, cfg["skor"]["ufuklar"]).to_string(index=False))
    elif a.cmd == "zamanla":
        from .zamanla import main as z
        z()
    return 0


if __name__ == "__main__":
    sys.exit(main())
