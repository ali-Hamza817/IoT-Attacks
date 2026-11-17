"""Values reported in Martinez-Fuentes et al. (2026), Int. J. Inf. Secur. 25:62.

Typed in by hand from Tables 2-7, Sec. 3.1.3 and Fig. 4 so the pipeline can
check its output against the paper automatically. Each entry keeps the number
of decimals printed in the paper. A comparison counts as a match when our value,
rounded the same way, is equal to it.
"""
FD = "FLOW_DURATION_MILLISECONDS"

N_RECORDS_FULL = 1_379_274
N_RECORDS_SUB = 49_997

# Table 2 -> feature: (unique values, zero count, zero %)
TABLE2 = {
    "IPV4_SRC_ADDR": (174, 0, 0.00),
    "IPV4_DST_ADDR": (1478, 0, 0.00),
    "L4_SRC_PORT": (38857, 6323, 0.46),
    "L4_DST_PORT": (16071, 6323, 0.46),
    "PROTOCOL": (5, 0, 0.00),
    "L7_PROTO": (97, 14342, 1.04),
    "IN_BYTES": (5049, 0, 0.00),
    "OUT_BYTES": (5140, 147823, 10.72),
    "IN_PKTS": (921, 0, 0.00),
    "OUT_PKTS": (812, 147823, 10.72),
    "TCP_FLAGS": (24, 127790, 9.27),
    FD: (28408, 372255, 26.99),
}

# Table 3 -> feature: (mode, entropy, max entropy)
TABLE3 = {
    "IPV4_SRC_ADDR": ("192.168.1.31", 3.215, 7.443),
    "IPV4_DST_ADDR": ("192.168.1.190", 3.598, 10.529),
    "PROTOCOL": ("6", 0.474, 2.322),
    "L4_SRC_PORT": ("443", 13.095, 15.246),
    "L4_DST_PORT": ("80", 3.681, 13.972),
    "TCP_FLAGS": ("27", 2.568, 4.585),
    "L7_PROTO": ("7.0", 1.825, 6.600),
}

# Sec. 3.1.3 -> feature: [(value, % of flows), ...]
TOP_FREQUENCIES = {
    "IPV4_SRC_ADDR": [("192.168.1.31", 19.57), ("192.168.1.30", 19.50),
                      ("192.168.1.36", 17.72), ("192.168.1.33", 14.19)],
    "IPV4_DST_ADDR": [("192.168.1.190", 20.85), ("192.168.1.184", 17.47),
                      ("192.168.1.195", 13.90), ("192.168.1.152", 13.79)],
    "PROTOCOL": [("6", 90.73), ("17", 8.81)],
    "L4_SRC_PORT": [("443", 8.20), ("80", 2.65), ("8080", 1.22)],
    "L4_DST_PORT": [("80", 58.56), ("443", 16.91), ("53", 6.14)],
    "TCP_FLAGS": [("27", 44.63), ("18", 19.80)],
    "L7_PROTO": [("7.0", 59.31), ("91.0", 25.01)],
}

# Table 4 -> attack: (full count, full %, sub count, sub %)
TABLE4 = {
    "Benign": (270279, 19.595744, 9797, 19.595176),
    "backdoor": (17247, 1.250440, 625, 1.250075),
    "ddos": (326345, 23.660636, 11830, 23.661420),
    "dos": (17717, 1.284516, 642, 1.284077),
    "injection": (468539, 33.969973, 16985, 33.972038),
    "mitm": (1295, 0.093890, 46, 0.092006),
    "password": (156299, 11.331976, 5666, 11.332680),
    "ransomware": (142, 0.010295, 5, 0.010001),
    "scanning": (21467, 1.556399, 778, 1.556093),
    "xss": (99944, 7.246131, 3623, 7.246435),
}
TABLE4_ATTACK_TOTAL = (1108995, 80.404256, 40200, 80.404824)
MAX_ABS_DEVIATION_PP = 0.00207  # Sec. 4

# Tables 5-7 -> feature: {stat: (full, sub)}
NUMERIC = {
    "IN_BYTES": {"Min": (0, 0), "Max": (79415904, 20640060), "Mean": (1466.23, 1262.97),
                 "Q1": (112, 112), "Q2": (458, 458), "Q3": (554, 555),
                 "Std": (177963.17, 97316.39), "Skewness": (315.76, 196.76),
                 "Kurtosis": (110425.10, 40853.35), "Outlier Ratio": (0.034103, 0.033022)},
    "OUT_BYTES": {"Min": (0, 0), "Max": (70165175, 10796832), "Mean": (2745.43, 2691.21),
                  "Q1": (60, 60), "Q2": (696, 696), "Q3": (2239, 2239),
                  "Std": (110558.95, 54035.36), "Skewness": (431.08, 169.77),
                  "Kurtosis": (227684.79, 32492.39), "Outlier Ratio": (0.087107, 0.088165)},
    "IN_PKTS": {"Min": (1, 1), "Max": (1221043, 737145), "Mean": (18.01, 22.41),
                "Q1": (2, 2), "Q2": (4, 4), "Q3": (5, 5),
                "Std": (2885.74, 3323.75), "Skewness": (293.60, 218.59),
                "Kurtosis": (94452.87, 48393.98), "Outlier Ratio": (0.037913, 0.037282)},
    "OUT_PKTS": {"Min": (1, 1), "Max": (1349068, 99744), "Mean": (10.71, 9.77),
                 "Q1": (1, 1), "Q2": (4, 4), "Q3": (6, 6),
                 "Std": (1454.47, 584.29), "Skewness": (647.20, 149.44),
                 "Kurtosis": (551856.99, 23482.00), "Outlier Ratio": (0.018641, 0.018861)},
    FD: {"Min": (0, 0), "Max": (4294849, 4294849), "Mean": (6633.70, 7555.84),
         "Q1": (0, 0), "Q2": (94, 92), "Q3": (382, 383),
         "Std": (119731.99, 132476.33), "Skewness": (26.22, 24.43),
         "Kurtosis": (738.46, 635.56), "Outlier Ratio": (0.165941, 0.165850)},
}
NUMERIC_DECIMALS = {"Min": 0, "Max": 0, "Mean": 2, "Q1": 0, "Q2": 0, "Q3": 0,
                    "Std": 2, "Skewness": 2, "Kurtosis": 2, "Outlier Ratio": 6}

# Differences we investigated and can explain. They are listed next to the
# check in the report. The check itself stays marked as a mismatch.
KNOWN_DISCREPANCIES = {
    "L7_PROTO rank 1 %": "Exact value is 59.3151%: the paper truncates (59.31) "
                         "where standard rounding gives 59.32.",
    "IN_BYTES Min (full)": "Paper's Table 5 contradicts its own Table 2: IN_BYTES has "
                           "0 zero-valued cells, so its minimum cannot be 0. Observed min = 28.",
    "IN_BYTES Min (sub)": "Same inconsistency as the full dataset (sub-sample min = 28).",
    "OUT_PKTS Min (full)": "Paper's Table 5 contradicts its own Table 2: OUT_PKTS has "
                           "147,823 zeros, so its minimum cannot be 1. Observed min = 0.",
    "OUT_PKTS Min (sub)": "Same inconsistency as the full dataset (sub-sample min = 0).",
}

# Fig. 4 -> upper triangle of the Pearson matrices, 2 decimals: (full, sub)
CORRELATIONS = {
    ("IN_BYTES", "OUT_BYTES"): (0.50, 0.01),
    ("IN_BYTES", "IN_PKTS"): (0.86, 0.98),
    ("IN_BYTES", "OUT_PKTS"): (0.32, 0.02),
    ("IN_BYTES", FD): (0.00, 0.01),
    ("OUT_BYTES", "IN_PKTS"): (0.40, 0.01),
    ("OUT_BYTES", "OUT_PKTS"): (0.73, 0.75),
    ("OUT_BYTES", FD): (0.00, 0.00),
    ("IN_PKTS", "OUT_PKTS"): (0.10, 0.01),
    ("IN_PKTS", FD): (0.00, 0.00),
    ("OUT_PKTS", FD): (0.00, 0.00),
}
