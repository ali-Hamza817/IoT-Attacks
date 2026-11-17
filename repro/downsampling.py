"""Phase 2 - Step 5: proportional stratified random downsampling.

    S_c = P_c * S_total,   P_c = p_c / 100            (paper, Eq. 1)

Each class is sampled on its own, without replacement, with a fixed seed.
The per-class subsets are then concatenated in sorted class-label order.
"""
from __future__ import annotations

import pandas as pd

from . import config


def class_allocation(
    labels: pd.Series,
    target_size: int = config.TARGET_SIZE,
    percent_decimals: int | None = config.PERCENT_DECIMALS,
) -> pd.DataFrame:
    """Return the target sample count S_c for every class.

    ``percent_decimals`` rounds the class percentage p_c before applying Eq. 1.
    With 4 decimals this gives exactly the counts in the paper's Table 4
    (49,997 rows). ``None`` uses the exact proportion and gives 49,995 rows.
    """
    counts = labels.value_counts().sort_index()
    pct = counts / counts.sum() * 100
    if percent_decimals is not None:
        pct = pct.round(percent_decimals)
    target = (pct / 100 * target_size).astype(int)  # int(S_c): whole rows
    return pd.DataFrame({"Count": counts, "Percent": pct, "Target": target})


def stratified_downsample(
    df: pd.DataFrame,
    by: str = config.ATTACK_COL,
    target_size: int = config.TARGET_SIZE,
    random_state: int = config.RANDOM_STATE,
    percent_decimals: int | None = config.PERCENT_DECIMALS,
    order: list[str] | None = config.CONCAT_ORDER,
) -> pd.DataFrame:
    alloc = class_allocation(df[by], target_size, percent_decimals)
    classes = list(alloc.index)
    if order is not None and set(order) == set(classes):
        classes = list(order)
    parts = [
        df[df[by] == cls].sample(
            n=int(alloc.at[cls, "Target"]), replace=False, random_state=random_state
        )
        for cls in classes
    ]
    return pd.concat(parts, ignore_index=True)


def class_distribution_table(full: pd.DataFrame, sub: pd.DataFrame) -> pd.DataFrame:
    """Table 4: Label/Attack counts and percentages in both datasets."""
    keys = [config.LABEL_COL, config.ATTACK_COL]
    f = full.groupby(keys).size().rename("Full Count")
    s = sub.groupby(keys).size().rename("Sub Count")
    t = pd.concat([f, s], axis=1).fillna(0).astype(int)
    t = t.sort_index(level=[0, 1], key=lambda i: i.astype(str).str.lower())
    t["Full %"] = t["Full Count"] / len(full) * 100
    t["Sub %"] = t["Sub Count"] / len(sub) * 100
    t["Abs Dev (pp)"] = (t["Full %"] - t["Sub %"]).abs()
    t = t.reset_index()
    attack = t[t[config.LABEL_COL] == 1]
    totals = pd.DataFrame([
        {config.LABEL_COL: "", config.ATTACK_COL: "Total (Label=1)",
         "Full Count": attack["Full Count"].sum(), "Sub Count": attack["Sub Count"].sum(),
         "Full %": attack["Full %"].sum(), "Sub %": attack["Sub %"].sum(), "Abs Dev (pp)": None},
        {config.LABEL_COL: "", config.ATTACK_COL: "Total dataset records (flows)",
         "Full Count": len(full), "Sub Count": len(sub),
         "Full %": 100.0, "Sub %": 100.0, "Abs Dev (pp)": None},
    ])
    return pd.concat([t, totals], ignore_index=True)


def compare_with_reference(ours: pd.DataFrame, reference: pd.DataFrame) -> dict:
    """Row-level check of our subset against the authors' published CSV."""
    same_shape = ours.shape == reference.shape
    same_cols = list(ours.columns) == list(reference.columns)
    identical = False
    if same_shape and same_cols:
        a = ours.reset_index(drop=True)
        b = reference.reset_index(drop=True).astype(a.dtypes.to_dict())
        identical = bool(a.equals(b))
    return {"our_shape": ours.shape, "reference_shape": reference.shape,
            "same_columns": same_cols, "identical_rows_and_order": identical}
