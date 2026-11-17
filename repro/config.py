"""Central configuration: paths, dataset sources, feature groups and constants.

Every other module imports from here so that a single edit changes the whole
pipeline (e.g. a different target size or seed for a sensitivity study).
"""
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTRACT_DIR = RAW_DIR / "extracted"
REFERENCE_DIR = DATA_DIR / "reference_downsampled_ubu"
PROCESSED_DIR = DATA_DIR / "processed"

RESULTS_DIR = PROJECT_ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"

RAW_ZIP = RAW_DIR / "NF-ToN-IoT.zip"
REFERENCE_CSV = REFERENCE_DIR / "Martinez-Downsampled_NF-ToN-IoT_V1_Dataset_2026.csv"
REPRODUCED_CSV = PROCESSED_DIR / "Downsampled_NF-ToN-IoT_V1_reproduced.csv"

# --------------------------------------------------------------------------- #
# Official sources
# --------------------------------------------------------------------------- #
# NF-ToN-IoT (NetFlow V1) on the University of Queensland Research Data Manager.
# Linked from https://staff.itee.uq.edu.au/marius/NIDS_datasets/
UQ_DATASET_UUID = "2ad93cd0-ef9c-11ed-827d-e762de186848"
UQ_DOWNLOAD_API = f"https://api.rdm.uq.edu.au/datasets/{UQ_DATASET_UUID}/download"
# SHA-1 published in the BagIt manifest shipped inside the official zip.
UQ_CSV_SHA1 = "ee8ee11c7e08bee0fb3d8d196d5c5fd2520a44d2"

# Downsampled NF-ToN-IoT V1 published by the paper's authors (Univ. of Burgos),
# DOI https://doi.org/10.71486/wyx0-x933 -> https://riubu.ubu.es/handle/10259/10953
UBU_REFERENCE_URL = (
    "https://riubu.ubu.es/bitstream/handle/10259/10953/"
    "Martinez-Downsampled_NF-ToN-IoT_V1_Dataset_2026.csv?sequence=4&isAllowed=y"
)

# --------------------------------------------------------------------------- #
# Dataset schema
# --------------------------------------------------------------------------- #
LABEL_COL = "Label"      # binary: 0 = Benign, 1 = Attack
ATTACK_COL = "Attack"    # multiclass: Benign + 9 attack types
TARGETS = [LABEL_COL, ATTACK_COL]

# Feature typing follows the paper's functional-role criterion (Sec. 3.1.1),
# not the dtype pandas infers.
CATEGORICAL_FEATURES = {
    # feature: (functional role, TCP/IP layer)
    "IPV4_SRC_ADDR": ("Identifier", "Internet"),
    "IPV4_DST_ADDR": ("Identifier", "Internet"),
    "PROTOCOL": ("Predefined category", "Internet"),
    "L4_SRC_PORT": ("Identifier", "Transport"),
    "L4_DST_PORT": ("Identifier", "Transport"),
    "TCP_FLAGS": ("Predefined category", "Transport"),
    "L7_PROTO": ("Predefined category", "Application"),
}
NUMERICAL_FEATURES = [
    "IN_BYTES",
    "OUT_BYTES",
    "IN_PKTS",
    "OUT_PKTS",
    "FLOW_DURATION_MILLISECONDS",
]

# Row order used by the paper's Table 2.
TABLE2_ORDER = [
    "IPV4_SRC_ADDR", "IPV4_DST_ADDR", "L4_SRC_PORT", "L4_DST_PORT",
    "PROTOCOL", "L7_PROTO", "IN_BYTES", "OUT_BYTES", "IN_PKTS",
    "OUT_PKTS", "TCP_FLAGS", "FLOW_DURATION_MILLISECONDS",
]

# Placeholder tokens treated as "missing" in Step 2.
MISSING_PLACEHOLDERS = ["", "-"]

# --------------------------------------------------------------------------- #
# Step 5 - proportional stratified random downsampling
# --------------------------------------------------------------------------- #
TARGET_SIZE = 50_000
RANDOM_STATE = 42
# Class percentages are rounded to this many decimals before allocation.
# The paper does not state it, but it is the only convention among those we
# tested that gives the published per-class counts and the 49,997 total (see README).
PERCENT_DECIMALS = 4
# Order in which the per-class subsets are concatenated. It does not affect any
# statistic. This is the block order observed in the authors' published CSV,
# so that our output can be compared to it row by row.
CONCAT_ORDER = ["Benign", "backdoor", "dos", "ddos", "injection",
                "mitm", "password", "ransomware", "scanning", "xss"]


def ensure_dirs() -> None:
    for d in (RAW_DIR, REFERENCE_DIR, PROCESSED_DIR, TABLES_DIR, FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)
