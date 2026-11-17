"""Phase 1 - Exploratory Data Analysis (Steps 1-4 of the framework).

Each public function takes a DataFrame and returns a tidy DataFrame / dict so
results can be saved, compared with the paper, or reused in later chapters.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config


def load_dataset(path) -> pd.DataFrame:
    """Read a NF-ToN-IoT CSV, keeping IP addresses and labels as strings."""
    return pd.read_csv(
        path,
        dtype={"IPV4_SRC_ADDR": str, "IPV4_DST_ADDR": str, config.ATTACK_COL: str},
        keep_default_na=False,  # so that '' and '-' can be inspected explicitly
    )


# --------------------------------------------------------------------------- #
# Step 1 - dataset overview and feature-type analysis
# --------------------------------------------------------------------------- #
def dataset_overview(df: pd.DataFrame) -> dict:
    features = [c for c in df.columns if c not in config.TARGETS]
    return {
        "n_records": len(df),
        "n_attributes": df.shape[1],
        "n_features": len(features),
        "n_targets": len(config.TARGETS),
        "label_values": sorted(df[config.LABEL_COL].unique().tolist()),
        "attack_values": sorted(df[config.ATTACK_COL].unique().tolist(), key=str.lower),
        "n_attack_types": int(
            df.loc[df[config.ATTACK_COL] != "Benign", config.ATTACK_COL].nunique()
        ),
    }


def feature_classification(df: pd.DataFrame) -> pd.DataFrame:
    """Table 2: unique values, functional role, type and zero-value counts."""
    rows = []
    for feat in config.TABLE2_ORDER:
        if feat in config.CATEGORICAL_FEATURES:
            role, kind = config.CATEGORICAL_FEATURES[feat][0], "Categorical"
        else:
            role, kind = "Quantitative data", "Numerical"
        col = df[feat]
        zeros = _zero_count(col)
        rows.append({
            "Feature": feat,
            "Unique Values": col.nunique(),
            "Functional Role": role,
            "Classification": kind,
            "Zero Count": zeros,
            "Zero %": round(100 * zeros / len(df), 2),
        })
    return pd.DataFrame(rows)


def _zero_count(col: pd.Series) -> int:
    """Cells holding the value 0 (paper's definition, Sec. 3.1.2).

    String identifiers (IP addresses) are never equal to 0. Note: 309 flows use
    the unspecified address 0.0.0.0; see ``unspecified_ip_counts``.
    """
    if pd.api.types.is_numeric_dtype(col):
        return int((col == 0).sum())
    return int((col.astype(str).str.strip() == "0").sum())


def unspecified_ip_counts(df: pd.DataFrame) -> dict:
    """Extra finding not in the paper: flows using the 0.0.0.0 address."""
    return {c: int((df[c] == "0.0.0.0").sum()) for c in ("IPV4_SRC_ADDR", "IPV4_DST_ADDR")}


# --------------------------------------------------------------------------- #
# Step 2 - missing and zero-value analysis
# --------------------------------------------------------------------------- #
def missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Count NaN, empty strings and placeholder tokens per column."""
    out = []
    for c in df.columns:
        col = df[c]
        nan = int(col.isna().sum())
        if col.dtype == object or pd.api.types.is_string_dtype(col):
            stripped = col.astype(str).str.strip()
            empty = int((stripped == "").sum())
            placeholder = int(stripped.isin(config.MISSING_PLACEHOLDERS[1:]).sum())
        else:
            empty = placeholder = 0
        out.append({"Column": c, "NaN": nan, "Empty string": empty,
                    "Placeholder '-'": placeholder, "Total missing": nan + empty + placeholder})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- #
# Step 3 - categorical feature analysis
# --------------------------------------------------------------------------- #
def shannon_entropy(col: pd.Series) -> float:
    """H = -sum p log2 p over the observed category frequencies."""
    p = col.value_counts(normalize=True).to_numpy()
    return float(-(p * np.log2(p)).sum())


def categorical_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Table 3: TCP/IP layer, mode, Shannon entropy and maximum entropy."""
    rows = []
    for feat, (_, layer) in config.CATEGORICAL_FEATURES.items():
        col = df[feat]
        rows.append({
            "Feature": feat,
            "TCP/IP Layer": layer,
            "Mode": col.mode().iloc[0],
            "Entropy": round(shannon_entropy(col), 3),
            "Max Entropy": round(float(np.log2(col.nunique())), 3),
        })
    return pd.DataFrame(rows)


def top_frequencies(df: pd.DataFrame, k: int = 4) -> pd.DataFrame:
    """Most frequent values (with % of flows) for every categorical feature."""
    rows = []
    for feat in config.CATEGORICAL_FEATURES:
        vc = df[feat].value_counts(normalize=True).head(k) * 100
        for rank, (val, pct) in enumerate(vc.items(), 1):
            rows.append({"Feature": feat, "Rank": rank, "Value": val, "Percent": round(pct, 2)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Step 4 - numerical feature analysis
# --------------------------------------------------------------------------- #
def iqr_outlier_ratio(col: pd.Series) -> float:
    q1, q3 = col.quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return float(((col < lo) | (col > hi)).mean())


def numerical_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Range, central tendency, dispersion, quartiles, shape and outliers.

    Conventions (checked against the paper's tables):
      * std/variance: sample estimator (ddof=1, pandas default)
      * quartiles: linear interpolation (pandas default)
      * skewness / kurtosis: population moment estimators, Fisher (excess)
        kurtosis -> scipy.stats.skew / scipy.stats.kurtosis defaults
    """
    rows = []
    for feat in config.NUMERICAL_FEATURES:
        x = df[feat].astype("float64")
        q1, q2, q3 = x.quantile([0.25, 0.5, 0.75])
        rows.append({
            "Feature": feat,
            "Min": x.min(), "Max": x.max(),
            "Mean": x.mean(), "Median": q2, "Mode": x.mode().iloc[0],
            "Std": x.std(), "Variance": x.var(),
            "Q1": q1, "Q2": q2, "Q3": q3,
            "Skewness": float(stats.skew(x)),
            "Kurtosis": float(stats.kurtosis(x)),
            "Outlier Ratio": iqr_outlier_ratio(x),
        })
    return pd.DataFrame(rows)


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation among the numerical features (Fig. 4)."""
    return df[config.NUMERICAL_FEATURES].corr(method="pearson")
