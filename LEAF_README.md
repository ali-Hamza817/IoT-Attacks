# LEAF: Leakage-aware Evaluation And Fidelity framework for NF-ToN-IoT

Code for the proposed research direction. It builds on the reproduction of Martinez-Fuentes et al. (2026) in `repro/`.

## Research question

That paper shows that proportional stratified downsampling keeps the *statistical* properties of NF-ToN-IoT V1: class proportions, quantiles, skewness and outlier ratios. Researchers then train and compare ML intrusion detectors on such subsets. LEAF asks whether those conclusions can be trusted:

1. **Data integrity (E1).** How many records are duplicated, and how many share an identical feature vector with a *different* label? What is the highest accuracy or recall any classifier could reach?
2. **Shortcuts (E2).** How much of the detection signal comes from identifier fields (IP addresses, ports) rather than from traffic behaviour?
3. **Protocol inflation (E3).** How much does the usual protocol (random row-level split, all features) inflate reported scores, compared with a leakage-controlled protocol?
4. **Subset fidelity (E4).** Does a model trained on a reduced subset perform, rank and attribute features like one trained on the full data? Which sampling strategy is most faithful at which budget?
5. **Internal vs external validity (E5).** If a researcher splits the *published* 49,997-row subset 80/20, how well does the score transfer to the other 96.4% of NF-ToN-IoT?
6. **Replication forensics (E1b).** Are the multi-label records one flow written out once per attack label?
7. **Evaluation fidelity of reduced datasets (E6, E6b).** For the paper's practice and for the improved pipeline, do a subset's internal scores and model ranking hold on unseen data? The design and hypotheses were fixed before the run: [docs/task2_design.md](docs/task2_design.md).

## Protocols and feature sets

| | Description |
|---|---|
| **Naive split** | Stratified random 80/20 split of the raw rows (common practice). |
| **Controlled split** | (1) Exact duplicate rows removed. (2) Rows grouped by identical feature vector, and each group goes wholly to train or wholly to test, so no test vector is seen in training. (3) Group-level 80/20 split stratified by each group's majority class. |
| **ALL** | All 12 NetFlow features, with IPs encoded as 32-bit integers. |
| **NOID** | The 8 flow features. The four fields the original paper classifies as *Identifier* (Table 2: IPV4_SRC/DST_ADDR, L4_SRC/DST_PORT) are removed. |

## Models

LR, DT, RF, ET, XGBoost, LightGBM and MLP, with hyper-parameters fixed in advance (`leaf/models.py`); none are tuned on test data.
- XGBoost and LightGBM use early stopping on 10% of the *training* data.
- LightGBM's validation log-loss diverged without early stopping at learning rate 0.1, because of the label conflict in this dataset. This is documented in the code.

## Sampling strategies (E4)

| Strategy | Description |
|---|---|
| `uniform` | Simple random sample (non-stratified baseline). |
| `proportional` | Martinez-Fuentes et al. Step 5: `S_c = int(P_c × budget)`. |
| `dedup_proportional` | Exact duplicates removed first, then proportional sampling. |
| `floor` | Proportional, with at least min(200, available) rows per class. |

Budgets are 10k, 50k and 100k rows, with 5 seeds each. All subsets are drawn from the controlled training pool and evaluated on the same full controlled test set.

## Running

```bash
python run_leaf.py all        # E1..E5 (several hours on 8 CPU cores; resumable)
python run_leaf.py e1b e6     # replication forensics; E6 (560 fits, about 80 min)
python run_leaf.py e6b        # E6 extension, 15 more seeds on 3 configs (315 fits, about 47 min)
python analyze_leaf.py        # E1-E5 tables + figures -> results/leaf/
python -m leaf.analyze_e6     # E6/E6b tables + figures
```

- Splits are cached in `results/leaf/raw/splits.npz`, so every experiment uses identical partitions.
- Every run is appended to `results/leaf/raw/*.csv`. Interrupted runs skip finished work when restarted.
- E3 test predictions are kept for bootstrap CIs and significance tests.

## Results (full run, 2026-11-05; total compute 39,100 s on 8 CPU cores)

All numbers below come from `results/leaf/tables/`. Macro-F1 95% CIs use a bootstrap over the E3 test predictions (`E3_protocol_with_ci.csv`).

### F1 - Labels are replicated across attack classes (E1)
- 168,345 rows (12.2%) are exact duplicates.
- 287,559 distinct 12-feature records carry more than one attack label. In **100%** of them, every label occurs with exactly the same multiplicity. This was checked independently with a pandas groupby. It is consistent with records having been copied into several attack captures; that is a hypothesis to confirm with the dataset authors.
- 100% of `xss` records also occur as `injection`, 100% of `dos` as `ddos`, and 92.2% of `password` as `injection`.
- The multiclass **accuracy ceiling** for any classifier is 72.82% (raw data) and 69.94% (deduplicated). The binary ceiling is 100%, because Benign never shares a record with an attack.

### F2 - Identifier shortcut (E2, E3)
- Identifier fields alone reach 0.9998 binary F1; `L4_DST_PORT` alone reaches 0.986.
- In E3 binary detection (controlled split), removing identifiers changes macro-F1 as follows:

| Model | With identifiers | Without | Change |
|---|---|---|---|
| LGBM | 0.9998 | 0.993 | −0.6 pp |
| RF | 0.9998 | 0.983 | −1.7 pp |
| XGB | 0.9998 | 0.982 | −1.7 pp |
| DT | 0.9997 | 0.979 | −2.1 pp |
| MLP | 0.998 | 0.819 | −17.9 pp |
| LR | 0.980 | 0.784 | −19.6 pp |
| ET | 0.9998 | 0.609 | −39.1 pp |

### F3 - Multiclass errors are almost all label ambiguity (E3)
- Every model's strict multiclass accuracy is ≤ 0.723, just under the ceiling.
- Label-tolerant accuracy counts a prediction as correct if the same record carries that label anywhere in the dataset. On that measure RF, XGB and LGBM reach 0.986–0.9996 under every protocol and feature set; LGBM on the controlled split with all features reaches 0.9996.
- So almost every apparent multiclass error comes from ambiguous labels, not from the model.

### F4 - On this dataset the random split does not inflate multiclass scores; it penalises memorising models
- Moving from the random (naive) split to the controlled split changes multiclass macro-F1 by between −5.4 and +1.0 pp (`E3_multiclass_inflation.csv`). It does not inflate it.
- On records with ambiguous labels, the naive split gives DT a strict accuracy of 0.073 and RF 0.147, against about 0.43 for the other models.
- Likely mechanism: in a random split, copies of the same record with different labels land in both train and test. The test copy then tends to carry the label that is under-represented in training, so a model that memorises the training copy is systematically wrong.

### F5 - Subset macro-F1 is not a reliable fidelity signal (E4)
- On the controlled pool, `dedup_proportional` is identical to `proportional`, because the pool contains no duplicates. It is dropped from the analysis.
- Some subsets *exceed* full-data macro-F1, e.g. LGBM 100k proportional: 0.589 vs full-data 0.525, while their accuracy is equal or lower (0.695 vs 0.699).
- The whole gain comes from the replicated classes. For LGBM, dos goes from 0.017 to 0.31, xss from 0.135 to 0.35 and password from 0.027 to 0.20. A full-data model consistently assigns such records the twin label. Random subsets can hold more copies with the minority label, which helps those classes.
- Learnable rare classes behave as expected and lose performance in subsets, e.g. LGBM ransomware 0.825 → 0.716, mitm 0.739 → 0.69.
- Model rankings on subsets agree only moderately with the full-data ranking: Kendall τ = 0.37–0.75. The top model on full data (RF, ALL) was never the top model on any ALL-feature subset. The `floor` strategy gives the highest τ at 10k rows.

### F6 - Internal evaluation of the published 49,997-row subset (E5)
- The 10,000-row internal test set contains 1 ransomware row and 9 mitm rows.
- Internal macro-F1 varies more across seeds than external macro-F1 on unseen vectors. With all features its standard deviation is 1.2–11× the external one, and at least 2.5× for five of the seven models. For tree ensembles it is usually 0.05–0.06 lower. For example, LGBM scores 0.526 ± 0.023 internally and 0.590 ± 0.019 externally on unseen vectors (`E5_internal_vs_external.csv`). *(Corrected 2026-11-17: an earlier version said "4–10×" and mixed two external columns.)*
- Accuracy transfers within 0.5 pp.
- Model order changes between internal and external evaluation: LR beats ET internally (0.428 vs 0.369), but loses externally (0.397 vs 0.431).

### F7 - The multi-label records are replicated flows (E1b)
- 287,559 distinct 12-feature vectors (668,984 rows) carry 2–5 attack labels.
- In 100% of them every label occurs equally often, and rows = labels × copies.
- 100% use an ephemeral source port (≥ 1024; 44.27% ≥ 49152), spread over 21,798 distinct source ports. 87.94% have a non-zero duration and 92.38% carry more than 100 bytes. Two independent flows are very unlikely to coincide on all of these.
- They sit on 43 attacker → victim host pairs; the top 10 pairs carry 73.5% of the rows.
- The largest label combinations are injection+xss (88,403 vectors) and injection+password (76,374).
- dos, password, scanning and xss have **no** record that carries their label alone: 295,427 rows, 21.4% of the data.
- These labels are therefore treated as **candidate sets** (`leaf/partial.py`).

### F8 - Evaluation fidelity of reduced datasets (E6, E6b)
Full results, including the failed hypothesis, are in [docs/task2_design.md](docs/task2_design.md) §4–5. All 16 configurations are in `results/leaf/tables/E6_fidelity_summary.csv`.

| 20 seeds × 7 models | τ internal vs external ranking | Mean \|internal − external\| | Seed sd |
|---|---|---|---|
| Paper practice (published subset, random split, all features) | 0.705 [0.614, 0.790] | 0.0392 | 0.0468 |
| Published subset, disjoint split | 0.810 [0.724, 0.886] | 0.0335 | 0.0425 |
| Full LEAF, pre-registered metric | 0.800 [0.752, 0.848] | **0.0451** (worse, p = 0.034) | 0.0217 |
| Full LEAF, matched classes (post hoc; confirmed on 15 fresh seeds) | 0.881 [0.852, 0.910] | 0.0188 | 0.0156 |

- **H1 supported.** Under the paper's practice the 7-model ranking agrees only partly with unseen data. The internal winner is the external winner in 14 of 20 seeds.
- **H3 rejected as pre-registered.** LEAF's floor step pulls *every* ransomware record (and, without identifiers, every dos record) into the subset, so the unseen data cannot score those classes. The pre-registered gap is worse.
- On matched classes LEAF halves the gap (p = 3.4 × 10⁻⁶ on fresh seeds) and raises τ (p = 0.022). A capped floor is proposed as the fix and is not yet tested.
- Removing identifiers does not improve fidelity *within* NF-ToN-IoT V1. Its value is avoiding the shortcut (F2).
