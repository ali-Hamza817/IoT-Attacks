"""Run the full five-step framework end to end and check it against the paper.

    python run_pipeline.py              # download (if needed) + run everything
    python run_pipeline.py --no-download

Outputs
    data/processed/Downsampled_NF-ToN-IoT_V1_reproduced.csv
    results/tables/*.csv
    results/figures/fig2_*.png, fig3_*.png, fig4_*.png
    results/reproduction_report.md
"""
from __future__ import annotations

import argparse
import json
import time

import pandas as pd

from repro import compare, config, download, downsampling, eda, plots


def md_table(df: pd.DataFrame, floatfmt: str = "{:,.6g}") -> str:
    def fmt(v):
        if isinstance(v, float):
            return floatfmt.format(v)
        if isinstance(v, (bool,)):
            return "✅" if v else "❌"
        return str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    body = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, sep, *body])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-download", action="store_true", help="use files already on disk")
    args = ap.parse_args()
    config.ensure_dirs()
    t0 = time.time()

    # ---------------- data acquisition ---------------- #
    if args.no_download:
        csv = download.find_original_csv()
        if csv is None:
            raise SystemExit("original CSV not found; run without --no-download first")
    else:
        csv = download.download_original()
        download.download_reference()

    full = eda.load_dataset(csv)
    print(f"[load] {full.shape[0]:,} rows x {full.shape[1]} columns")

    # ---------------- Phase 1: EDA ---------------- #
    res: dict = {}
    res["overview"] = eda.dataset_overview(full)                 # Step 1
    res["table2"] = eda.feature_classification(full)             # Step 1 + 2
    res["missing"] = eda.missing_values(full)                    # Step 2
    res["table3"] = eda.categorical_summary(full)                # Step 3
    res["top_freq"] = eda.top_frequencies(full)                  # Step 3
    res["num_full"] = eda.numerical_summary(full)                # Step 4
    res["corr_full"] = eda.correlation_matrix(full)

    # ---------------- Phase 2: Step 5 ---------------- #
    alloc = downsampling.class_allocation(full[config.ATTACK_COL])
    sub = downsampling.stratified_downsample(full)
    sub.to_csv(config.REPRODUCED_CSV, index=False)
    res["sub_n"] = len(sub)
    res["table4"] = downsampling.class_distribution_table(full, sub)
    res["num_sub"] = eda.numerical_summary(sub)
    res["corr_sub"] = eda.correlation_matrix(sub)
    print(f"[step5] downsampled to {len(sub):,} rows -> {config.REPRODUCED_CSV.name}")

    ref_check = None
    if config.REFERENCE_CSV.exists():
        ref = eda.load_dataset(config.REFERENCE_CSV)
        ref_check = downsampling.compare_with_reference(sub, ref)
        print(f"[step5] vs authors' published subset: {ref_check}")

    # ---------------- save tables ---------------- #
    T = config.TABLES_DIR
    res["table2"].to_csv(T / "table2_feature_classification_zero_values.csv", index=False)
    res["missing"].to_csv(T / "step2_missing_values.csv", index=False)
    res["table3"].to_csv(T / "table3_categorical_mode_entropy.csv", index=False)
    res["top_freq"].to_csv(T / "step3_top_category_frequencies.csv", index=False)
    alloc.to_csv(T / "step5_class_allocation.csv")
    res["table4"].to_csv(T / "table4_class_distribution.csv", index=False)
    num = res["num_full"].merge(res["num_sub"], on="Feature", suffixes=(" (Full)", " (Sub)"))
    num.to_csv(T / "tables5-7_numerical_full_vs_sub.csv", index=False)
    res["corr_full"].to_csv(T / "fig4_correlation_full.csv")
    res["corr_sub"].to_csv(T / "fig4_correlation_sub.csv")

    # ---------------- figures ---------------- #
    F = config.FIGURES_DIR
    plots.fig2_class_distribution(full, sub, F / "fig2_class_distribution.png")
    plots.fig3_boxplots(full, sub, F / "fig3_boxplots_log.png")
    plots.fig4_correlations(res["corr_full"], res["corr_sub"], F / "fig4_correlation_matrices.png")
    print("[plots] figures written")

    # ---------------- compare with paper ---------------- #
    checks = compare.run_all_checks(res)
    checks.to_csv(T / "paper_vs_reproduced_all_checks.csv", index=False)
    n_ok, n = int(checks["Match"].sum()), len(checks)
    mism = checks[~checks["Match"]]

    by_section = checks.groupby("Section", sort=False)["Match"].agg(["sum", "count"]).reset_index()
    by_section.columns = ["Section", "Matched", "Checked"]

    report = [
        "# Reproduction report - Martinez-Fuentes et al. (2026), IJIS 25:62",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} in {time.time() - t0:.0f}s from "
        f"`{csv.relative_to(config.PROJECT_ROOT).as_posix()}` (SHA-1 `{config.UQ_CSV_SHA1}`).",
        "",
        f"**{n_ok} / {n} reported values reproduced** (equal after rounding to the paper's precision).",
        "",
        "## Summary by section", "", md_table(by_section), "",
        "## Downsampled subset vs. the authors' published CSV (UBU, doi:10.71486/wyx0-x933)", "",
        "```json", json.dumps(ref_check, default=str, indent=2), "```", "",
        "## Values that differ from the paper", "",
        md_table(mism) if len(mism) else "None.", "",
        "## Dataset overview (Step 1)", "", "```json",
        json.dumps(res["overview"], default=str, indent=2), "```", "",
        "## Additional observation (not reported in the paper)", "",
        f"Flows using the unspecified IPv4 address 0.0.0.0: "
        f"{eda.unspecified_ip_counts(full)}. They are not counted as zero values, "
        "which follows the paper's definition.", "",
        "## Table 2 (reproduced)", "", md_table(res["table2"]), "",
        "## Table 3 (reproduced)", "", md_table(res["table3"]), "",
        "## Table 4 (reproduced)", "", md_table(res["table4"]), "",
        "## Tables 5-7 (reproduced; Full)", "", md_table(res["num_full"]), "",
        "## Tables 5-7 (reproduced; Downsampled)", "", md_table(res["num_sub"]), "",
        "## Fig. 4 correlations (Full)", "", md_table(res["corr_full"].round(2).reset_index()), "",
        "## Fig. 4 correlations (Downsampled)", "", md_table(res["corr_sub"].round(2).reset_index()), "",
    ]
    (config.RESULTS_DIR / "reproduction_report.md").write_text("\n".join(report), encoding="utf-8")

    print(f"\n=== {n_ok}/{n} paper values reproduced ===")
    if len(mism):
        print(mism.to_string(index=False))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
