# Task 2 – Design of the improved framework and of experiment E6

Written 2026-11-17, **before** the full E6 run. Only a pipeline smoke test (one seed, DT and LR, four configurations) had been run when this plan was fixed.

## 1. Weaknesses of the original framework (Martinez-Fuentes et al., 2026)

| # | Weakness | Evidence (verified) |
|---|---|---|
| W1 | Representativeness is judged only by statistics, never by models | The paper trains no model; scikit-learn appears only as future work (its Table 1) |
| W2 | No label-consistency check | 287,559 distinct 12-feature records carry 2–5 attack labels. Each label occurs equally often (100%), and rows = labels × copies (100%) (E1b) |
| W3 | Four attack classes are not separable at all | dos, password, scanning and xss have **0** records that carry their label alone: 295,427 rows, 21.4% of the data (E1, checked independently) |
| W4 | Identifiers are kept as features | IPs and ports alone give 0.9998 binary F1 (E2). Known shortcut (D'hooge 2022) |
| W5 | Rare classes almost vanish in the subset | 5 ransomware and 46 mitm rows. The internal test set holds 1 and 9 of them (E5) |
| W6 | No leakage-safe split is provided | A random split of the published subset puts 5.2% of test vectors' exact copies in training (E6 smoke test). *Updated after the run* (`python run_leaf.py leak`, 20 seeds): 4.95% (4.63–5.26%) with all features and 46.8% (45.8–47.4%) without identifiers. The disjoint split gives 0% |
| W7 | Some statistical claims are overstated | Maxima change for 4 of 5 numerical features. The IN_BYTES–OUT_BYTES correlation falls from 0.50 to 0.01; it hangs on 8 extreme flows (README §8) |

## 2. Improved framework (LEAF preprocessing)

| Phase | Step | Change vs. the original paper |
|---|---|---|
| 1. EDA | 1–4 | Unchanged (reproduced exactly in Task 1) |
| 2. Integrity | 5. Duplicate and label-consistency audit | **New.** Exact duplicates, multi-label vectors, per-class sole-label share, Bayes accuracy ceiling (`leaf/audit.py`, `leaf/forensics.py`) |
| | 6. Label consolidation | **New.** One record per distinct feature vector, with its *set of candidate labels*. This removes replicated rows and exact duplicates in one step (`leaf/partial.py`) |
| | 7. Identifier handling | **New.** IPs and ports are removed by default (NOID). Keeping them must be an explicit, reported choice |
| 3. Sampling and validation | 8. Floor-proportional downsampling | Proportional allocation as in the paper, but every stratum keeps min(200, available) records. Strata = candidate sets |
| | 9. Leakage-safe split | **New.** A fixed 80/20 split in which identical vectors never appear on both sides |
| | 10. Model-fidelity validation | **New.** Train models on the subset; compare internal scores and rankings with scores on unseen data outside the subset (E6) |

**Evaluation for candidate-label data** (`leaf/partial.py`). A prediction is *consistent* if it is one of the record's candidate labels.

- Primary metric: **balanced consistency**, the mean over classes of the consistent accuracy on records that have that class as a candidate.
- Secondary metrics: consistent accuracy and resolved macro-F1.
- On single-label data the three metrics equal balanced accuracy, accuracy and macro-F1. This is unit-tested against scikit-learn.

## 3. Experiment E6 – evaluation fidelity of reduced datasets

**Question.** A researcher uses a ~50k subset, splits it 80/20 and reports scores. Do the scores and the model ranking hold on unseen data from the rest of NF-ToN-IoT V1?

**Configurations (16).**

| Labels | Sampling | Protocol | Features |
|---|---|---|---|
| raw | published (authors' exact file), proportional, floor | random, disjoint | ALL, NOID |
| consolidated | proportional, floor | disjoint (equal to random, since all records are distinct) | ALL, NOID |

- The paper's practice is `raw|published|random|ALL`.
- Full LEAF is `consolidated|floor|disjoint|NOID`.

**Per configuration:** 5 seeds (subset draw, split and model seed) × 7 models (LR, DT, RF, ET, XGB, LGBM, MLP). That is 560 fits. Model hyper-parameters are those fixed before E3, with no tuning.

**Scores per fit:**

- *internal*: the subset's own 20% test part;
- *external*: every record of the same pool outside the subset whose feature vector never occurs in the subset's training part.

**Fidelity measures (computed on the primary metric):**

1. **Gap:** mean |internal − external| over fits, and the mean signed gap (internal − external), which measures optimism.
2. **Ranking agreement:** Kendall τ between the 7-model internal ranking and the external ranking, per seed; mean ± sd.
3. **Stability:** the standard deviation of internal scores across the 5 seeds, averaged over models.
4. **Test support:** the smallest internal per-class support, and the number of classes with fewer than 10 internal test records.

**Hypotheses:**

- **H1.** Under the paper's practice (`raw|published|random|ALL`), internal and external results disagree: there is a non-zero gap and τ < 1.
- **H2.** Each LEAF factor (disjoint split, floor sampling, label consolidation, identifier removal) improves at least one fidelity measure *when the others are held fixed*.
- **H3.** Full LEAF (`consolidated|floor|disjoint|NOID`) has better fidelity than the paper's practice on gap, τ and stability.

**Commitment.** All 16 configurations are reported, whatever the outcome. A hypothesis that fails is reported as failed.

**Caveat, decided in advance.** Raw and consolidated configurations do not measure the same task. Raw data is scored against replicated single labels, which caps accuracy at 72.82%. Consolidated data is scored against candidate sets, so the ceiling is 100%. The *levels* of the two are therefore not compared as if they measured the same thing. Only the fidelity measures (gap, τ, stability) are compared across label handling.

## 4. E6 results (added after the run, 2026-11-17)

Run: 560 fits, 4,803 s, no errors, no missing or duplicate (config, seed, model) rows. Tables: `results/leaf/tables/E6_fidelity_summary.csv`, `E6_factor_contrasts.csv`, `E6_per_model.csv`. Figure: `results/leaf/figures/E6_fidelity_overview.png`. Analysis code: `python -m leaf.analyze_e6`.

### 4.1 Pre-registered measures (primary metric, mean over 5 seeds × 7 models)

| Config | Internal | External | Mean \|gap\| | Signed gap | τ mean ± sd | Same winner | Seed sd | Min class support |
|---|---|---|---|---|---|---|---|---|
| **raw\|published\|random\|ALL** (paper) | 0.4776 | 0.4674 | 0.0372 | +0.0102 | 0.676 ± 0.239 | 3/5 | 0.0465 | 1 |
| raw\|published\|disjoint\|ALL | 0.4794 | 0.4691 | 0.0355 | +0.0103 | 0.867 ± 0.197 | 4/5 | 0.0444 | 1 |
| raw\|proportional\|random\|ALL | 0.4659 | 0.4821 | 0.0348 | −0.0162 | 0.790 ± 0.227 | 3/5 | 0.0453 | 1 |
| raw\|proportional\|disjoint\|ALL | 0.4785 | 0.4816 | 0.0373 | −0.0032 | 0.886 ± 0.080 | 5/5 | 0.0462 | 1 |
| raw\|floor\|random\|ALL | 0.5837 | 0.5509 | 0.0328 | +0.0328 | 0.810 ± 0.117 | 5/5 | 0.0155 | 28 |
| raw\|floor\|disjoint\|ALL | 0.5871 | 0.5494 | 0.0377 | +0.0377 | 0.905 ± 0.117 | 5/5 | 0.0137 | 28 |
| consolidated\|proportional\|disjoint\|ALL | 0.8926 | 0.8760 | 0.0228 | +0.0166 | 0.771 ± 0.186 | 4/5 | 0.0259 | 1 |
| consolidated\|floor\|disjoint\|ALL | 0.9542 | 0.9473 | 0.0103 | +0.0069 | 0.771 ± 0.144 | 5/5 | 0.0066 | 29 |
| raw\|published\|random\|NOID | 0.4192 | 0.3725 | 0.0519 | +0.0467 | 0.505 ± 0.206 | 2/5 | 0.0369 | 1 |
| raw\|published\|disjoint\|NOID | 0.3597 | 0.3579 | 0.0175 | +0.0018 | 0.790 ± 0.124 | 4/5 | 0.0309 | 1 |
| raw\|proportional\|random\|NOID | 0.4055 | 0.3747 | 0.0407 | +0.0308 | 0.829 ± 0.080 | 3/5 | 0.0398 | 1 |
| raw\|proportional\|disjoint\|NOID | 0.3747 | 0.3728 | 0.0296 | +0.0019 | 0.714 ± 0.178 | 3/5 | 0.0435 | 1 |
| raw\|floor\|random\|NOID | 0.5329 | 0.4347 | 0.0982 | +0.0982 | 0.581 ± 0.248 | 2/5 | 0.0213 | 28 |
| raw\|floor\|disjoint\|NOID | 0.4867 | 0.4457 | 0.0451 | +0.0410 | 0.676 ± 0.109 | 5/5 | 0.0461 | 10 |
| consolidated\|proportional\|disjoint\|NOID | 0.7111 | 0.7235 | 0.0218 | −0.0124 | 0.829 ± 0.124 | 2/5 | 0.0253 | 1 |
| **consolidated\|floor\|disjoint\|NOID** (LEAF) | 0.8378 | 0.8646 | 0.0415 | −0.0268 | 0.829 ± 0.043 | 3/5 | 0.0187 | 7 |

Reading guide: "Same winner" = seeds in which the best model on the internal test part is also the best model externally. "Seed sd" = standard deviation of a model's internal score over the 5 seeds, averaged over the 7 models. With 7 models, τ moves in steps of 2/21 ≈ 0.095 per seed.

### 4.2 Hypotheses

- **H1 – supported.** Under the paper's practice the internal estimate is off by 0.037 on average (mean \|gap\|; signed +0.010), and the model ranking agrees only partially: τ = 0.676 ± 0.239, with per-seed τ of 0.43, 0.43, 0.90, 0.90 and 0.71. The internal winner is the external winner in 3 of 5 seeds. One ransomware record is in the internal test part, and two classes have fewer than 10 test records.
- **H2 – partly supported.** Counted per matched pair (configs that differ in one factor only):

  | Factor | Pairs improving ≥1 measure | \|gap\| better | τ better | Seed sd better |
  |---|---|---|---|---|
  | random → disjoint split | 6/6 | 4/6 | 5/6 | 3/6 |
  | proportional → floor sampling | 5/6 | 2/6 | 2/6 | 5/6 |
  | raw → consolidated labels | 4/4 | 4/4 | 2/4 | 4/4 |
  | ALL → NOID features | 6/8 | 3/8 | 3/8 | 5/8 |

  The split and the label consolidation pass in every pair. Floor sampling fails in one pair and identifier removal fails in two. The criterion "≥1 of 3 measures improves" is lenient, and several of the deltas are smaller than the seed-to-seed noise. These counts are therefore weak evidence on their own; see the E6b extension.
- **H3 – not supported as pre-registered.** Full LEAF beats the paper's practice on τ (0.829 vs 0.676; per-seed sd 0.043 vs 0.239) and on stability (seed sd 0.0187 vs 0.0465). It is **worse on mean \|gap\| (0.0415 vs 0.0372)**. Its internal estimate is pessimistic (signed gap −0.027).

### 4.3 What explains the H3 gap failure (diagnosed after the run)

Floor sampling keeps min(200, available) records per candidate set. For NOID consolidated data this takes **every** record that carries dos or ransomware into the subset, so the external set holds no record of either class. The table is `external_support` in `E6_fidelity.csv`: dos = 0 and ransomware = 0 externally, while the internal test part has ≥142 dos and ≥7 ransomware records. The pre-registered external balanced consistency therefore averages over 8 classes and the internal one over 10. Per class, internal and external agree closely; mitm is the exception (+0.13). The same happens to ransomware in every floor config. The paper's file keeps only 5 ransomware rows, so its external set still contains 136.

**Post-hoc sensitivity analysis, not pre-registered.** The internal and external scores are averaged over the classes present on **both** sides (`balanced_matched` in the tables). This changes only configs where a class is missing externally (all floor configs):

| | Paper practice | Full LEAF |
|---|---|---|
| Mean \|gap\| | 0.0372 | **0.0185** |
| Signed gap | +0.0102 | +0.0094 |
| τ mean ± sd | 0.676 ± 0.239 | **0.924 ± 0.043** |
| Seed sd | 0.0465 | 0.0187 |

On matched classes, full LEAF is better on all three H3 measures. Because this comparison was chosen after seeing the data, it is reported as a sensitivity analysis and not as a confirmation of H3. The confirmatory evidence is E6b (§5).

The absences were checked in all 5 seeds. Ransomware is absent externally in every floor config. dos is additionally absent in `consolidated|floor|disjoint|NOID`. No proportional or published config loses a class.

**Design lesson (refinement proposed, not yet tested).** A floor that takes *every* record of a rare class leaves nothing to validate that class on. Step 8 should cap the floor at a share of what is available, for example min(200, ⌊0.5 × available⌋), so that each class keeps external records. This changes the method after seeing the results, so it must be evaluated on fresh seeds or a second dataset before any claim is made.

### 4.4 Other observations

- **Identifier removal does not improve within-dataset fidelity** (\|gap\| better in 3/8 pairs, τ in 3/8). Its justification is different: IPs and ports are a shortcut that will not carry over to another network (E2). E6 measures agreement with the rest of the *same* capture, where the same hosts recur, so it cannot show that benefit.
- **A random split is most harmful when identifiers are removed.** About 47% of the random-split test records then have an exact copy in training (`E6_split_leakage.csv`), against about 5% with all features. For NOID data the random split inflates the internal score: signed gap +0.047 (published), +0.031 (proportional) and +0.098 (floor), against +0.002, +0.002 and +0.041 with the disjoint split. Eight flow features produce many more exact duplicates than twelve.
- `consolidated|floor|disjoint|ALL` has the smallest pre-registered gap (0.0103) and the lowest seed sd (0.0066) of all 16 configs. It keeps identifiers, which E2 shows to be a shortcut.
- The best external scores among the full-LEAF models are LGBM 0.947, XGB 0.948 and RF 0.943 (balanced consistency). They are not comparable with raw-label scores (§3 caveat).

## 5. E6b – confirmatory extension with 20 seeds (added 2026-11-17)

**Why.** With 5 seeds and 7 models, τ moves in steps of 0.095, and the matched-class metric (§4.3) was chosen after seeing seeds 0–4. Before any claim, the three key configs were rerun with 15 **fresh** seeds (5–19; 315 fits, 2,791 s, no errors) and written to a separate file (`results/leaf/raw/E6b_more_seeds.csv`). The pre-registered E6 file was not modified.

Tables: `E6b_summary.csv`, `E6b_per_seed.csv`, `E6b_tests.csv`. Figure: `E6b_seed_distributions.png`.

Tests:

- The paper's practice vs `raw|published|disjoint|ALL` uses the same file and the same seed, so the test is paired (Wilcoxon signed-rank).
- The paper's practice vs full LEAF uses independent subset draws (Mann–Whitney U).
- All tests are two-sided. The 95% CIs are percentile bootstrap intervals over seeds.

| 20 seeds | τ mean [95% CI] | Same winner | Mean \|gap\| [95% CI] | Signed gap | Seed sd | Regret* | Top-2 external margin |
|---|---|---|---|---|---|---|---|
| Paper practice `raw\|published\|random\|ALL` | 0.705 [0.614, 0.790] | 14/20 | 0.0392 [0.0362, 0.0423] | +0.006 | 0.0468 | 0.0052 | 0.031 |
| Paper file + disjoint split `raw\|published\|disjoint\|ALL` | 0.810 [0.724, 0.886] | 16/20 | 0.0335 [0.0288, 0.0386] | +0.009 | 0.0425 | 0.0050 | 0.026 |
| Full LEAF, pre-registered metric | 0.800 [0.752, 0.848] | 8/20 | 0.0451 [0.0411, 0.0491] | −0.036 | 0.0217 | 0.0021 | 0.002 |
| Full LEAF, matched classes (post hoc) | 0.881 [0.852, 0.910] | 9/20 | 0.0188 [0.0169, 0.0205] | +0.012 | 0.0156 | 0.0016 | 0.002 |

\*Regret = the external score of the externally best model minus the external score of the model chosen on the internal test part. It is a post-hoc measure, added to interpret the "same winner" column.

**Results, stated plainly:**

1. **Disjoint split on the authors' file.** τ improves 0.705 → 0.810 and the gap shrinks 0.0392 → 0.0335. Neither change is significant (p = 0.114 and 0.105, n = 20). The direction is consistent, but the evidence is not conclusive.
2. **Full LEAF on the pre-registered metric.** The gap is **significantly worse**, 0.0451 vs 0.0392 (p = 0.034). τ is higher but not significantly (0.800 vs 0.705, p = 0.195). **H3 as pre-registered is rejected on the gap measure.** The internal estimate is pessimistic (−0.036) because the external set lacks the dos and ransomware classes (§4.3).
3. **Full LEAF on matched classes, tested only on the 15 fresh seeds.**
   - Gap: 0.0189 vs 0.0399, p = 3.4 × 10⁻⁶.
   - τ: 0.867 vs 0.714, p = 0.022.
   - Over all 20 seeds: gap p = 6.8 × 10⁻⁸ and τ p = 0.0028.

   The metric was defined before seeds 5–19 were run, so this test is a genuine out-of-sample confirmation of the post-hoc metric. It is still not the pre-registered measure.
4. **Stability.** The seed sd of internal scores halves or better: 0.0468 → 0.0217 (pre-registered) and 0.0156 (matched).
5. **Picking the winner.** LEAF's internal winner matches the external winner less often (8/20 vs 14/20). Under LEAF, however, the best three models (LGBM, XGB, RF) are nearly tied externally: the mean margin between the top two is 0.002, against 0.031 for the paper's practice. Choosing on the internal set therefore costs only 0.0021 of external score, against 0.0052 for the paper's practice. That difference is not significant (p = 0.43). So the lower winner agreement reflects near-ties, not worse model selection.

### 5.1 Overall verdict on the hypotheses

| | Verdict |
|---|---|
| H1 | **Supported.** The paper's practice gives τ = 0.705 [0.614, 0.790] and the right winner in only 14 of 20 seeds. |
| H2 | **Partly supported**, on a lenient criterion; see §4.2. Individual effects are mostly not significant with this many seeds. |
| H3 | **Rejected as pre-registered** on the gap measure. It is supported on ranking agreement (in direction only, not significant) and on stability. On matched classes (post hoc, confirmed on fresh seeds) full LEAF is significantly better on gap and τ. |

**What can honestly be claimed.**

- The paper's 49,997-row subset with a random 80/20 split gives a noisy model ranking. Its internal scores carry roughly ±0.04 of error relative to unseen data.
- LEAF's subset gives more stable and more consistently ranked results.
- LEAF's floor step, as specified, removes rare classes from the data left for validation. When that is accounted for, its estimates are about twice as close to unseen-data performance.
- The floor step needs the refinement in §4.3, to be tested before publication.
