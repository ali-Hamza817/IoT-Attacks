"""E1b - forensics of cross-class label replication in NF-ToN-IoT V1.

Tests the hypothesis that each multi-label record is ONE flow that was
written out once for every attack label it matched during labelling, rather
than several distinct flows that happen to look identical.

Fingerprints checked on every 12-feature vector that carries >1 attack label:
  1. equal multiplicity  - every label of the vector occurs k times;
  2. product structure   - total rows = (number of labels) x k;
  3. ephemeral src port  - two distinct flows rarely share a random high
                           source port AND identical bytes/packets/duration;
  4. concentration       - multi-label rows sit on a few attacker->victim
                           host pairs whose attacker ran several attack types.

    python -m leaf.forensics
Writes results/leaf/tables/E1b_*.csv
"""
from __future__ import annotations

import pandas as pd

from . import config as C
from repro import download

FEATS = C.FEATURE_SETS["ALL"]


def _key(labels: pd.Series) -> str:
    return "+".join(sorted(labels, key=str.lower))


def replication_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per distinct 12-feature vector that carries more than one label."""
    vl = df.groupby(FEATS + [C.ATTACK], sort=False).size().rename("n").reset_index()
    vec = vl.groupby(FEATS, sort=False).agg(
        n_labels=(C.ATTACK, "size"), k_min=("n", "min"), k_max=("n", "max"),
        rows=("n", "sum"), labels=(C.ATTACK, _key)).reset_index()
    return vec[vec["n_labels"] > 1].reset_index(drop=True)


def summarise(df: pd.DataFrame, multi: pd.DataFrame) -> pd.DataFrame:
    n_vec = df[FEATS].drop_duplicates().shape[0]
    s = [
        ("Distinct 12-feature vectors", n_vec),
        ("Vectors carrying >1 attack label", len(multi)),
        ("Rows in those vectors", int(multi["rows"].sum())),
        ("Share with equal label multiplicity (k_min = k_max)", (multi.k_min == multi.k_max).mean()),
        ("Share with rows = n_labels x k", (multi["rows"] == multi.n_labels * multi.k_min).mean()),
        ("Share with source port >= 1024", (multi[C.IDENTIFIERS[1]] >= 1024).mean()),
        ("Share with source port >= 49152", (multi[C.IDENTIFIERS[1]] >= 49152).mean()),
        ("Distinct source ports among them", multi[C.IDENTIFIERS[1]].nunique()),
        ("Share with FLOW_DURATION_MILLISECONDS > 0", (multi["FLOW_DURATION_MILLISECONDS"] > 0).mean()),
        ("Share with IN_BYTES > 100", (multi["IN_BYTES"] > 100).mean()),
    ]
    return pd.DataFrame(s, columns=["Statistic", "Value"])


def main() -> None:
    df = pd.read_csv(download.find_original_csv())
    multi = replication_table(df)
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)

    summ = summarise(df, multi)
    summ.to_csv(C.TABLE_DIR / "E1b_replication_summary.csv", index=False)

    combos = (multi.groupby("labels").agg(vectors=("rows", "size"), rows=("rows", "sum"))
              .sort_values("rows", ascending=False).reset_index())
    combos.to_csv(C.TABLE_DIR / "E1b_label_combinations.csv", index=False)

    mult = multi.groupby(["n_labels", "k_min"]).size().rename("vectors").reset_index()
    mult.columns = ["labels_per_vector", "copies_per_label", "vectors"]
    mult.to_csv(C.TABLE_DIR / "E1b_multiplicity.csv", index=False)

    src, dst = "IPV4_SRC_ADDR", "IPV4_DST_ADDR"
    pairs = multi.groupby([src, dst])["rows"].sum().sort_values(ascending=False).rename("multi_label_rows").reset_index()
    pairs["share"] = pairs["multi_label_rows"] / pairs["multi_label_rows"].sum()
    attacks = (df[df[C.LABEL] == 1].groupby(src)[C.ATTACK]
               .agg(lambda s: "+".join(sorted(s.unique(), key=str.lower))))
    pairs["attacks_run_by_source"] = pairs[src].map(attacks)
    pairs.to_csv(C.TABLE_DIR / "E1b_host_pairs.csv", index=False)

    print(summ.to_string(index=False))
    print("\nTop label combinations:\n" + combos.head(10).to_string(index=False))
    print(f"\nHost pairs: {len(pairs)}; top-10 share of multi-label rows = {pairs['share'].head(10).sum():.3f}")
    print(pairs.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
