"""E1 - data-integrity audit and E2 - shortcut (spurious-feature) audit."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.tree import DecisionTreeClassifier

from . import config as C
from .data import class_codes, exact_duplicate_mask, vector_hash


# --------------------------------------------------------------------------- #
# E1 - integrity
# --------------------------------------------------------------------------- #
def bayes_ceiling(groups: np.ndarray, y: np.ndarray, n_classes: int) -> dict:
    """Upper bounds for ANY classifier that sees only these features.

    Rows with the same feature vector must get the same prediction, so the
    best achievable accuracy is obtained by predicting each vector's majority
    class. Ties do not change this bound.

    Per class we report two bounds that do not depend on how ties are broken:
      * unambiguous share: rows of c whose vector holds only class c (an
        accuracy-optimal classifier always gets these right);
      * recall upper bound: rows of c whose vector has c among its majority
        classes (no accuracy-optimal classifier can do better on c).
    Also returned: the share of conflicting vectors in which all classes
    have exactly equal multiplicity (a sign of records replicated across
    attack captures).
    """
    t = pd.DataFrame({"g": groups, "y": y}).value_counts().rename("n").reset_index()
    gmax = t.groupby("g")["n"].transform("max")
    gk = t.groupby("g")["y"].transform("size")
    acc = t.loc[t["n"] == gmax].drop_duplicates("g")["n"].sum() / len(y)
    support = np.bincount(y, minlength=n_classes)
    unamb = t[gk == 1].groupby("y")["n"].sum().reindex(range(n_classes), fill_value=0)
    upper = t[t["n"] == gmax].groupby("y")["n"].sum().reindex(range(n_classes), fill_value=0)
    conf = t[gk > 1]
    eq = conf.groupby("g")["n"].agg(lambda s: s.nunique() == 1) if len(conf) else pd.Series(dtype=bool)
    return {"accuracy_ceiling": acc,
            "per_class_unambiguous": (unamb / support).to_numpy(),
            "per_class_recall_upper": (upper / support).to_numpy(),
            "conflict_vectors": int(len(eq)),
            "conflict_vectors_equal_multiplicity": float(eq.mean()) if len(eq) else np.nan}


def integrity_audit(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Duplicate, conflict and separability statistics.

    Returns (summary table, per-class table).
    """
    y, names = class_codes(df, "multiclass")
    yb, _ = class_codes(df, "binary")
    dup = exact_duplicate_mask(df)
    rows, per_class = [], {"Class": names, "Rows": np.bincount(y),
                           "Exact-duplicate rows": np.bincount(y[dup], minlength=len(names))}
    rows.append(("Records", len(df), 100.0))
    rows.append(("Exact duplicate rows (all 14 columns)", int(dup.sum()), 100 * dup.mean()))

    for view, mask in (("raw", np.ones(len(df), bool)), ("dedup", ~dup)):
        d, yy, yyb = df[mask], y[mask], yb[mask]
        for fs, feats in C.FEATURE_SETS.items():
            g = vector_hash(d, feats)
            gs = pd.Series(g)
            repeated = gs.duplicated(keep=False).to_numpy()
            n_lab = pd.DataFrame({"g": g, "y": yy}).groupby("g")["y"].nunique()
            conflict = gs.map(n_lab).to_numpy() > 1
            n_lab_b = pd.DataFrame({"g": g, "y": yyb}).groupby("g")["y"].nunique()
            conflict_b = gs.map(n_lab_b).to_numpy() > 1
            bc = bayes_ceiling(g, yy, len(names))
            bb = bayes_ceiling(g, yyb, 2)
            p = f"[{view}, {fs}]"
            rows += [
                (f"{p} unique feature vectors", int(gs.nunique()), 100 * gs.nunique() / len(d)),
                (f"{p} rows sharing their vector with another row", int(repeated.sum()), 100 * repeated.mean()),
                (f"{p} rows in vectors with >1 attack class", int(conflict.sum()), 100 * conflict.mean()),
                (f"{p} rows in vectors with both Benign and Attack", int(conflict_b.sum()), 100 * conflict_b.mean()),
                (f"{p} multiclass accuracy ceiling (%)", None, 100 * bc["accuracy_ceiling"]),
                (f"{p} binary accuracy ceiling (%)", None, 100 * bb["accuracy_ceiling"]),
                (f"{p} multi-class vectors", bc["conflict_vectors"], None),
                (f"{p} ... of which all classes have equal multiplicity (%)", None,
                 100 * bc["conflict_vectors_equal_multiplicity"]),
            ]
            per_class[f"Unambiguous % [{view}, {fs}]"] = 100 * bc["per_class_unambiguous"]
            per_class[f"Recall upper bound % [{view}, {fs}]"] = 100 * bc["per_class_recall_upper"]
    summary = pd.DataFrame(rows, columns=["Statistic", "Count", "Percent"])
    pc = pd.DataFrame(per_class)
    pc["Exact-duplicate %"] = 100 * pc["Exact-duplicate rows"] / pc["Rows"]
    return summary, pc


def conflict_cooccurrence(df: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """For each class A (row) and class B (column): % of A's distinct records
    (feature vectors) that also occur with label B. Diagonal = % of A's
    records that occur with A only."""
    _, names = class_codes(df, "multiclass")
    d = df[feats + [C.ATTACK]].drop_duplicates()
    g = vector_hash(d, feats)
    lab = pd.crosstab(g, d[C.ATTACK].to_numpy()).reindex(columns=names, fill_value=0) > 0
    k = lab.sum(axis=1)
    out = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        mine = lab[lab[a]]
        for b in names:
            out.at[a, b] = 100 * ((k[mine.index] == 1).mean() if a == b else mine[b].mean())
    out.index.name = "class \\ also labelled as"
    return out


# --------------------------------------------------------------------------- #
# E2 - shortcut audit
# --------------------------------------------------------------------------- #
def single_feature_power(df, tr, te, task: str, seed: int = 0) -> pd.DataFrame:
    """Predictive power of each feature alone, and of the identifier / flow
    groups. A shallow-capacity tree (<=1024 leaves) is used, which is enough to
    memorise individual IP addresses or ports."""
    y, _ = class_codes(df, task)
    avg = "binary" if task == "binary" else "macro"
    specs = [(f, [f]) for f in C.FEATURE_SETS["ALL"]]
    specs += [("<identifiers only>", C.IDENTIFIERS), ("<flow features only>", C.FLOW_FEATURES),
              ("<all 12 features>", C.FEATURE_SETS["ALL"])]
    out = []
    for name, cols in specs:
        m = DecisionTreeClassifier(max_leaf_nodes=1024, random_state=seed)
        m.fit(df.iloc[tr][cols].to_numpy(), y[tr])
        p = m.predict(df.iloc[te][cols].to_numpy())
        out.append({"Task": task, "Feature(s)": name,
                    "Group": "identifier" if set(cols) <= set(C.IDENTIFIERS) else
                             ("flow" if set(cols) <= set(C.FLOW_FEATURES) else "mixed"),
                    "Accuracy": accuracy_score(y[te], p),
                    "F1": f1_score(y[te], p, average=avg, zero_division=0)})
    return pd.DataFrame(out)
