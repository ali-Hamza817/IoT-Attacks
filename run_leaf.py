"""Run the LEAF experiments.

    python run_leaf.py e1 e2 e3 e4 e5     # any subset, in this order
    python run_leaf.py e1b e6           # replication forensics, fidelity of reduced datasets
    python run_leaf.py e6b              # E6 confirmatory extension: 15 more seeds, 3 configs
    python run_leaf.py leak             # W6: test vectors seen in training, per split
    python run_leaf.py all

Splits are computed once and cached in results/leaf/raw/splits.npz, so every
experiment and every rerun uses identical train/test partitions.
"""
from __future__ import annotations

import sys
import time

import numpy as np

from leaf import config as C
from leaf import data, experiments as E, fidelity, forensics


def get_splits(df):
    path = C.RAW_DIR / "splits.npz"
    if path.exists():
        z = np.load(path)
        cache = {}
        for k in z.files:
            task, proto, fs, part = k.split("|")
            cache.setdefault(task, {}).setdefault((proto, fs), [None, None])
            cache[task][(proto, fs)][0 if part == "tr" else 1] = z[k]
        return {t: {k: tuple(v) for k, v in d.items()} for t, d in cache.items()}
    cache, flat = {}, {}
    for task in ("multiclass", "binary"):
        y, _ = data.class_codes(df, task)
        cache[task] = E.splits_for(df, y, task)
        for (proto, fs), (tr, te) in cache[task].items():
            flat[f"{task}|{proto}|{fs}|tr"], flat[f"{task}|{proto}|{fs}|te"] = tr, te
    np.savez_compressed(path, **flat)
    return cache


def main(argv):
    steps = [s.lower() for s in argv] or ["all"]
    if "all" in steps:
        steps = ["e1", "e2", "e3", "e4", "e5"]
    C.ensure_dirs()
    t0 = time.time()
    df = data.load()
    print(f"[load] {len(df):,} rows", flush=True)
    splits = get_splits(df) if set(steps) & {"e2", "e3", "e4"} else None
    for s in steps:
        t = time.time()
        if s == "e1":
            E.run_e1(df)
        elif s == "e2":
            E.run_e2(df, splits)
        elif s == "e3":
            E.run_e3(df, splits)
        elif s == "e4":
            E.run_e4(df, splits)
        elif s == "e5":
            E.run_e5(df)
        elif s == "e1b":
            forensics.main()
        elif s == "e6":
            fidelity.run_e6(df)
        elif s == "e6b":
            fidelity.run_e6b(df)
        elif s == "leak":
            print(fidelity.random_split_leakage(df).to_string(index=False))
        else:
            raise SystemExit(f"unknown step {s}")
        print(f"[{s}] finished in {time.time() - t:.0f}s", flush=True)
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
