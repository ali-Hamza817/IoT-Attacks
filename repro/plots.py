"""Figures 2-4 of the paper, drawn with matplotlib only."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402

FULL_C, SUB_C = "#66c2a5", "#fc8d62"  # teal / orange used for full vs sub


def fig2_class_distribution(full: pd.DataFrame, sub: pd.DataFrame, path) -> None:
    pf = full[config.ATTACK_COL].value_counts(normalize=True) * 100
    ps = sub[config.ATTACK_COL].value_counts(normalize=True) * 100
    cats = sorted(pf.index, key=str.lower)
    x, w = np.arange(len(cats)), 0.38
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - w / 2, pf[cats], w, label="NF-ToN-IoT V1 dataset", color="tab:blue")
    ax.bar(x + w / 2, ps.reindex(cats).fillna(0), w, label="Downsampled dataset", color="tab:orange")
    for xi, v in zip(x, pf[cats]):
        ax.text(xi, v + 0.6, f"{v:.2f}%", ha="center", fontsize=10)
    ax.set_xticks(x, cats, rotation=45, ha="right")
    ax.set_xlabel("Attack Categories")
    ax.set_ylabel("Class Proportion (%)")
    ax.set_ylim(0, pf.max() * 1.12)
    ax.legend(fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig3_boxplots(full: pd.DataFrame, sub: pd.DataFrame, path) -> None:
    feats = config.NUMERICAL_FEATURES
    fig, ax = plt.subplots(figsize=(12, 7))
    pos_full = np.arange(len(feats)) * 2.0 - 0.4
    pos_sub = np.arange(len(feats)) * 2.0 + 0.4
    common = dict(widths=0.75, patch_artist=True, showfliers=True,
                  medianprops=dict(color="#444"), whiskerprops=dict(color="#666"),
                  capprops=dict(color="#666"),
                  flierprops=dict(marker="o", markersize=3, markerfacecolor="none",
                                  markeredgecolor="#555", alpha=0.6))
    b1 = ax.boxplot([full[f].to_numpy() for f in feats], positions=pos_full, **common)
    b2 = ax.boxplot([sub[f].to_numpy() for f in feats], positions=pos_sub, **common)
    for b, col in ((b1, FULL_C), (b2, SUB_C)):
        for patch in b["boxes"]:
            patch.set_facecolor(col)
            patch.set_edgecolor("#666")
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.5)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xticks(np.arange(len(feats)) * 2.0, feats, rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.4)
    ax.legend([b1["boxes"][0], b2["boxes"][0]],
              ["NF-ToN-IoT V1 Dataset", "Downsampled Dataset"], title="Dataset", loc="upper right")
    ax.set_title("Comparison of Distribution Shape and Outliers (Log Scale)\n"
                 "Across Numerical Features in the NF-ToN-IoT V1 Dataset and Its Downsampled Version")
    ax.set_xlabel("Numerical Feature")
    ax.set_ylabel("Feature Value (Log Scale)")
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def _heatmap(ax, corr: pd.DataFrame, title: str):
    im = ax.imshow(corr.to_numpy(), cmap="coolwarm", vmin=corr.to_numpy().min(), vmax=1.0)
    labels = list(corr.columns)
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            v = corr.iat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color="white" if v > 0.8 or v < 0.15 else "black", fontsize=10)
    ax.set_title(title)
    return im


def fig4_correlations(corr_full: pd.DataFrame, corr_sub: pd.DataFrame, path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    im1 = _heatmap(axes[0], corr_full, "Correlation Matrix - NF-ToN-IoT V1")
    im2 = _heatmap(axes[1], corr_sub, "Correlation Matrix - Downsampled Dataset")
    fig.colorbar(im1, ax=axes[0], fraction=0.046)
    fig.colorbar(im2, ax=axes[1], fraction=0.046)
    fig.suptitle("Feature Correlation Matrices Comparison\nBetween the NF-ToN-IoT V1 Dataset "
                 "and Its Proportionally Downsampled Counterpart")
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)
