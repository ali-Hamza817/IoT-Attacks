# Reproduction report - Martinez-Fuentes et al. (2026), IJIS 25:62

Generated 2026-11-17 14:15 in 11s from `data/raw/extracted/7ca78ae35fa4961a_MOHANAD_A4706/data/NF-ToN-IoT.csv` (SHA-1 `ee8ee11c7e08bee0fb3d8d196d5c5fd2520a44d2`).

**261 / 266 reported values reproduced** (equal after rounding to the paper's precision).

## Summary by section

| Section | Matched | Checked |
|---|---|---|
| Step 1 | 2 | 2 |
| Step 2 | 1 | 1 |
| Table 2 | 36 | 36 |
| Table 3 | 21 | 21 |
| Sec 3.1.3 | 39 | 40 |
| Table 4 | 45 | 45 |
| Sec 4 | 1 | 1 |
| Table 5 | 26 | 30 |
| Table 6 | 40 | 40 |
| Table 7 | 30 | 30 |
| Fig 4 | 20 | 20 |

## Downsampled subset vs. the authors' published CSV (UBU, doi:10.71486/wyx0-x933)

```json
{
  "our_shape": [
    49997,
    14
  ],
  "reference_shape": [
    49997,
    14
  ],
  "same_columns": true,
  "identical_rows_and_order": true
}
```

## Values that differ from the paper

| Section | Item | Paper | Reproduced | Abs diff | Match | Explanation |
|---|---|---|---|---|---|---|
| Sec 3.1.3 | L7_PROTO rank 1 % | 59.31 | 59.32 | 0.01 | ❌ | Exact value is 59.3151%: the paper truncates (59.31) where standard rounding gives 59.32. |
| Table 5 | IN_BYTES Min (full) | 0 | 28 | 28 | ❌ | Paper's Table 5 contradicts its own Table 2: IN_BYTES has 0 zero-valued cells, so its minimum cannot be 0. Observed min = 28. |
| Table 5 | IN_BYTES Min (sub) | 0 | 28 | 28 | ❌ | Same inconsistency as the full dataset (sub-sample min = 28). |
| Table 5 | OUT_PKTS Min (full) | 1 | 0 | 1 | ❌ | Paper's Table 5 contradicts its own Table 2: OUT_PKTS has 147,823 zeros, so its minimum cannot be 1. Observed min = 0. |
| Table 5 | OUT_PKTS Min (sub) | 1 | 0 | 1 | ❌ | Same inconsistency as the full dataset (sub-sample min = 0). |

## Dataset overview (Step 1)

```json
{
  "n_records": 1379274,
  "n_attributes": 14,
  "n_features": 12,
  "n_targets": 2,
  "label_values": [
    0,
    1
  ],
  "attack_values": [
    "backdoor",
    "Benign",
    "ddos",
    "dos",
    "injection",
    "mitm",
    "password",
    "ransomware",
    "scanning",
    "xss"
  ],
  "n_attack_types": 9
}
```

## Additional observation (not reported in the paper)

Flows using the unspecified IPv4 address 0.0.0.0: {'IPV4_SRC_ADDR': 309, 'IPV4_DST_ADDR': 309}. They are not counted as zero values, which follows the paper's definition.

## Table 2 (reproduced)

| Feature | Unique Values | Functional Role | Classification | Zero Count | Zero % |
|---|---|---|---|---|---|
| IPV4_SRC_ADDR | 174 | Identifier | Categorical | 0 | 0 |
| IPV4_DST_ADDR | 1478 | Identifier | Categorical | 0 | 0 |
| L4_SRC_PORT | 38857 | Identifier | Categorical | 6323 | 0.46 |
| L4_DST_PORT | 16071 | Identifier | Categorical | 6323 | 0.46 |
| PROTOCOL | 5 | Predefined category | Categorical | 0 | 0 |
| L7_PROTO | 97 | Predefined category | Categorical | 14342 | 1.04 |
| IN_BYTES | 5049 | Quantitative data | Numerical | 0 | 0 |
| OUT_BYTES | 5140 | Quantitative data | Numerical | 147823 | 10.72 |
| IN_PKTS | 921 | Quantitative data | Numerical | 0 | 0 |
| OUT_PKTS | 812 | Quantitative data | Numerical | 147823 | 10.72 |
| TCP_FLAGS | 24 | Predefined category | Categorical | 127790 | 9.27 |
| FLOW_DURATION_MILLISECONDS | 28408 | Quantitative data | Numerical | 372255 | 26.99 |

## Table 3 (reproduced)

| Feature | TCP/IP Layer | Mode | Entropy | Max Entropy |
|---|---|---|---|---|
| IPV4_SRC_ADDR | Internet | 192.168.1.31 | 3.215 | 7.443 |
| IPV4_DST_ADDR | Internet | 192.168.1.190 | 3.598 | 10.529 |
| PROTOCOL | Internet | 6 | 0.474 | 2.322 |
| L4_SRC_PORT | Transport | 443 | 13.095 | 15.246 |
| L4_DST_PORT | Transport | 80 | 3.681 | 13.972 |
| TCP_FLAGS | Transport | 27 | 2.568 | 4.585 |
| L7_PROTO | Application | 7 | 1.825 | 6.6 |

## Table 4 (reproduced)

| Label | Attack | Full Count | Sub Count | Full % | Sub % | Abs Dev (pp) |
|---|---|---|---|---|---|---|
| 0 | Benign | 270279 | 9797 | 19.5957 | 19.5952 | 0.000568137 |
| 1 | backdoor | 17247 | 625 | 1.25044 | 1.25008 | 0.000365445 |
| 1 | ddos | 326345 | 11830 | 23.6606 | 23.6614 | 0.000783727 |
| 1 | dos | 17717 | 642 | 1.28452 | 1.28408 | 0.000439302 |
| 1 | injection | 468539 | 16985 | 33.97 | 33.972 | 0.00206571 |
| 1 | mitm | 1295 | 46 | 0.09389 | 0.0920055 | 0.00188445 |
| 1 | password | 156299 | 5666 | 11.332 | 11.3327 | 0.000703863 |
| 1 | ransomware | 142 | 5 | 0.0102953 | 0.0100006 | 0.000294671 |
| 1 | scanning | 21467 | 778 | 1.5564 | 1.55609 | 0.000305145 |
| 1 | xss | 99944 | 3623 | 7.24613 | 7.24643 | 0.000303851 |
|  | Total (Label=1) | 1108995 | 40200 | 80.4043 | 80.4048 | None |
|  | Total dataset records (flows) | 1379274 | 49997 | 100 | 100 | None |

## Tables 5-7 (reproduced; Full)

| Feature | Min | Max | Mean | Median | Mode | Std | Variance | Q1 | Q2 | Q3 | Skewness | Kurtosis | Outlier Ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IN_BYTES | 28 | 7.94159e+07 | 1,466.23 | 458 | 112 | 177,963 | 3.16709e+10 | 112 | 458 | 554 | 315.755 | 110,425 | 0.0341027 |
| OUT_BYTES | 0 | 7.01652e+07 | 2,745.43 | 696 | 60 | 110,559 | 1.22233e+10 | 60 | 696 | 2,239 | 431.076 | 227,685 | 0.0871074 |
| IN_PKTS | 1 | 1.22104e+06 | 18.0083 | 4 | 5 | 2,885.74 | 8.3275e+06 | 2 | 4 | 5 | 293.597 | 94,452.9 | 0.0379127 |
| OUT_PKTS | 0 | 1.34907e+06 | 10.7116 | 4 | 1 | 1,454.47 | 2.11547e+06 | 1 | 4 | 6 | 647.198 | 551,857 | 0.018641 |
| FLOW_DURATION_MILLISECONDS | 0 | 4.29485e+06 | 6,633.7 | 94 | 0 | 119,732 | 1.43357e+10 | 0 | 94 | 382 | 26.2238 | 738.463 | 0.165941 |

## Tables 5-7 (reproduced; Downsampled)

| Feature | Min | Max | Mean | Median | Mode | Std | Variance | Q1 | Q2 | Q3 | Skewness | Kurtosis | Outlier Ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IN_BYTES | 28 | 2.06401e+07 | 1,262.97 | 458 | 112 | 97,316.4 | 9.47048e+09 | 112 | 458 | 555 | 196.763 | 40,853.4 | 0.033022 |
| OUT_BYTES | 0 | 1.07968e+07 | 2,691.21 | 696 | 60 | 54,035.4 | 2.91982e+09 | 60 | 696 | 2,239 | 169.774 | 32,492.4 | 0.0881653 |
| IN_PKTS | 1 | 737,145 | 22.415 | 4 | 5 | 3,323.75 | 1.10473e+07 | 2 | 4 | 5 | 218.59 | 48,394 | 0.0372822 |
| OUT_PKTS | 0 | 99,744 | 9.76913 | 4 | 1 | 584.287 | 341,392 | 1 | 4 | 6 | 149.437 | 23,482 | 0.0188611 |
| FLOW_DURATION_MILLISECONDS | 0 | 4.29485e+06 | 7,555.84 | 92 | 0 | 132,476 | 1.755e+10 | 0 | 92 | 383 | 24.4334 | 635.556 | 0.16585 |

## Fig. 4 correlations (Full)

| index | IN_BYTES | OUT_BYTES | IN_PKTS | OUT_PKTS | FLOW_DURATION_MILLISECONDS |
|---|---|---|---|---|---|
| IN_BYTES | 1 | 0.5 | 0.86 | 0.32 | 0 |
| OUT_BYTES | 0.5 | 1 | 0.4 | 0.73 | 0 |
| IN_PKTS | 0.86 | 0.4 | 1 | 0.1 | 0 |
| OUT_PKTS | 0.32 | 0.73 | 0.1 | 1 | 0 |
| FLOW_DURATION_MILLISECONDS | 0 | 0 | 0 | 0 | 1 |

## Fig. 4 correlations (Downsampled)

| index | IN_BYTES | OUT_BYTES | IN_PKTS | OUT_PKTS | FLOW_DURATION_MILLISECONDS |
|---|---|---|---|---|---|
| IN_BYTES | 1 | 0.01 | 0.98 | 0.02 | 0.01 |
| OUT_BYTES | 0.01 | 1 | 0.01 | 0.75 | 0 |
| IN_PKTS | 0.98 | 0.01 | 1 | 0.01 | 0 |
| OUT_PKTS | 0.02 | 0.75 | 0.01 | 1 | 0 |
| FLOW_DURATION_MILLISECONDS | 0.01 | 0 | 0 | 0 | 1 |
