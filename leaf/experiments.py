"""E1-E5 runners. Each run appends one row to results/leaf/raw/<exp>.csv. Runs
already recorded there are skipped, so an interrupted run can simply be
restarted. Test-set predictions are stored so that confidence intervals and
significance tests can be computed afterwards."""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score

from repro import downsampling as paper_ds
from . import audit, models, sampling
from . import config as C
from .data import class_codes, ip_to_int, split_controlled, split_naive, vector_hash

PRED_DIR = C.RAW_DIR / "predictions"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _done(path, key_cols) -> set:
    if not path.exists():
        return set()
    d = pd.read_csv(path, usecols=key_cols, dtype=str)
    return set(map(tuple, d[key_cols].to_numpy()))


def _append(path, row: dict) -> None:
    """Append one run. Rows may carry different columns (binary runs add
    attack_f1), so the file is rewritten with the union of columns when a new
    column appears; otherwise the row is aligned to the existing header."""
    new = pd.DataFrame([row])
    if not path.exists():
        new.to_csv(path, index=False)
        return
    header = list(pd.read_csv(path, nrows=0).columns)
    if set(new.columns) <= set(header):
        new.reindex(columns=header).to_csv(path, mode="a", header=False, index=False)
    else:
        old = pd.read_csv(path)
        pd.concat([old, new], ignore_index=True).to_csv(path, index=False)


def repair_ragged_csv(path, extra_col="attack_f1", before="importance") -> int:
    """One-off repair for logs written before _append was schema-aware: rows
    with one field more than the header contain `extra_col` just before
    `before`. Returns the number of repaired rows."""
    import csv
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    h = rows[0]
    if extra_col in h:
        return 0
    i = h.index(before)
    h2 = h[:i] + [extra_col] + h[i:]
    out, fixed = [], 0
    for r in rows[1:]:
        if len(r) == len(h):
            r = r[:i] + [""] + r[i:]
        elif len(r) == len(h2):
            fixed += 1
        else:
            raise ValueError(f"unexpected row width {len(r)}")
        out.append(r)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(h2)
        w.writerows(out)
    return fixed


def _fit_predict(name, seed, Xtr, ytr, Xte, n_classes):
    """Fit with labels re-coded to 0..k-1 (some subsets miss rare classes,
    which XGBoost does not accept). Predictions are mapped back afterwards."""
    present = np.unique(ytr)
    lut = np.full(n_classes, -1)
    lut[present] = np.arange(len(present))
    m = models.make(name, seed, len(present))
    t = time.time()
    models.fit(name, m, Xtr, lut[ytr], seed)
    fit_s = time.time() - t
    pred = present[np.asarray(m.predict(Xte)).astype(int).ravel()]
    return m, pred, fit_s


def _metrics(y, p, n_classes, task):
    per = f1_score(y, p, labels=range(n_classes), average=None, zero_division=0)
    out = {"accuracy": accuracy_score(y, p),
           "balanced_accuracy": balanced_accuracy_score(y, p),
           "macro_f1": f1_score(y, p, average="macro", labels=range(n_classes), zero_division=0),
           "weighted_f1": f1_score(y, p, average="weighted", zero_division=0),
           "per_class_f1": json.dumps([round(float(v), 6) for v in per])}
    if task == "binary":
        out["attack_f1"] = f1_score(y, p, pos_label=1, zero_division=0)
    return out


def _importance(model, n_feats):
    est = model[-1] if hasattr(model, "steps") else model
    imp = getattr(est, "feature_importances_", None)
    if imp is None or len(imp) != n_feats:
        return None
    imp = np.asarray(imp, float)
    return json.dumps([round(float(v), 8) for v in imp / max(imp.sum(), 1e-12)])


def splits_for(df, y, task):
    """The evaluation protocols: naive (shared) and controlled (per feature set)."""
    sp = {("naive", fs): split_naive(df, y) for fs in C.FEATURE_SETS}
    for fs, feats in C.FEATURE_SETS.items():
        sp[("controlled", fs)] = split_controlled(df, y, feats)
    return sp


# --------------------------------------------------------------------------- #
# E1 / E2
# --------------------------------------------------------------------------- #
def run_e1(df):
    summary, per_class = audit.integrity_audit(df)
    summary.to_csv(C.TABLE_DIR / "E1_integrity_summary.csv", index=False)
    per_class.to_csv(C.TABLE_DIR / "E1_integrity_per_class.csv", index=False)
    for fs, feats in C.FEATURE_SETS.items():
        audit.conflict_cooccurrence(df, feats).round(2).to_csv(
            C.TABLE_DIR / f"E1_label_cooccurrence_{fs}.csv")
    return summary, per_class


def run_e2(df, split_cache):
    out = []
    for task in ("binary", "multiclass"):
        for proto in ("naive", "controlled"):
            tr, te = split_cache[task][(proto, "ALL")]
            r = audit.single_feature_power(df, tr, te, task)
            r.insert(0, "Protocol", proto)
            out.append(r)
    res = pd.concat(out, ignore_index=True)
    res.to_csv(C.TABLE_DIR / "E2_shortcut_audit.csv", index=False)
    return res


# --------------------------------------------------------------------------- #
# E3 - protocol inflation on the full dataset
# --------------------------------------------------------------------------- #
def run_e3(df, split_cache, model_list=models.MODELS, tasks=("multiclass", "binary")):
    path = C.RAW_DIR / "E3_protocol.csv"
    keys = ["task", "protocol", "feature_set", "model"]
    done = _done(path, keys)
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        y, names = class_codes(df, task)
        for (proto, fs), (tr, te) in split_cache[task].items():
            feats = C.FEATURE_SETS[fs]
            Xtr, Xte = df.iloc[tr][feats].to_numpy(), df.iloc[te][feats].to_numpy()
            for name in model_list:
                if (task, proto, fs, name) in done:
                    continue
                m, p, fit_s = _fit_predict(name, 0, Xtr, y[tr], Xte, len(names))
                row = {"task": task, "protocol": proto, "feature_set": fs, "model": name,
                       "n_train": len(tr), "n_test": len(te), "fit_seconds": round(fit_s, 1),
                       **_metrics(y[te], p, len(names), task),
                       "importance": _importance(m, len(feats))}
                _append(path, row)
                np.savez_compressed(PRED_DIR / f"E3_{task}_{proto}_{fs}_{name}.npz",
                                    test_idx=te, y_true=y[te], y_pred=p)
                print(f"[E3] {task:10s} {proto:10s} {fs:4s} {name:4s} macroF1={row['macro_f1']:.4f} "
                      f"acc={row['accuracy']:.4f} ({fit_s:.0f}s)", flush=True)


# --------------------------------------------------------------------------- #
# E4 - subset fidelity (does a reduced training set give the same conclusions?)
# --------------------------------------------------------------------------- #
def run_e4(df, split_cache, model_list=models.MODELS, feature_sets=("NOID", "ALL"),
           strategies=sampling.STRATEGIES, budgets=C.BUDGETS, seeds=C.SUBSET_SEEDS):
    task = "multiclass"
    y, names = class_codes(df, task)
    path = C.RAW_DIR / "E4_subset_fidelity.csv"
    keys = ["feature_set", "strategy", "budget", "seed", "model"]
    done = _done(path, keys)
    for fs in feature_sets:
        feats = C.FEATURE_SETS[fs]
        pool, te = split_cache[task][("controlled", fs)]
        Xte = df.iloc[te][feats].to_numpy()
        for strategy in strategies:
            for budget in budgets:
                for seed in seeds:
                    idx = sampling.draw(df, pool, strategy, budget, seed)
                    counts = np.bincount(y[idx], minlength=len(names))
                    for name in model_list:
                        k = (fs, strategy, str(budget), str(seed), name)
                        if k in done:
                            continue
                        m, p, fit_s = _fit_predict(name, seed, df.iloc[idx][feats].to_numpy(),
                                                   y[idx], Xte, len(names))
                        row = {"feature_set": fs, "strategy": strategy, "budget": budget,
                               "seed": seed, "model": name, "n_train": len(idx),
                               "n_classes_in_train": int((counts > 0).sum()),
                               "train_class_counts": json.dumps(counts.tolist()),
                               "fit_seconds": round(fit_s, 1),
                               **_metrics(y[te], p, len(names), task),
                               "importance": _importance(m, len(feats))}
                        _append(path, row)
                    print(f"[E4] {fs} {strategy:18s} {budget:6d} seed={seed} done", flush=True)


# --------------------------------------------------------------------------- #
# E5 - is evaluating inside the published 49,997-row subset trustworthy?
# --------------------------------------------------------------------------- #
def published_subset_positions(df) -> np.ndarray:
    """Positions of the rows of the authors' published subset.

    The repro pipeline showed our Step-5 implementation is row-identical to the
    published CSV, so the same sampling on the original frame gives the
    original row positions. This is verified against the published file.
    """
    view = df.drop(columns="row_id").copy()
    attack = view[C.ATTACK]
    alloc = paper_ds.class_allocation(attack)
    pos = []
    for cls in paper_ds.config.CONCAT_ORDER:
        n = int(alloc.at[cls, "Target"])
        pos.append(view[attack == cls].sample(n=n, random_state=paper_ds.config.RANDOM_STATE).index)
    pos = np.concatenate(pos)
    # Verify against the published file (IPs are integer-encoded in df).
    ref = pd.read_csv(C.REFERENCE_CSV)
    for c in ("IPV4_SRC_ADDR", "IPV4_DST_ADDR"):
        ref[c] = ip_to_int(ref[c])
    cols = list(ref.columns)
    mine = df.iloc[pos][cols].reset_index(drop=True)
    if not mine.astype(str).equals(ref[cols].astype(str)):
        raise RuntimeError("could not locate the published subset in the original data")
    return pos


def run_e5(df, model_list=models.MODELS, seeds=C.SUBSET_SEEDS):
    task = "multiclass"
    y, names = class_codes(df, task)
    sub = published_subset_positions(df)
    outside = np.setdiff1d(np.arange(len(df)), sub)
    path = C.RAW_DIR / "E5_internal_vs_external.csv"
    keys = ["feature_set", "seed", "model"]
    done = _done(path, keys)
    from sklearn.model_selection import train_test_split
    for fs, feats in C.FEATURE_SETS.items():
        h = vector_hash(df, feats)
        X = df[feats].to_numpy()
        for seed in seeds:
            tr, te = train_test_split(sub, test_size=C.TEST_FRACTION, stratify=y[sub], random_state=seed)
            # external test sets drawn from the 96.4% of flows outside the subset
            seen = np.isin(h[outside], h[tr])
            ext_all, ext_unseen = outside, outside[~seen]
            for name in model_list:
                if (fs, str(seed), name) in done:
                    continue
                m, p_int, fit_s = _fit_predict(name, seed, X[tr], y[tr], X[te], len(names))
                present = np.unique(y[tr])
                p_all = present[np.asarray(m.predict(X[ext_all])).astype(int).ravel()]
                p_un = p_all[~seen]
                row = {"feature_set": fs, "seed": seed, "model": name,
                       "n_train": len(tr), "n_internal_test": len(te),
                       "n_external": len(ext_all), "n_external_unseen": len(ext_unseen),
                       "internal_test_class_counts": json.dumps(np.bincount(y[te], minlength=len(names)).tolist())}
                for tag, yt, pp in (("internal", y[te], p_int), ("external", y[ext_all], p_all),
                                    ("external_unseen", y[ext_unseen], p_un)):
                    for k, v in _metrics(yt, pp, len(names), task).items():
                        row[f"{tag}_{k}"] = v
                _append(path, row)
                print(f"[E5] {fs} seed={seed} {name:4s} internal={row['internal_macro_f1']:.4f} "
                      f"external={row['external_macro_f1']:.4f} unseen={row['external_unseen_macro_f1']:.4f}",
                      flush=True)
