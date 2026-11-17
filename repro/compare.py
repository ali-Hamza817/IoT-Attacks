"""Check every reproduced number against the value printed in the paper."""
from __future__ import annotations

import math

import pandas as pd

from . import paper_values as P


def _decimals(x) -> int:
    s = repr(float(x)) if not isinstance(x, int) else str(x)
    return len(s.split(".")[1]) if "." in s and not s.endswith(".0") else 0


def _match(ours: float, paper: float, decimals: int) -> bool:
    # Equal after rounding to the paper's precision (half-ulp tolerance for
    # floating-point rounding at the boundary).
    return math.isclose(round(float(ours), decimals), float(paper), abs_tol=10 ** (-decimals) / 2 + 1e-12)


class Checker:
    def __init__(self):
        self.rows: list[dict] = []

    def num(self, section, item, ours, paper, decimals=None):
        d = _decimals(paper) if decimals is None else decimals
        ok = _match(ours, paper, d)
        self.rows.append({"Section": section, "Item": item, "Paper": paper,
                          "Reproduced": round(float(ours), max(d, 0)) if d else int(round(float(ours))),
                          "Abs diff": abs(float(ours) - float(paper)), "Match": ok})

    def text(self, section, item, ours, paper):
        self.rows.append({"Section": section, "Item": item, "Paper": paper,
                          "Reproduced": ours, "Abs diff": None, "Match": str(ours) == str(paper)})

    def frame(self) -> pd.DataFrame:
        df = pd.DataFrame(self.rows)
        df["Explanation"] = [
            "" if ok else P.KNOWN_DISCREPANCIES.get(item, "UNEXPLAINED")
            for item, ok in zip(df["Item"], df["Match"])
        ]
        return df


def run_all_checks(res: dict) -> pd.DataFrame:
    c = Checker()
    c.num("Step 1", "records (full)", res["overview"]["n_records"], P.N_RECORDS_FULL, 0)
    c.num("Step 1", "attributes", res["overview"]["n_attributes"], 14, 0)
    c.num("Step 2", "missing cells (any kind)", res["missing"]["Total missing"].sum(), 0, 0)

    t2 = res["table2"].set_index("Feature")
    for f, (u, z, zp) in P.TABLE2.items():
        c.num("Table 2", f"{f} unique", t2.at[f, "Unique Values"], u, 0)
        c.num("Table 2", f"{f} zero count", t2.at[f, "Zero Count"], z, 0)
        c.num("Table 2", f"{f} zero %", t2.at[f, "Zero %"], zp, 2)

    t3 = res["table3"].set_index("Feature")
    for f, (mode, h, hmax) in P.TABLE3.items():
        c.text("Table 3", f"{f} mode", str(t3.at[f, "Mode"]), mode)
        c.num("Table 3", f"{f} entropy", t3.at[f, "Entropy"], h, 3)
        c.num("Table 3", f"{f} max entropy", t3.at[f, "Max Entropy"], hmax, 3)

    top = res["top_freq"]
    for f, pairs in P.TOP_FREQUENCIES.items():
        sub = top[top["Feature"] == f].reset_index(drop=True)
        for i, (val, pct) in enumerate(pairs):
            c.text("Sec 3.1.3", f"{f} rank {i + 1} value", str(sub.at[i, "Value"]), val)
            c.num("Sec 3.1.3", f"{f} rank {i + 1} %", sub.at[i, "Percent"], pct, 2)

    t4 = res["table4"].set_index("Attack")
    for a, (fc, fp, sc, sp) in P.TABLE4.items():
        c.num("Table 4", f"{a} full count", t4.at[a, "Full Count"], fc, 0)
        c.num("Table 4", f"{a} full %", t4.at[a, "Full %"], fp, 6)
        c.num("Table 4", f"{a} sub count", t4.at[a, "Sub Count"], sc, 0)
        c.num("Table 4", f"{a} sub %", t4.at[a, "Sub %"], sp, 6)
    tot = t4.loc["Total (Label=1)"]
    for name, ours, paper, d in zip(["full count", "full %", "sub count", "sub %"],
                                    [tot["Full Count"], tot["Full %"], tot["Sub Count"], tot["Sub %"]],
                                    P.TABLE4_ATTACK_TOTAL, [0, 6, 0, 6]):
        c.num("Table 4", f"Total (Label=1) {name}", ours, paper, d)
    c.num("Table 4", "Total records (sub)", res["sub_n"], P.N_RECORDS_SUB, 0)
    c.num("Sec 4", "max |class % deviation| (pp)",
          res["table4"]["Abs Dev (pp)"].max(), P.MAX_ABS_DEVIATION_PP, 5)

    nf, ns = res["num_full"].set_index("Feature"), res["num_sub"].set_index("Feature")
    for f, stats in P.NUMERIC.items():
        for stat, (pf, ps) in stats.items():
            d = P.NUMERIC_DECIMALS[stat]
            tbl = "Table 5" if stat in ("Min", "Max", "Mean") else (
                "Table 6" if stat in ("Q1", "Q2", "Q3", "Std") else "Table 7")
            c.num(tbl, f"{f} {stat} (full)", nf.at[f, stat], pf, d)
            c.num(tbl, f"{f} {stat} (sub)", ns.at[f, stat], ps, d)

    for (a, b), (pf, ps) in P.CORRELATIONS.items():
        c.num("Fig 4", f"r({a},{b}) full", res["corr_full"].at[a, b], pf, 2)
        c.num("Fig 4", f"r({a},{b}) sub", res["corr_sub"].at[a, b], ps, 2)

    return c.frame()
