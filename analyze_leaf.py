"""Turn the raw LEAF logs into paper tables and figures.

    python analyze_leaf.py

Reads results/leaf/raw/*.csv (+ predictions/*.npz) and writes
results/leaf/tables/*.csv and results/leaf/figures/*.png.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import kendalltau, spearmanr  # noqa: E402

from leaf import config as C  # noqa: E402

CLASSES = ["backdoor", "Benign", "ddos", "dos", "injection", "mitm", "password",
           "ransomware", "scanning", "xss"]
MODEL_ORDER = ["LR", "DT", "RF", "ET", "XGB", "LGBM", "MLP"]
COND_ORDER = [("naive", "ALL"), ("naive", "NOID"), ("controlled", "ALL"), ("controlled", "NOID")]
COND_LABEL = {("naive", "ALL"): "Naive split, all 12 features",
              ("naive", "NOID"): "Naive split, no identifiers",
              ("controlled", "ALL"): "Controlled split, all 12 features",
              ("controlled", "NOID"): "Controlled split, no identifiers"}
COLORS = ["#4e79a7", "#a0cbe8", "#f28e2b", "#ffbe7d"]
STRAT_COLORS = {"uniform": "#8c8c8c", "proportional": "#4e79a7",
                "dedup_proportional": "#59a14f", "floor": "#e15759"}


# --------------------------------------------------------------------------- #
def macro_f1_from_cm(cm):
    tp = np.diag(cm).astype(float)
    denom = cm.sum(0) + cm.sum(1)
    f1 = np.divide(2 * tp, denom, out=np.zeros_like(tp), where=denom > 0)
    return f1.mean()


def bootstrap_macro_f1(y, p, k, n_boot=300, seed=0):
    rng = np.random.default_rng(seed)
    n = len(y)
    code = y * k + p
    out = np.empty(n_boot)
    for b in range(n_boot):
        cm = np.bincount(code[rng.integers(0, n, n)], minlength=k * k).reshape(k, k)
        out[b] = macro_f1_from_cm(cm)
    return np.percentile(out, [2.5, 97.5])


def ci_for_e3(row):
    f = C.RAW_DIR / "predictions" / f"E3_{row.task}_{row.protocol}_{row.feature_set}_{row.model}.npz"
    if not f.exists():
        return (np.nan, np.nan)
    z = np.load(f)
    k = 10 if row.task == "multiclass" else 2
    return tuple(bootstrap_macro_f1(z["y_true"], z["y_pred"], k))


# --------------------------------------------------------------------------- #
def analyze_e3():
    f = C.RAW_DIR / "E3_protocol.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    cis = [ci_for_e3(r) for r in d.itertuples()]
    d["macro_f1_ci_low"] = [c[0] for c in cis]
    d["macro_f1_ci_high"] = [c[1] for c in cis]
    d.to_csv(C.TABLE_DIR / "E3_protocol_with_ci.csv", index=False)

    for task in d.task.unique():
        t = d[d.task == task]
        wide = t.pivot_table(index="model", columns=["protocol", "feature_set"],
                             values=["macro_f1", "accuracy"]).reindex(MODEL_ORDER)
        wide.to_csv(C.TABLE_DIR / f"E3_{task}_summary.csv")
        mf = t.pivot_table(index="model", columns=["protocol", "feature_set"], values="macro_f1")
        mf = mf.reindex(MODEL_ORDER)
        infl = pd.DataFrame({
            "naive_ALL": mf[("naive", "ALL")],
            "controlled_NOID": mf[("controlled", "NOID")],
            "inflation_pp": 100 * (mf[("naive", "ALL")] - mf[("controlled", "NOID")]),
            "due_to_split_pp (ALL)": 100 * (mf[("naive", "ALL")] - mf[("controlled", "ALL")]),
            "due_to_identifiers_pp (controlled)": 100 * (mf[("controlled", "ALL")] - mf[("controlled", "NOID")]),
        })
        infl.to_csv(C.TABLE_DIR / f"E3_{task}_inflation.csv")

        # Fig: grouped bars of macro-F1 under the 4 conditions
        fig, ax = plt.subplots(figsize=(11, 5))
        x, w = np.arange(len(MODEL_ORDER)), 0.2
        for i, cond in enumerate(COND_ORDER):
            vals = mf[cond].to_numpy() if cond in mf.columns else np.full(len(x), np.nan)
            sub = t.set_index(["model", "protocol", "feature_set"])
            lo = [sub.loc[(m, *cond), "macro_f1_ci_low"] if (m, *cond) in sub.index else np.nan for m in MODEL_ORDER]
            hi = [sub.loc[(m, *cond), "macro_f1_ci_high"] if (m, *cond) in sub.index else np.nan for m in MODEL_ORDER]
            err = np.vstack([vals - np.array(lo), np.array(hi) - vals])
            ax.bar(x + (i - 1.5) * w, vals, w, yerr=err, capsize=2, color=COLORS[i], label=COND_LABEL[cond])
        ax.set_xticks(x, MODEL_ORDER)
        ax.set_ylabel(f"Macro-F1 ({task})")
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
        ax.legend(loc="lower right", fontsize=9)
        ax.set_title(f"E3 - Effect of evaluation protocol and identifier features ({task}); "
                     "error bars: 95% bootstrap CI")
        fig.tight_layout()
        fig.savefig(C.FIG_DIR / f"E3_{task}_protocol_effect.png", dpi=300)
        plt.close(fig)

        if task == "multiclass":
            best = mf[("controlled", "NOID")].idxmax()
            rows = []
            for cond in COND_ORDER:
                r = t[(t.model == best) & (t.protocol == cond[0]) & (t.feature_set == cond[1])]
                if len(r):
                    rows.append(pd.Series(json.loads(r.iloc[0].per_class_f1), index=CLASSES, name=COND_LABEL[cond]))
            pc = pd.DataFrame(rows)
            pc.to_csv(C.TABLE_DIR / f"E3_per_class_f1_{best}.csv")
            fig, ax = plt.subplots(figsize=(11, 3.8))
            im = ax.imshow(pc.to_numpy(), cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
            ax.set_xticks(range(len(CLASSES)), CLASSES, rotation=30, ha="right")
            ax.set_yticks(range(len(pc)), pc.index)
            for i in range(pc.shape[0]):
                for j in range(pc.shape[1]):
                    ax.text(j, i, f"{pc.iat[i, j]:.2f}", ha="center", va="center", fontsize=9)
            fig.colorbar(im, ax=ax, fraction=0.03)
            ax.set_title(f"Per-class F1 of {best} under each protocol")
            fig.tight_layout()
            fig.savefig(C.FIG_DIR / "E3_per_class_f1_heatmap.png", dpi=300)
            plt.close(fig)
    return d


# --------------------------------------------------------------------------- #
def analyze_e4(e3):
    f = C.RAW_DIR / "E4_subset_fidelity.csv"
    if not f.exists() or e3 is None:
        return
    d = pd.read_csv(f)
    # The controlled training pool is already free of exact duplicates, so
    # dedup_proportional draws exactly the same rows as proportional. Keep it
    # only if it ever differs (e.g. if E4 is run on a raw pool).
    p = d[d.strategy == "proportional"].set_index(["feature_set", "budget", "seed", "model"])
    q = d[d.strategy == "dedup_proportional"].set_index(["feature_set", "budget", "seed", "model"])
    if len(q) and q["train_class_counts"].reindex(p.index).eq(p["train_class_counts"]).all():
        print("[E4] dedup_proportional == proportional on the controlled pool; dropped as redundant")
        d = d[d.strategy != "dedup_proportional"]
    ref = e3[(e3.task == "multiclass") & (e3.protocol == "controlled")]
    ref = ref.set_index(["feature_set", "model"])
    d["full_macro_f1"] = [ref.at[(r.feature_set, r.model), "macro_f1"] for r in d.itertuples()]
    d["gap_pp"] = 100 * (d.macro_f1 - d.full_macro_f1)
    pcf = np.array([json.loads(s) for s in d.per_class_f1])
    for j, c in enumerate(CLASSES):
        d[f"f1_{c}"] = pcf[:, j]

    # (a) performance & gap per strategy/budget (mean, sd over seeds)
    agg = d.groupby(["feature_set", "model", "strategy", "budget"]).agg(
        macro_f1_mean=("macro_f1", "mean"), macro_f1_sd=("macro_f1", "std"),
        gap_pp_mean=("gap_pp", "mean"), gap_pp_sd=("gap_pp", "std"),
        f1_ransomware_mean=("f1_ransomware", "mean"), f1_mitm_mean=("f1_mitm", "mean"),
        classes_in_train_min=("n_classes_in_train", "min")).reset_index()
    agg.to_csv(C.TABLE_DIR / "E4_subset_performance.csv", index=False)

    # (b) model-ranking agreement with the full-data ranking (Kendall tau)
    rk = []
    for (fs, s, b, seed), g in d.groupby(["feature_set", "strategy", "budget", "seed"]):
        g = g.set_index("model").reindex(MODEL_ORDER).dropna(subset=["macro_f1"])
        full = ref.loc[fs].reindex(g.index)["macro_f1"]
        tau = kendalltau(g.macro_f1, full).statistic
        best_same = g.macro_f1.idxmax() == full.idxmax()
        rk.append({"feature_set": fs, "strategy": s, "budget": b, "seed": seed,
                   "kendall_tau": tau, "same_best_model": best_same})
    rk = pd.DataFrame(rk)
    rk.to_csv(C.TABLE_DIR / "E4_ranking_agreement_raw.csv", index=False)
    rka = rk.groupby(["feature_set", "strategy", "budget"]).agg(
        tau_mean=("kendall_tau", "mean"), tau_sd=("kendall_tau", "std"),
        same_best_model_rate=("same_best_model", "mean")).reset_index()
    rka.to_csv(C.TABLE_DIR / "E4_ranking_agreement.csv", index=False)

    # (c) feature-importance agreement (tree ensembles) with full-data model
    imp = []
    for r in d.dropna(subset=["importance"]).itertuples():
        if (r.feature_set, r.model) not in ref.index or pd.isna(ref.at[(r.feature_set, r.model), "importance"]):
            continue
        a = np.array(json.loads(r.importance))
        b_ = np.array(json.loads(ref.at[(r.feature_set, r.model), "importance"]))
        imp.append({"feature_set": r.feature_set, "model": r.model, "strategy": r.strategy,
                    "budget": r.budget, "seed": r.seed, "spearman": spearmanr(a, b_).statistic})
    imp = pd.DataFrame(imp)
    if len(imp):
        imp.groupby(["feature_set", "model", "strategy", "budget"])["spearman"].agg(["mean", "std"]) \
           .reset_index().to_csv(C.TABLE_DIR / "E4_importance_agreement.csv", index=False)

    # Figures
    for fs in d.feature_set.unique():
        a = agg[agg.feature_set == fs]
        models_present = [m for m in MODEL_ORDER if m in a.model.unique()]
        fig, axes = plt.subplots(1, len(models_present), figsize=(3.1 * len(models_present), 3.6), sharey=True)
        axes = np.atleast_1d(axes)
        for ax, m in zip(axes, models_present):
            for s, col in STRAT_COLORS.items():
                q = a[(a.model == m) & (a.strategy == s)].sort_values("budget")
                ax.errorbar(q.budget, q.gap_pp_mean, yerr=q.gap_pp_sd, marker="o", ms=3,
                            capsize=2, color=col, label=s)
            ax.axhline(0, color="k", lw=0.8)
            ax.set_xscale("log")
            ax.set_title(m)
            ax.set_xlabel("training budget (rows)")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel("macro-F1 gap vs full data (pp)")
        axes[-1].legend(fontsize=7, loc="lower right")
        fig.suptitle(f"E4 - Fidelity of reduced training sets ({fs} features, controlled protocol)")
        fig.tight_layout()
        fig.savefig(C.FIG_DIR / f"E4_fidelity_gap_{fs}.png", dpi=300)
        plt.close(fig)

        r = rka[rka.feature_set == fs]
        fig, ax = plt.subplots(figsize=(6, 4))
        for s, col in STRAT_COLORS.items():
            q = r[r.strategy == s].sort_values("budget")
            ax.errorbar(q.budget, q.tau_mean, yerr=q.tau_sd, marker="o", capsize=3, color=col, label=s)
        ax.set_xscale("log")
        ax.set_ylim(-1.05, 1.05)
        ax.set_xlabel("training budget (rows)")
        ax.set_ylabel("Kendall tau vs full-data model ranking")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        ax.set_title(f"E4 - Does the subset rank models like the full data? ({fs})")
        fig.tight_layout()
        fig.savefig(C.FIG_DIR / f"E4_ranking_agreement_{fs}.png", dpi=300)
        plt.close(fig)


# --------------------------------------------------------------------------- #
def analyze_e5():
    f = C.RAW_DIR / "E5_internal_vs_external.csv"
    if not f.exists():
        return
    d = pd.read_csv(f)
    d["optimism_pp"] = 100 * (d.internal_macro_f1 - d.external_unseen_macro_f1)
    agg = d.groupby(["feature_set", "model"]).agg(
        internal=("internal_macro_f1", "mean"), internal_sd=("internal_macro_f1", "std"),
        external=("external_macro_f1", "mean"),
        external_unseen=("external_unseen_macro_f1", "mean"),
        external_unseen_sd=("external_unseen_macro_f1", "std"),
        optimism_pp=("optimism_pp", "mean"), optimism_pp_sd=("optimism_pp", "std")).reset_index()
    agg.to_csv(C.TABLE_DIR / "E5_internal_vs_external.csv", index=False)
    rare = d[["feature_set", "seed", "internal_test_class_counts"]].drop_duplicates(["feature_set", "seed"])
    rare = rare.assign(**{c: [json.loads(s)[j] for s in rare.internal_test_class_counts]
                          for j, c in enumerate(CLASSES)}).drop(columns="internal_test_class_counts")
    rare.to_csv(C.TABLE_DIR / "E5_internal_test_class_counts.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
    for ax, fs in zip(axes, ["ALL", "NOID"]):
        a = agg[agg.feature_set == fs].set_index("model").reindex(MODEL_ORDER)
        x, w = np.arange(len(a)), 0.27
        ax.bar(x - w, a.internal, w, yerr=a.internal_sd, capsize=2, color="#4e79a7",
               label="internal (80/20 split of published subset)")
        ax.bar(x, a.external, w, color="#a0cbe8", label="external: all flows outside subset")
        ax.bar(x + w, a.external_unseen, w, yerr=a.external_unseen_sd, capsize=2, color="#e15759",
               label="external: unseen feature vectors only")
        ax.set_xticks(x, a.index)
        ax.set_title(f"{fs} features")
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("Macro-F1 (multiclass)")
    axes[1].legend(fontsize=8, loc="lower right")
    fig.suptitle("E5 - Scores measured inside the published 49,997-row subset vs. on the rest of NF-ToN-IoT")
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "E5_internal_vs_external.png", dpi=300)
    plt.close(fig)


def analyze_e1_e2():
    f = C.TABLE_DIR / "E1_integrity_per_class.csv"
    if f.exists():
        pc = pd.read_csv(f)
        fig, axes = plt.subplots(1, 2, figsize=(14, 4.2), sharey=True)
        for ax, fs in zip(axes, ["ALL", "NOID"]):
            x, w = np.arange(len(pc)), 0.38
            ax.bar(x - w / 2, pc[f"Unambiguous % [dedup, {fs}]"], w, color="#4e79a7",
                   label="unambiguous (vector unique to the class)")
            ax.bar(x + w / 2, pc[f"Recall upper bound % [dedup, {fs}]"], w, color="#f28e2b",
                   label="recall upper bound (class is a majority label)")
            ax.set_xticks(x, pc.Class, rotation=30, ha="right")
            ax.set_title(f"{fs} features (de-duplicated data)")
            ax.grid(axis="y", alpha=0.3)
        axes[0].set_ylabel("% of the class's flows")
        axes[0].legend(fontsize=8, loc="lower left")
        fig.suptitle("E1 - Per-class separability bounds implied by identical feature vectors")
        fig.tight_layout()
        fig.savefig(C.FIG_DIR / "E1_separability_bounds.png", dpi=300)
        plt.close(fig)
    f = C.TABLE_DIR / "E2_shortcut_audit.csv"
    if f.exists():
        d = pd.read_csv(f)
        d = d[(d.Protocol == "controlled")]
        for task in d.Task.unique():
            q = d[d.Task == task].sort_values("F1")
            fig, ax = plt.subplots(figsize=(8, 5))
            col = q.Group.map({"identifier": "#e15759", "flow": "#4e79a7", "mixed": "#8c8c8c"})
            ax.barh(q["Feature(s)"], q.F1, color=col)
            ax.set_xlabel("F1 (binary: attack-F1; multiclass: macro-F1)")
            ax.set_title(f"E2 - Predictive power of single features / groups ({task}); red = identifier")
            ax.grid(axis="x", alpha=0.3)
            fig.tight_layout()
            fig.savefig(C.FIG_DIR / f"E2_shortcut_{task}.png", dpi=300)
            plt.close(fig)


def analyze_tolerant():
    """Label-tolerant re-scoring of E3 multiclass predictions.

    A prediction is 'tolerantly correct' if the dataset itself assigns that
    label to the very same 12-feature record somewhere (NF-ToN-IoT replicates
    records across attack classes). This separates model error from label
    replication."""
    files = sorted((C.RAW_DIR / "predictions").glob("E3_multiclass_*.npz"))
    if not files:
        return
    from leaf import data
    df = data.load()
    y, names = data.class_codes(df, "multiclass")
    codes, _ = pd.factorize(pd.Series(data.vector_hash(df, C.FEATURE_SETS["ALL"])))
    mask = np.zeros(codes.max() + 1, np.int64)
    np.bitwise_or.at(mask, codes, (1 << y).astype(np.int64))
    row_mask = mask[codes]
    n_labels = np.array([bin(int(m)).count("1") for m in range(1 << len(names))])[row_mask]
    out = []
    for f in files:
        _, task, proto, fs, model = f.stem.split("_")
        z = np.load(f)
        te, yt, yp = z["test_idx"], z["y_true"], z["y_pred"]
        tol = ((row_mask[te] >> yp) & 1).astype(bool)
        amb = n_labels[te] > 1
        out.append({"protocol": proto, "feature_set": fs, "model": model,
                    "strict_accuracy": (yp == yt).mean(), "tolerant_accuracy": tol.mean(),
                    "share_test_rows_with_replicated_labels": amb.mean(),
                    "strict_acc_on_unambiguous_rows": (yp[~amb] == yt[~amb]).mean(),
                    "strict_acc_on_ambiguous_rows": (yp[amb] == yt[amb]).mean(),
                    "tolerant_acc_on_ambiguous_rows": tol[amb].mean()})
    res = pd.DataFrame(out)
    res["model"] = pd.Categorical(res.model, MODEL_ORDER)
    res = res.sort_values(["protocol", "feature_set", "model"])
    res.to_csv(C.TABLE_DIR / "E3_label_tolerant_accuracy.csv", index=False)
    return res


if __name__ == "__main__":
    C.ensure_dirs()
    analyze_e1_e2()
    analyze_tolerant()
    e3 = analyze_e3()
    analyze_e4(e3)
    analyze_e5()
    print("analysis written to", C.OUT_DIR)
