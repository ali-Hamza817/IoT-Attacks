"""Analysis of E6 (evaluation fidelity of reduced datasets).

Reads results/leaf/raw/E6_fidelity.csv (560 fits = 16 configs x 5 seeds x 7
models) and computes, for every config and metric, the fidelity measures fixed
in docs/task2_design.md before the run:

  gap        mean |internal - external| over the 35 fits, and the mean signed
             gap (internal - external; > 0 means the subset is optimistic)
  ranking    Kendall tau-b between the internal and the external 7-model
             ranking, per seed; mean, sd, and how often the internal winner is
             also the external winner
  stability  sd of the internal score over the 5 seeds, averaged over models
  support    smallest internal per-class test support over the 5 seeds, and
             mean number of classes with < 10 internal test records

H2 factor contrasts compare configs that differ in exactly one factor.

Post-hoc sensitivity (added after the run, reported separately): when a class
has no external records (e.g. floor sampling puts every ransomware record into
the subset), the pre-registered external balanced consistency averages over
fewer classes than the internal one. "balanced_matched" averages both sides
over the classes present in BOTH the internal test part and the external set.

    python -m leaf.analyze_e6
Writes results/leaf/tables/E6_*.csv and results/leaf/figures/E6_*.png
"""
from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import kendalltau, mannwhitneyu, wilcoxon  # noqa: E402

from . import config as C  # noqa: E402
from .fidelity import METRICS, config_name, configs  # noqa: E402

PRIMARY = "balanced_consistency"
MATCHED = "balanced_matched"
PAPER = "raw|published|random|ALL"
LEAF = "consolidated|floor|disjoint|NOID"
ORDER = [config_name(c) for c in configs()]
FACTORS = ["labels", "sampling", "protocol", "features"]


def load() -> pd.DataFrame:
    d = _read(C.RAW_DIR / "E6_fidelity.csv")
    n = d.groupby("config").size()
    assert len(n) == 16 and (n == 35).all(), n
    return d


def _read(path) -> pd.DataFrame:
    d = pd.read_csv(path)
    assert not d.duplicated(["config", "seed", "model"]).any()
    pi = np.array([json.loads(x) for x in d["internal_per_class"]], float)
    pe = np.array([json.loads(x) for x in d["external_per_class"]], float)
    si = np.array([json.loads(x) for x in d["internal_support"]])
    se = np.array([json.loads(x) for x in d["external_support"]])
    both = (si > 0) & (se > 0)
    d[f"internal_{MATCHED}"] = np.nanmean(np.where(both, pi, np.nan), axis=1)
    d[f"external_{MATCHED}"] = np.nanmean(np.where(both, pe, np.nan), axis=1)
    d["classes_scored_both"] = both.sum(1)
    d["classes_external_absent"] = (se == 0).sum(1)
    return d


def fidelity(d: pd.DataFrame, metric: str) -> pd.DataFrame:
    i, e = f"internal_{metric}", f"external_{metric}"
    d = d.assign(gap=d[i] - d[e])
    rows = []
    for cname, g in d.groupby("config", sort=False):
        taus, top1 = [], []
        for _, s in g.groupby("seed"):
            taus.append(kendalltau(s[i], s[e]).statistic)
            top1.append(s.loc[s[i].idxmax(), "model"] == s.loc[s[e].idxmax(), "model"])
        r = g.iloc[0]
        rows.append({
            "config": cname, **{f: r[f] for f in FACTORS}, "metric": metric,
            "internal_mean": g[i].mean(), "external_mean": g[e].mean(),
            "abs_gap_mean": g["gap"].abs().mean(), "abs_gap_max": g["gap"].abs().max(),
            "signed_gap_mean": g["gap"].mean(),
            "tau_mean": np.mean(taus), "tau_sd": np.std(taus, ddof=1),
            "tau_min": np.min(taus), "top1_agree": int(np.sum(top1)),
            "internal_seed_sd": g.groupby("model")[i].std(ddof=1).mean(),
            "external_seed_sd": g.groupby("model")[e].std(ddof=1).mean(),
            "min_internal_class_support": g["internal_min_class_support"].min(),
            "classes_lt10_mean": g["internal_classes_lt10"].mean(),
            "n_internal_test_mean": g["n_internal_test"].mean(),
            "n_external_mean": g["n_external"].mean(),
            "classes_external_absent_max": g["classes_external_absent"].max(),
        })
    out = pd.DataFrame(rows)
    out["config"] = pd.Categorical(out["config"], ORDER, ordered=True)
    return out.sort_values("config").reset_index(drop=True)


# measure -> True if larger is better
MEASURES = {"abs_gap_mean": False, "tau_mean": True, "internal_seed_sd": False}


def contrasts(fid: pd.DataFrame) -> pd.DataFrame:
    """Pairs of configs that differ in exactly one LEAF factor."""
    steps = {"protocol": ("random", "disjoint"), "sampling": ("proportional", "floor"),
             "labels": ("raw", "consolidated"), "features": ("ALL", "NOID")}
    rows = []
    for factor, (a, b) in steps.items():
        others = [f for f in FACTORS if f != factor]
        A = fid[fid[factor] == a].set_index(others)
        B = fid[fid[factor] == b].set_index(others)
        for key in A.index.intersection(B.index):
            ra, rb = A.loc[key], B.loc[key]
            row = {"factor": factor, "from": ra["config"], "to": rb["config"]}
            improved = []
            for m, higher in MEASURES.items():
                row[f"{m}_from"], row[f"{m}_to"] = ra[m], rb[m]
                delta = rb[m] - ra[m]
                row[f"{m}_delta"] = delta
                better = delta > 0 if higher else delta < 0
                row[f"{m}_improved"] = bool(better)
                if better:
                    improved.append(m)
            row["improves_any"] = bool(improved)
            rows.append(row)
    return pd.DataFrame(rows)


def figures(fid: pd.DataFrame) -> None:
    f = fid[fid.metric == PRIMARY].reset_index(drop=True)
    y = np.arange(len(f))[::-1]
    lab = f["config"].astype(str).tolist()
    blue, orange, ink, grid = "#2a78d6", "#eb6834", "#52514e", "#e4e3df"
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.4), sharey=True,
                             gridspec_kw={"width_ratios": [1.3, 1, 1]})
    ax = axes[0]
    for yy, (_, r) in zip(y, f.iterrows()):
        ax.plot([r.external_mean, r.internal_mean], [yy, yy], color=grid, lw=2, zorder=1)
    ax.scatter(f.internal_mean, y, s=48, color=blue, label="internal (subset 20% test)", zorder=3,
               edgecolor="white", linewidth=1.5)
    ax.scatter(f.external_mean, y, s=48, color=orange, marker="D", label="external (unseen rest of data)",
               zorder=2, edgecolor="white", linewidth=1.5)
    ax.set_xlabel("Balanced consistency, mean of 35 fits")
    ax.legend(loc="lower left", fontsize=8, frameon=False)
    ax.set_title("Score levels", loc="left", fontsize=10)
    ax = axes[1]
    ax.barh(y, f.signed_gap_mean, color=blue, height=0.6)
    ax.axvline(0, color=ink, lw=0.8)
    ax.set_xlabel("Mean signed gap (internal - external)")
    ax.set_title("Optimism of internal estimate", loc="left", fontsize=10)
    ax = axes[2]
    ax.errorbar(f.tau_mean, y, xerr=f.tau_sd, fmt="o", color=blue, ecolor=ink, elinewidth=1,
                capsize=2, markersize=6)
    ax.axvline(1, color=grid, lw=1)
    ax.set_xlabel("Kendall tau, internal vs external 7-model ranking\n(mean +/- sd over 5 seeds)")
    ax.set_xlim(-0.2, 1.05)
    ax.set_title("Model-ranking agreement", loc="left", fontsize=10)
    axes[0].set_yticks(y, lab, fontsize=8)
    for ax in axes:
        ax.grid(axis="x", color=grid, lw=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=ink, labelsize=8)
    for t in axes[0].get_yticklabels():
        if t.get_text() in (PAPER, LEAF):
            t.set_fontweight("bold")
    fig.suptitle("E6 - does a 50k-row subset predict results on unseen NF-ToN-IoT V1 data? "
                 "(pre-registered metric; raw and consolidated levels are not comparable)",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "E6_fidelity_overview.png", dpi=300)
    plt.close(fig)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    C.FIG_DIR.mkdir(parents=True, exist_ok=True)
    d = load()
    fid = pd.concat([fidelity(d, m) for m in METRICS + [MATCHED]], ignore_index=True)
    fid.to_csv(C.TABLE_DIR / "E6_fidelity_summary.csv", index=False)
    prim = fid[fid.metric == PRIMARY]
    con = pd.concat([contrasts(fid[fid.metric == m]).assign(metric=m) for m in (PRIMARY, MATCHED)],
                    ignore_index=True)
    con.to_csv(C.TABLE_DIR / "E6_factor_contrasts.csv", index=False)

    # internal / external score per model, primary metric (mean over seeds)
    pm = (d.groupby(["config", "model"])[[f"internal_{PRIMARY}", f"external_{PRIMARY}"]].mean()
          .reset_index())
    pm["config"] = pd.Categorical(pm["config"], ORDER, ordered=True)
    pm.sort_values(["config", "model"]).to_csv(C.TABLE_DIR / "E6_per_model.csv", index=False)
    figures(fid)

    cols = ["config", "internal_mean", "external_mean", "abs_gap_mean", "signed_gap_mean",
            "tau_mean", "tau_sd", "top1_agree", "internal_seed_sd", "min_internal_class_support",
            "classes_lt10_mean", "classes_external_absent_max"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        for metric in (PRIMARY, MATCHED):
            f = fid[fid.metric == metric]
            print(f"===== {metric} =====")
            print(f[cols].round(4).to_string(index=False))
            print()
            for (factor), g in con[con.metric == metric].groupby("factor", sort=False):
                print(f"[{factor}] pairs={len(g)} improves_any={g.improves_any.sum()} | "
                      + " ".join(f"{m}:{g[m + '_improved'].sum()}/{len(g)}" for m in MEASURES))
            p, l = f.set_index("config").loc[PAPER], f.set_index("config").loc[LEAF]
            print()
            for m in ["abs_gap_mean", "signed_gap_mean", "tau_mean", "tau_sd", "top1_agree",
                      "internal_seed_sd", "min_internal_class_support"]:
                print(f"{m:28s} paper={p[m]:.4f}  leaf={l[m]:.4f}")
            print()


# --------------------------------------------------------------------------- #
# E6b: confirmatory extension, 20 seeds (0-4 from E6, 5-19 from E6b)
# --------------------------------------------------------------------------- #
def per_seed(d: pd.DataFrame, metric: str) -> pd.DataFrame:
    i, e = f"internal_{metric}", f"external_{metric}"
    rows = []
    for (cname, seed), g in d.groupby(["config", "seed"], sort=False):
        rows.append({"config": cname, "seed": seed, "metric": metric,
                     "tau": kendalltau(g[i], g[e]).statistic,
                     "abs_gap": (g[i] - g[e]).abs().mean(), "signed_gap": (g[i] - g[e]).mean(),
                     "top1_agree": g.loc[g[i].idxmax(), "model"] == g.loc[g[e].idxmax(), "model"],
                     # external score lost by choosing the internal winner (post hoc)
                     "regret": g[e].max() - g.loc[g[i].idxmax(), e],
                     "top2_external_margin": np.sort(g[e].to_numpy())[-1] - np.sort(g[e].to_numpy())[-2],
                     "internal_mean": g[i].mean(), "external_mean": g[e].mean()})
    return pd.DataFrame(rows)


def _boot_ci(x, n=10_000, seed=0):
    rng = np.random.default_rng(seed)
    m = rng.choice(x, size=(n, len(x)), replace=True).mean(1)
    return np.percentile(m, [2.5, 97.5])


def analyze_e6b() -> None:
    from .fidelity import E6B_CONFIGS
    path = C.RAW_DIR / "E6b_more_seeds.csv"
    if not path.exists():
        print("[E6b] no results yet"); return
    d = pd.concat([load(), _read(path)], ignore_index=True)
    d = d[d.config.isin(E6B_CONFIGS)]
    n = d.groupby("config").size()
    assert (n == 140).all(), f"E6b incomplete: {n.to_dict()}"
    ps = pd.concat([per_seed(d, m) for m in (PRIMARY, MATCHED)], ignore_index=True)
    ps.to_csv(C.TABLE_DIR / "E6b_per_seed.csv", index=False)
    rows, tests = [], []
    for metric, g in ps.groupby("metric", sort=False):
        dm = d.assign()
        sd = dm.groupby(["config", "model"])[f"internal_{metric}"].std(ddof=1).groupby("config").mean()
        for cname in E6B_CONFIGS:
            x = g[g.config == cname]
            r = {"metric": metric, "config": cname, "n_seeds": len(x)}
            for k in ("tau", "abs_gap", "signed_gap", "regret", "top2_external_margin"):
                lo, hi = _boot_ci(x[k].to_numpy())
                r.update({f"{k}_mean": x[k].mean(), f"{k}_sd": x[k].std(ddof=1),
                          f"{k}_ci_lo": lo, f"{k}_ci_hi": hi})
            r["top1_agree"] = f"{int(x.top1_agree.sum())}/{len(x)}"
            r["internal_seed_sd"] = sd[cname]
            rows.append(r)
        # seeds "all" = 0-19; "fresh" = 5-19 only, i.e. seeds not seen when the
        # matched-class metric was defined (the strict test for balanced_matched)
        for seeds_name, keep in (("all_0_19", lambda x: x >= 0), ("fresh_5_19", lambda x: x >= 5)):
            gg = g[keep(g.seed)]
            a = gg[gg.config == PAPER].set_index("seed")
            for other, paired in (("raw|published|disjoint|ALL", True), (LEAF, False)):
                b = gg[gg.config == other].set_index("seed").loc[a.index]
                for k in ("tau", "abs_gap", "regret"):
                    if paired:   # same subset (the authors' file) and same seed: paired test
                        test = "wilcoxon_signed_rank"
                        p = wilcoxon(a[k], b[k]).pvalue if (a[k] != b[k]).any() else 1.0
                    else:        # independent subset draws: unpaired test
                        test, p = "mann_whitney_u", mannwhitneyu(a[k], b[k], alternative="two-sided").pvalue
                    tests.append({"metric": metric, "seeds": seeds_name, "measure": k, "a": PAPER, "b": other,
                                  "test": test, "n": len(a), "a_mean": a[k].mean(), "b_mean": b[k].mean(),
                                  "p_two_sided": p})
    summ, tst = pd.DataFrame(rows), pd.DataFrame(tests)
    summ.to_csv(C.TABLE_DIR / "E6b_summary.csv", index=False)
    tst.to_csv(C.TABLE_DIR / "E6b_tests.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(summ.round(4).to_string(index=False)); print()
        print(tst.round(4).to_string(index=False))

    # figure: per-seed tau and |gap|; one extra row for LEAF on matched classes
    # (for raw configs no class is missing externally, so matched == primary)
    rows_ = [(c, ps[(ps.metric == PRIMARY) & (ps.config == c)]) for c in E6B_CONFIGS]
    rows_.append((LEAF + "\nmatched classes (post hoc)", ps[(ps.metric == MATCHED) & (ps.config == LEAF)]))
    rows_ = rows_[::-1]
    blue, ink, grid = "#2a78d6", "#52514e", "#e4e3df"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    rng = np.random.default_rng(0)
    for ax, k, xl in ((axes[0], "tau", "Kendall tau, internal vs external 7-model ranking"),
                      (axes[1], "abs_gap", "Mean |internal - external| balanced consistency")):
        for yy, (_, x) in enumerate(rows_):
            x = x[k].to_numpy()
            ax.scatter(x, yy + rng.uniform(-0.15, 0.15, len(x)), s=22, color=blue, alpha=0.75,
                       edgecolor="white", linewidth=0.8)
            ax.plot([x.mean()] * 2, [yy - 0.3, yy + 0.3], color=ink, lw=2)
        ax.set_xlabel(xl, fontsize=9)
        ax.grid(axis="x", color=grid, lw=0.6); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(colors=ink, labelsize=8)
    axes[0].set_yticks(range(len(rows_)), [r[0] for r in rows_], fontsize=8)
    fig.suptitle("E6b - 20 seeds per configuration (dots = seeds, bar = mean)", x=0.01, ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "E6b_seed_distributions.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
    analyze_e6b()
