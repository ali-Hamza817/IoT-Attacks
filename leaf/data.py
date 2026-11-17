"""Loading, encoding, de-duplication and the two evaluation protocols."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from repro import download
from . import config as C


def ip_to_int(s: pd.Series) -> pd.Series:
    o = s.str.split(".", expand=True).astype(np.int64)
    return o[0] * (1 << 24) + o[1] * (1 << 16) + o[2] * (1 << 8) + o[3]


def load(path=None) -> pd.DataFrame:
    """Original NF-ToN-IoT V1 with IPs encoded as 32-bit integers.

    A stable ``row_id`` (position in the official CSV) is kept, so any subset
    can be traced back to the original rows.
    """
    path = path or download.find_original_csv()
    df = pd.read_csv(path)
    df.insert(0, "row_id", np.arange(len(df), dtype=np.int64))
    for c in ("IPV4_SRC_ADDR", "IPV4_DST_ADDR"):
        df[c] = ip_to_int(df[c])
    df[C.ATTACK] = df[C.ATTACK].astype(str)
    return df


def class_codes(df: pd.DataFrame, task: str) -> tuple[np.ndarray, list[str]]:
    if task == "binary":
        return df[C.LABEL].to_numpy(np.int64), ["Benign", "Attack"]
    names = sorted(df[C.ATTACK].unique(), key=str.lower)
    lut = {n: i for i, n in enumerate(names)}
    return df[C.ATTACK].map(lut).to_numpy(np.int64), names


def vector_hash(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """64-bit hash of a row's feature vector: equal vectors -> equal hash."""
    return pd.util.hash_pandas_object(df[cols], index=False).to_numpy()


def exact_duplicate_mask(df: pd.DataFrame) -> np.ndarray:
    cols = C.FEATURE_SETS["ALL"] + [C.LABEL, C.ATTACK]
    return df.duplicated(cols, keep="first").to_numpy()


# --------------------------------------------------------------------------- #
# Evaluation protocols
# --------------------------------------------------------------------------- #
def split_naive(df: pd.DataFrame, y: np.ndarray, seed: int = C.SPLIT_SEED):
    """Common practice: stratified random 80/20 split of the raw rows."""
    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=C.TEST_FRACTION, stratify=y, random_state=seed)
    return np.sort(tr), np.sort(te)


def split_controlled(df: pd.DataFrame, y: np.ndarray, feats: list[str], seed: int = C.SPLIT_SEED):
    """Leakage-controlled split.

    1. exact duplicate rows are removed (only the first occurrence is kept);
    2. rows are grouped by their feature vector over ``feats``, and every
       group goes wholly to train or wholly to test. So no test vector
       appears in training.
    Groups are split 80/20 with stratification on each group's majority
    class. This is a fast group-level equivalent of StratifiedGroupKFold,
    whose Python loop is impractical for ~10^6 groups.
    Returns positional indices into ``df``.
    """
    keep = np.flatnonzero(~exact_duplicate_mask(df))
    g = pd.Series(vector_hash(df.iloc[keep], feats))
    codes, uniq = pd.factorize(g)
    t = pd.DataFrame({"g": codes, "y": y[keep]}).value_counts().reset_index(name="n")
    major = t.sort_values(["g", "n"], ascending=[True, False]).drop_duplicates("g")
    major = major.set_index("g")["y"].reindex(range(len(uniq))).to_numpy()
    gtr, gte = train_test_split(np.arange(len(uniq)), test_size=C.TEST_FRACTION,
                                stratify=major, random_state=seed)
    is_test = np.zeros(len(uniq), bool)
    is_test[gte] = True
    te_mask = is_test[codes]
    return np.sort(keep[~te_mask]), np.sort(keep[te_mask])
