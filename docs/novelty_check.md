# Task 2 – Novelty check (literature search, 2026-11-17)

Purpose: before claiming anything as new, record what earlier work has already found about the problems that Task 2 studies.

Each entry says what was **read**, not inferred. "Not stated" means the source does not say it.

---

## 1. Closest prior work

### 1.1 Raskovalov, Gabdullin, Dolmatov (2022)
*Investigation and rectification of NIDS datasets and standardized feature set derivation for network attack detection with graph neural networks.* arXiv:2212.13994 (v2, 29 Dec 2022). No venue stated. Read: full HTML text (v2).

- They inspect several ToN-IoT versions: full ToN-IoT, its train-test subset, NF-ToN-IoT and NF-ToN-IoT-v2.
- On our main issue they write one sentence: *"in NF-ToN-IoT a number of flows are duplicated and labeled as corresponding to different attacks."*
- **Not stated:**
  - how many flows are affected;
  - which class pairs are involved;
  - how the copies are distributed across labels (multiplicity);
  - any accuracy ceiling;
  - the effect on evaluation.
- Other findings, without counts:
  - flows to external IPs are labelled as attacks;
  - normal router/DNS traffic (192.168.1.1) is labelled as attacks.
- They build a filtered version, ToN-IoT-R, from the *full* ToN-IoT. It is available on request.

**Consequence for us:** the existence of conflicting duplicates in NF-ToN-IoT was *noticed* in 2022, so we must cite this paper. Our contribution is the first **measurement and analysis** of the problem:

- 287,559 multi-label records;
- equal multiplicity in 100% of them;
- the class-pair structure;
- a 72.82% accuracy ceiling;
- label-tolerant evaluation;
- the effect on evaluation protocols and on downsampling.

### 1.2 AlMahadin (2026)
*Configuration fingerprints and redundant flows: an evaluation-integrity audit of the ToN-IoT intrusion detection benchmark.* SSRN preprint (posted Sept 2026, not accessible to us). Under review: manuscript INS-D-26-12214. Software and result tables: Zenodo doi:10.5281/zenodo.23924443 (v2, 3 Nov 2026, CC-BY-4.0 / MIT). Read: the README, configuration and result tables of the Zenodo package. Its code was not run or reused.

- **Dataset audited:** the *original* ToN-IoT release (`Processed_Network_dataset`, 22,339,021 flows, 39 features), plus ToN-IoT Windows 7 and 10, NSL-KDD, CIC-IDS2017, UNSW-NB15 and BoT-IoT. **It does not audit NF-ToN-IoT V1.**
- **Findings:**
  - 65.7% exact duplicate rows in the original ToN-IoT network release; ransomware has a replication factor of 226.1.
  - Identifier columns add +2.87 accuracy points: Random Forest goes from 0.9694 to 0.9981 accuracy and from 0.9027 to 0.9746 macro-F1.
  - Random split vs deduplicate-then-stratify comparison. The author notes that the model ranking is **not stable between protocols**. He retracted an earlier estimate of the duplicate-overlap effect, because deduplication also changes the test set's class composition.
  - Windows subsets: machine-configuration counters predict the attack label.
- **Ambiguous vectors** (identical feature vector, more than one label) in the original ToN-IoT network release: **33,605** (`revision_1/results/T2_duplication_audit.csv`).
- **Not covered:**
  - NF-ToN-IoT V1;
  - equal-multiplicity replication across classes;
  - accuracy ceilings;
  - label-tolerant evaluation;
  - downsampled subsets or subset fidelity;
  - the Martinez-Fuentes et al. framework or subset.

**Consequence for us:**

- Duplicate auditing, identifier leakage and deduplicated split protocols on **ToN-IoT are already published**. For these, our NF-ToN-IoT results are *confirmatory* and must be framed that way, with citations.
- His original release has 33,605 ambiguous vectors; NF-ToN-IoT V1 has 287,559 multi-label 12-feature vectors. This suggests the cross-class replication may have been **introduced by the NetFlow conversion and labelling** step. That is a new hypothesis to test.

### 1.3 D'hooge, Verkerken, Volckaert, Wauters, De Turck (2022)
*Establishing the contaminating effect of metadata feature inclusion in machine-learned network intrusion detection models.* DIMVA 2022, LNCS 13358. Read: abstract and repository/publisher excerpts.

- The destination port alone separates ten intrusion detection datasets with 70–100% accuracy on class-balanced test sets. They recommend dropping metadata features (IPs, ports, timestamps, flow IDs).

**Consequence:** the identifier-shortcut idea is **known**. Our E2 result (L4_DST_PORT alone gives 0.986 binary F1 on NF-ToN-IoT V1) confirms it on a dataset they did not test; it is not a new concept.

### 1.4 Flood, Engelen, Aspinall, Desmet (2024)
*Bad Design Smells in Benchmark NIDS Datasets.* IEEE EuroS&P 2024, pp. 658–675. Read: abstract and summaries.

- A manual analysis of seven highly cited NIDS datasets identifies six "data design smells", including near-duplicate flows, label leakage through features and unclear ground truth.

**Consequence:** general background for dataset-quality problems. We still need to check whether ToN-IoT or NF-ToN-IoT is among their seven datasets before citing them for it.

---

## 2. Downsampling and subset fidelity

- No study found that evaluates the **Downsampled NF-ToN-IoT V1** dataset (Martinez-Fuentes et al., UBU, doi:10.71486/wyx0-x933) or the paper's framework with ML models.
- No intrusion-detection study found that measures whether downsampling preserves **model rankings** (e.g. Kendall's τ between full-data and subset rankings).
- Methodological reference outside security: *Benchmarking on Tasks That Matter: Dataset Selection for Preserving Model Rankings* (arXiv:2606.27997). It compares subset rankings with full-benchmark rankings.

---

## 3. Resulting novelty position

| Our result | Status in the literature | How to present it |
|---|---|---|
| Duplicates (12.2%) in NF-ToN-IoT V1 | Duplicates known for ToN-IoT (AlMahadin 2026) | Confirmatory |
| Identifier shortcut (E2) | Known in general (D'hooge 2022; AlMahadin 2026) | Confirmatory, on a new dataset |
| Random vs controlled split (E3) | Done on the original ToN-IoT (AlMahadin 2026) | Extension: we explain *why* the random split penalises memorising models on replicated labels |
| 287,559 multi-label records, 100% equal multiplicity, class-pair structure, 72.82% ceiling | Only noticed in one sentence (Raskovalov 2022) | **New: first measurement and analysis** |
| Label-tolerant accuracy (≈99% for strong models) | Not found | **New** |
| Model-level fidelity of downsampled subsets (E4) | Not found for NIDS | **New** |
| Internal vs external validity of the published subset (E5) | Not found | **New** |
| Improved, fidelity-validated preprocessing framework and subset | Not found | **New: main contribution of Task 2** |

## Sources
- Raskovalov et al. 2022: https://arxiv.org/abs/2212.13994
- AlMahadin 2026, software and result tables: https://zenodo.org/records/23924443 (v1: https://zenodo.org/records/22157652)
- D'hooge et al. 2022: https://dblp.org/rec/conf/dimva/DhoogeVVWT22.html
- Flood et al. 2024: https://ieeexplore.ieee.org/document/10629000 and https://detlearsom.github.io/pubs/BadSmells-EuroSP24-finaldraft.pdf
- Dataset selection for preserving model rankings: https://arxiv.org/pdf/2606.27997
- Martinez-Fuentes et al. 2026: https://link.springer.com/article/10.1007/s10207-026-01235-z; dataset: https://riubu.ubu.es/handle/10259/10953

---

## 4. Second, wider search (2026-11-17, after E6/E6b)

New prior work found, and what was read:

### 4.1 Valencia Vélez (2026) — closest competitor
*Auditing the NetFlow versions of IoT and enterprise intrusion detection benchmarks: data quality, shortcuts and cross-dataset evaluation.* Submitted to *Computer Networks*, not yet published. Code: https://github.com/luiggiv2/netflow-benchmark-audit; Zenodo doi:10.5281/zenodo.23291192 (v1.0.0, 11 Oct 2026). Read: the README, the Zenodo record, `T5_findings.csv` and `duplicates_conflicts_report.txt`.

- **Datasets:** NF-ToN-IoT, NF-BoT-IoT and NF-CSE-CIC-IDS2018, **v2 and v3 only**. NF-ToN-IoT V1 is not covered.
- **Findings:**
  - NF-ToN-IoT-v3 has 226,146 vectors with conflicting labels, mostly Benign/attack pairs (Benign/scanning 154,245 vectors).
  - NF-ToN-IoT-v2 has 0 conflicting vectors.
  - Within-file duplication is 35–99%.
  - Grouped splits (no vector in two partitions), single-feature and shallow-tree shortcut probes, and cross-dataset evaluation.
- **Not covered:**
  - V1;
  - cross-*attack* replication with equal multiplicity;
  - classes with no sole-label record;
  - accuracy ceilings;
  - candidate-label scoring;
  - downsampled subsets;
  - model-ranking fidelity;
  - Martinez-Fuentes et al.
- **Consequence:** conflicting labels in NF-ToN-IoT (v3) and grouped/disjoint splits on NF datasets are **already covered**. We must cite this work. Our V1 findings are a different version with a different pattern: attack/attack, not benign/attack.

### 4.2 Sarhan, Layeghy, Moustafa, Portmann (2020) — the dataset paper
*NetFlow Datasets for ML-based NIDS*, arXiv:2011.09144. Read: PDF pp. 8–14.

- Table 11 (p. 13), NF-ToN-IoT multiclass detection rate (DR) with Extra Trees:
  - injection 41.47%;
  - password 27.36%;
  - scanning 31.30%;
  - XSS 24.49%;
  - weighted accuracy 56.34%.
- The authors attribute this to missing payload features: "We suspect that specific features present in the original dataset contain payload information…"
- **Consequence (new angle):** our replication finding gives a different, measured explanation. These classes have no records carrying their label alone, which caps accuracy at 72.82%, and label-tolerant accuracy reaches about 99%. No published work was found that makes this connection.

### 4.3 Xie, Li, Zhang, Sun, Xu (SciSec 2022 / arXiv:2310.10660)
*Analysis and Detection against Network Attacks in the Overlapping Phenomenon of Behavior Attribute.* Read: search summaries of the abstract.

- They argue that one behaviour can belong to several attack types, and relabel UNSW-NB15 as multi-label (1.689 labels per sample on average).
- **Consequence:** "identical behaviour, several attack labels" has already been described for UNSW-NB15, and treated as **multi-label** (all labels true). We must cite this. Our view differs: each record has *one* true label among its candidates (partial-label), and the contribution is the evaluation metrics and their use in fidelity measurement.

### 4.4 Other new items
- **Roy & Minu (arXiv:2609.28725, Sept 2026, under review).** On the CyberFlowIoT-GICAP dataset, a random flow split inflates attack recall by up to 14 points compared with a PCAP-disjoint split. No NF-ToN-IoT, no subsets, no ranking fidelity. *Supports the known idea that random splits inflate scores.*
- **Gusev & Zaytsev (arXiv:2606.27997, KDD 2026).** Choosing a subset of *datasets* that preserves model rankings, measured with Spearman and Kendall's τ, on time-series, recommender and NLP benchmarks. *Closest methodological analogue; a different problem* (dataset selection, not row downsampling; not security).
- **Zitoune (GitHub, 2026, no results yet).** A cross-dataset test on NF-v3 with capped class sampling. No transfer or ranking study.
- **Not found:**
  - any paper that uses or evaluates the Downsampled NF-ToN-IoT V1 dataset (doi:10.71486/wyx0-x933) or the Martinez-Fuentes framework with ML models;
  - any NIDS study that measures whether a downsampled subset preserves internal-vs-external scores or model rankings;
  - any set-membership ("consistent") metric for conflicting-label NIDS records.

### 4.5 Revised novelty position

| Claim | Status after the second search |
|---|---|
| Conflicting labels exist in NF-ToN-IoT | Known: Raskovalov 2022 (one sentence, V1); Valencia Vélez 2026 (v3, counted) |
| V1: 287,559 attack/attack multi-label vectors, equal multiplicity, 4 classes with no sole-label record, 72.82% ceiling | **New for V1** |
| Explains Sarhan et al.'s low NF-ToN-IoT multiclass results (attributed there to missing payload features) | **New** |
| Grouped/disjoint split; identifier shortcut | Known; confirmatory |
| Candidate-label (partial-label) consolidation and consistency metrics for NIDS evaluation | **New as an evaluation method**; related multi-label view in Xie et al. 2022 |
| Model-level fidelity of a downsampled NIDS subset (internal vs unseen gap, Kendall τ, 20 seeds) | **New** (closest analogue is outside security: Gusev & Zaytsev 2026) |
| ML evaluation of the published Martinez-Fuentes subset | **New** |

"New" means "not found in this search". A literature search cannot prove that something has never been done anywhere.
