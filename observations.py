"""Recompute the facts listed in README Section 8 ("Observations made during
reproduction"), so that every number quoted there can be checked.

    python observations.py      (run after run_pipeline.py has downloaded the data)

Writes results/tables/observations_correlation_sensitivity.csv and prints a summary.
"""
from __future__ import annotations

import pandas as pd

from repro import config, download

NUM = ["IN_BYTES", "OUT_BYTES", "IN_PKTS", "OUT_PKTS"]


def correlation_sensitivity(df: pd.DataFrame, ks=(0, 1, 5, 10, 50, 100)) -> pd.DataFrame:
    """Pearson correlations after removing the k largest flows by IN_BYTES and
    the k largest by OUT_BYTES (the union of both sets)."""
    rows = []
    for k in ks:
        top = set(df["IN_BYTES"].nlargest(k).index) | set(df["OUT_BYTES"].nlargest(k).index) if k else set()
        d = df.drop(index=list(top))
        rows.append({"k": k, "flows_removed": len(top),
                     "r(IN_BYTES,OUT_BYTES)": round(d["IN_BYTES"].corr(d["OUT_BYTES"]), 3),
                     "r(OUT_BYTES,IN_PKTS)": round(d["OUT_BYTES"].corr(d["IN_PKTS"]), 3),
                     "r(IN_BYTES,OUT_PKTS)": round(d["IN_BYTES"].corr(d["OUT_PKTS"]), 3)})
    return pd.DataFrame(rows)


def main() -> None:
    csv = download.find_original_csv()
    if csv is None:
        raise SystemExit("original CSV not found; run `python run_pipeline.py` first")
    df = pd.read_csv(csv)
    sub = pd.read_csv(config.REPRODUCED_CSV)

    sens = correlation_sensitivity(df[NUM])
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    sens.to_csv(config.TABLES_DIR / "observations_correlation_sensitivity.csv", index=False)
    print("Correlation after removing the k largest flows (by IN_BYTES and by OUT_BYTES):")
    print(sens.to_string(index=False))

    print("\nMaximum values, full vs subset:")
    for c in NUM + ["FLOW_DURATION_MILLISECONDS"]:
        print(f"  {c:28s} {df[c].max():>12,} {sub[c].max():>12,}  preserved={df[c].max() == sub[c].max()}")

    print("\nSmallest classes in the subset:")
    print(sub[config.ATTACK_COL].value_counts().nsmallest(3).to_string())

    both = ((df["IPV4_SRC_ADDR"] == "0.0.0.0") & (df["IPV4_DST_ADDR"] == "0.0.0.0")).sum()
    print(f"\nFlows with 0.0.0.0 as both source and destination IP: {both:,}")


if __name__ == "__main__":
    main()
