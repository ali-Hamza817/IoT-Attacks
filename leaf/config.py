"""LEAF - Leakage-aware Evaluation And Fidelity framework: configuration."""
from pathlib import Path

from repro import config as base

PROJECT_ROOT = base.PROJECT_ROOT
OUT_DIR = PROJECT_ROOT / "results" / "leaf"
RAW_DIR = OUT_DIR / "raw"          # one CSV per experiment, appended row by row
TABLE_DIR = OUT_DIR / "tables"
FIG_DIR = OUT_DIR / "figures"

ORIGINAL_CSV_GLOB = "*/data/NF-ToN-IoT.csv"
REFERENCE_CSV = base.REFERENCE_CSV   # authors' published 49,997-row subset

LABEL, ATTACK = base.LABEL_COL, base.ATTACK_COL

# Feature sets. "Identifier" is the functional role the original paper itself
# assigns (Table 2) to IP addresses and port numbers.
IDENTIFIERS = ["IPV4_SRC_ADDR", "L4_SRC_PORT", "IPV4_DST_ADDR", "L4_DST_PORT"]
FLOW_FEATURES = ["PROTOCOL", "L7_PROTO", "IN_BYTES", "OUT_BYTES", "IN_PKTS",
                 "OUT_PKTS", "TCP_FLAGS", "FLOW_DURATION_MILLISECONDS"]
FEATURE_SETS = {
    "ALL": IDENTIFIERS + FLOW_FEATURES,   # 12 features, as distributed
    "NOID": FLOW_FEATURES,                # identifiers removed (8 features)
}

TEST_FRACTION = 0.2          # 1 of 5 StratifiedGroupKFold folds
SPLIT_SEED = 2026

# Subset-fidelity experiment (E4)
BUDGETS = [10_000, 50_000, 100_000]
SUBSET_SEEDS = [0, 1, 2, 3, 4]
CLASS_FLOOR = 200            # minimum rows per class for the "floor" strategy


def ensure_dirs() -> None:
    for d in (RAW_DIR, TABLE_DIR, FIG_DIR):
        d.mkdir(parents=True, exist_ok=True)
