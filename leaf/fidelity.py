"""E6 - evaluation fidelity of reduced datasets: published pipeline vs LEAF.

Question: a researcher downloads a ~50k-row subset of NF-ToN-IoT V1, splits
it 80/20 and reports scores. Do those scores, and the model ranking they
imply, hold on the rest of the dataset?

Design factors (each config fixes one value of each):
  labels    raw          - one label per row, replicated as published
            consolidated - one record per distinct vector, candidate-label set
                           (leaf.partial)
  sampling  published    - the authors' exact 49,997-row subset (raw only)
            proportional - Eq. 1 of the paper, S_c = int(P_c * budget)
            floor        - proportional, with min(CLASS_FLOOR, available) per
                           stratum
  protocol  random       - stratified random 80/20 split of the subset
            disjoint     - identical feature vectors never on both sides
                           (for consolidated data every record is already a
                           distinct vector, so random == disjoint)
  features  ALL (12, with IPs/ports) or NOID (8 flow features)

Strata are classes for raw data and candidate sets for consolidated data.

For every (config, seed, model):
  internal - scores on the subset's own 20% test part;
  external - scores on every record of the same pool that is outside the
             subset and whose feature vector never occurs in the subset's
             training part (unseen data).
The metrics come from leaf.partial; on raw data they equal accuracy, balanced
accuracy and macro-F1.

    python run_leaf.py e6
Results are appended to results/leaf/raw/E6_fidelity.csv (resumable).
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from . import config as C
from . import models, partial
from . import sampling as S
from .data import class_codes, vector_hash
from .experiments import _append, _done, published_subset_positions

BUDGET = 50_000
SEEDS = C.SUBSET_SEEDS
METRICS = ["consistent_accuracy", "balanced_consistency", "resolved_macro_f1"]


def configs() -> list[dict]:
    out = []
    for fs in ("ALL", "NOID"):
        for samp in ("published", "proportional", "floor"):
            for proto in ("random", "disjoint"):
                out.append(dict(labels="raw", sampling=samp, protocol=proto, features=fs))
        for samp in ("proportional", "floor"):
            out.append(dict(labels="consolidated", sampling=samp, protocol="disjoint", features=fs))
    return out


def config_name(c: dict) -> str:
    return f"{c['labels']}|{c['sampling']}|{c['protocol']}|{c['features']}"


# --------------------------------------------------------------------------- #
# pools: what a "record" is under each label handling
# --------------------------------------------------------------------------- #
class Pool:
    def __init__(self, X: np.ndarray, mask: np.ndarray, hashes: np.ndarray, strata: np.ndarray):
        self.X, self.mask, self.hashes, self.strata = X, mask, hashes, strata
        self.members = pd.Series(np.arange(len(mask))).groupby(strata).apply(lambda s: s.to_numpy()).to_dict()


def build_pool(df: pd.DataFrame, labels: str, fs: str) -> Pool:
    feats = C.FEATURE_SETS[fs]
    if labels == "raw":
        y, _ = class_codes(df, "multiclass")
        return Pool(df[feats].to_numpy(), partial.single_masks(y), vector_hash(df, feats), y)
    rec, _ = partial.consolidate(df, feats)
    m = rec["mask"].to_numpy(np.int64)
    return Pool(rec[feats].to_numpy(), m, vector_hash(rec, feats), m)


# --------------------------------------------------------------------------- #
# subset drawing and splitting
# --------------------------------------------------------------------------- #
def draw(pool: Pool, sampling: str, seed: int, published: np.ndarray | None = None) -> np.ndarray:
    if sampling == "published":
        return np.sort(published)
    counts = pd.Series(pool.strata).value_counts().sort_index()
    if sampling == "proportional":
        alloc = S._alloc_proportional(counts, BUDGET)
    elif sampling == "floor":
        alloc = S._alloc_floor(counts, BUDGET, C.CLASS_FLOOR)
    else:
        raise ValueError(sampling)
    rng = np.random.default_rng(seed)
    picks = [rng.choice(pool.members[s], size=int(min(n, counts[s])), replace=False)
             for s, n in alloc.items() if n > 0]
    return np.sort(np.concatenate(picks))


def _stratify_labels(strata: np.ndarray) -> np.ndarray:
    """Strata with a single member cannot be stratified; pool them."""
    s = pd.Series(strata)
    vc = s.value_counts()
    s = s.where(s.map(vc) >= 2, -1)
    if (s == -1).sum() == 1:
        s[s == -1] = vc.index[0]
    return s.to_numpy()


def split(pool: Pool, sub: np.ndarray, protocol: str, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """80/20 split of the subset; returns positions into the pool."""
    strata = pool.strata[sub]
    if protocol == "random":
        tr, te = train_test_split(np.arange(len(sub)), test_size=C.TEST_FRACTION,
                                  stratify=_stratify_labels(strata), random_state=seed)
    else:
        codes, uniq = pd.factorize(pool.hashes[sub])
        first = pd.Series(np.arange(len(sub))).groupby(codes).first().to_numpy()
        gtr, gte = train_test_split(np.arange(len(uniq)), test_size=C.TEST_FRACTION,
                                    stratify=_stratify_labels(strata[first]), random_state=seed)
        is_te = np.zeros(len(uniq), bool)
        is_te[gte] = True
        te = np.flatnonzero(is_te[codes])
        tr = np.flatnonzero(~is_te[codes])
    return np.sort(sub[tr]), np.sort(sub[te])


def external(pool: Pool, sub: np.ndarray, tr: np.ndarray) -> np.ndarray:
    outside = np.setdiff1d(np.arange(len(pool.mask)), sub, assume_unique=True)
    seen = np.isin(pool.hashes[outside], pool.hashes[tr])
    return outside[~seen]


# --------------------------------------------------------------------------- #
# runner
# --------------------------------------------------------------------------- #
def _fit(name: str, seed: int, X: np.ndarray, y: np.ndarray, n_classes: int):
    present = np.unique(y)
    lut = np.full(n_classes, -1)
    lut[present] = np.arange(len(present))
    m = models.make(name, seed, len(present))
    t = time.time()
    models.fit(name, m, X, lut[y], seed)
    return m, present, time.time() - t


def _predict(m, present, X):
    return present[np.asarray(m.predict(X)).astype(int).ravel()]


# Confirmatory extension (added after E6, separate output file): more seeds on
# the paper's practice, the paper's file with a disjoint split, and full LEAF.
E6B_CONFIGS = ["raw|published|random|ALL", "raw|published|disjoint|ALL", "consolidated|floor|disjoint|NOID"]
E6B_SEEDS = list(range(5, 20))


def run_e6b(df: pd.DataFrame) -> None:
    run_e6(df, seeds=E6B_SEEDS, only=E6B_CONFIGS, path=C.RAW_DIR / "E6b_more_seeds.csv")


def run_e6(df: pd.DataFrame, model_list=models.MODELS, seeds=SEEDS, only=None, path=None) -> None:
    path = path or C.RAW_DIR / "E6_fidelity.csv"
    keys = ["config", "seed", "model"]
    done = _done(path, keys)
    _, names = class_codes(df, "multiclass")
    K = len(names)
    published = published_subset_positions(df)
    pools: dict = {}
    for cfg in configs():
        cname = config_name(cfg)
        if only is not None and cname not in only:
            continue
        todo = [(s, m) for s in seeds for m in model_list if (cname, str(s), m) not in done]
        if not todo:
            continue
        pk = (cfg["labels"], cfg["features"])
        if pk not in pools:
            pools.clear()                       # keep memory bounded: one pool at a time
            pools[pk] = build_pool(df, *pk)
        pool = pools[pk]
        for seed in sorted({s for s, _ in todo}):
            sub = draw(pool, cfg["sampling"], seed, published)
            tr, te = split(pool, sub, cfg["protocol"], seed)
            ext = external(pool, sub, tr)
            Xtr, ytr = partial.expand(pool.X[tr], pool.mask[tr], K)
            Xte, Xext = pool.X[te], pool.X[ext]
            for name in [m for s, m in todo if s == seed]:
                m, present, fit_s = _fit(name, seed, Xtr, ytr, K)
                si = partial.scores(pool.mask[te], _predict(m, present, Xte), K)
                se = partial.scores(pool.mask[ext], _predict(m, present, Xext), K)
                row = {"config": cname, **cfg, "seed": seed, "model": name,
                       "n_subset": len(sub), "n_train_records": len(tr), "n_train_rows": len(ytr),
                       "n_internal_test": len(te), "n_external": len(ext), "fit_seconds": round(fit_s, 1),
                       "internal_min_class_support": int(si["support"][si["support"] > 0].min()),
                       "internal_classes_lt10": int(((si["support"] > 0) & (si["support"] < 10)).sum()),
                       "internal_classes_absent": int((si["support"] == 0).sum()),
                       "internal_support": json.dumps(si["support"].tolist()),
                       "external_support": json.dumps(se["support"].tolist())}
                for tag, s in (("internal", si), ("external", se)):
                    for k in METRICS:
                        row[f"{tag}_{k}"] = s[k]
                    row[f"{tag}_per_class"] = json.dumps([None if np.isnan(v) else round(float(v), 6)
                                                          for v in s["per_class_consistency"]])
                _append(path, row)
                print(f"[E6] {cname:38s} seed={seed} {name:4s} "
                      f"bal int={si['balanced_consistency']:.4f} ext={se['balanced_consistency']:.4f} "
                      f"({fit_s:.0f}s)", flush=True)


def random_split_leakage(df: pd.DataFrame, seeds=range(20)) -> pd.DataFrame:
    """W6: share of internal test records whose exact feature vector also occurs
    in the training part, for each raw config's random and disjoint split."""
    published = published_subset_positions(df)
    rows = []
    for fs in ("ALL", "NOID"):
        pool = build_pool(df, "raw", fs)
        for samp in ("published", "proportional", "floor"):
            for proto in ("random", "disjoint"):
                for seed in seeds:
                    sub = draw(pool, samp, seed, published)
                    tr, te = split(pool, sub, proto, seed)
                    rows.append({"sampling": samp, "protocol": proto, "features": fs, "seed": seed,
                                 "test_seen_in_train": float(np.isin(pool.hashes[te], pool.hashes[tr]).mean())})
    out = pd.DataFrame(rows)
    out.to_csv(C.TABLE_DIR / "E6_split_leakage_per_seed.csv", index=False)
    summ = (out.groupby(["features", "sampling", "protocol"])["test_seen_in_train"]
            .agg(["mean", "min", "max"]).reset_index())
    summ.to_csv(C.TABLE_DIR / "E6_split_leakage.csv", index=False)
    return summ
