"""Candidate-label (partial-label) view of NF-ToN-IoT V1.

E1/E1b show that 287,559 distinct 12-feature records carry several attack
labels, each label exactly the same number of times, and that dos, password,
scanning and xss have no record that carries their label alone. A record's
labels are therefore best read as a *set of candidate labels*: the true
label is one of them, but the data cannot say which.

This module
  * consolidates the replicated rows into one record per distinct feature
    vector, carrying a bitmask of its candidate labels (Step "label
    consolidation" of the improved framework);
  * expands records back into one (x, label) training row per candidate, so
    ordinary single-label classifiers can be trained;
  * scores predictions against candidate sets.

The metrics generalise the usual ones. With single-label records (one bit per
mask) they are exactly accuracy, balanced accuracy and macro-F1 (scikit-learn
defaults). The primary metric is balanced consistency:
  consistent accuracy  share of records whose prediction is in the candidate set
  balanced consistency mean over classes c of the consistent accuracy on the
                       records that have c among their candidates
  resolved macro-F1    macro-F1 after resolving each record's target to the
                       prediction if it is a candidate, otherwise to the
                       record's lowest-index candidate
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from .data import class_codes


def single_masks(y: np.ndarray) -> np.ndarray:
    """Masks for ordinary single-label data (bit y set)."""
    return np.left_shift(np.int64(1), y.astype(np.int64))


def consolidate(df: pd.DataFrame, feats: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """One record per distinct vector over ``feats``.

    Returns a frame with the feature columns, ``mask`` (OR of the label bits of
    every row with that vector), ``n_rows`` (rows of the original data merged
    into the record) and ``label`` (binary: 1 if any candidate is an attack).
    """
    y, names = class_codes(df, "multiclass")
    t = df[feats].copy()
    t["bit"] = single_masks(y)
    g = t.groupby(feats, sort=False)
    out = g["bit"].agg(np.bitwise_or.reduce).rename("mask").to_frame()
    out["n_rows"] = g.size()
    out = out.reset_index()
    benign = names.index("Benign")
    out["label"] = (out["mask"] & ~np.int64(1 << benign)).ne(0).astype(np.int64)
    return out, names


def n_candidates(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.int64).copy()
    c = np.zeros(len(m), np.int64)
    while m.any():
        c += m & 1
        m >>= 1
    return c


def lowest_bit(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.int64)
    return np.log2(m & -m).astype(np.int64)


def expand(X: np.ndarray, mask: np.ndarray, n_classes: int) -> tuple[np.ndarray, np.ndarray]:
    """One training row per (record, candidate label)."""
    rows, labels = [], []
    for c in range(n_classes):
        hit = np.flatnonzero((mask >> c) & 1)
        rows.append(hit)
        labels.append(np.full(len(hit), c, np.int64))
    rows, labels = np.concatenate(rows), np.concatenate(labels)
    order = np.argsort(rows, kind="stable")
    return X[rows[order]], labels[order]


def scores(mask: np.ndarray, pred: np.ndarray, n_classes: int) -> dict:
    mask = mask.astype(np.int64)
    pred = pred.astype(np.int64)
    ok = ((mask >> pred) & 1).astype(bool)
    per_class, support = [], []
    for c in range(n_classes):
        has = ((mask >> c) & 1).astype(bool)
        support.append(int(has.sum()))
        per_class.append(float(ok[has].mean()) if has.any() else np.nan)
    per_class = np.array(per_class)
    target = np.where(ok, pred, lowest_bit(mask))
    # Labels = classes occurring in the resolved targets or the predictions
    # (scikit-learn's default). A class that only ever appears as a secondary
    # candidate and is never predicted is never wrong, so it is not scored.
    return {
        "consistent_accuracy": float(ok.mean()),
        "balanced_consistency": float(np.nanmean(per_class)),
        "resolved_macro_f1": float(f1_score(target, pred, average="macro", zero_division=0)),
        "per_class_consistency": per_class,
        "support": np.array(support),
    }
