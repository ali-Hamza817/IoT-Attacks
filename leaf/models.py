"""Model zoo. Hyper-parameters are fixed in advance (no tuning on test data),
which keeps protocols and subsets comparable."""
from __future__ import annotations

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

N_JOBS = 8


def _log_scaler():
    # Features are non-negative counts / codes with extreme right skew
    # (skewness up to ~650, Table 7 of the original paper).
    return [FunctionTransformer(np.log1p), StandardScaler()]


def make(name: str, seed: int, n_classes: int):
    if name == "LR":
        return make_pipeline(*_log_scaler(), LogisticRegression(max_iter=500, random_state=seed))
    if name == "DT":
        return DecisionTreeClassifier(random_state=seed)
    if name == "RF":
        return RandomForestClassifier(n_estimators=100, min_samples_leaf=2, n_jobs=N_JOBS,
                                      random_state=seed)
    if name == "ET":
        return ExtraTreesClassifier(n_estimators=100, min_samples_leaf=2, n_jobs=N_JOBS,
                                    random_state=seed)
    # Boosted models: up to 500 rounds with early stopping (see ``fit``).
    # A learning rate of 0.1 with no early stopping made LightGBM's validation
    # log-loss diverge (0.67 -> 5.7 within 100 rounds). The cause is the heavy
    # label conflict in NF-ToN-IoT. The settings below are stable.
    if name == "XGB":
        return XGBClassifier(n_estimators=500, max_depth=8, learning_rate=0.1, tree_method="hist",
                             early_stopping_rounds=30, n_jobs=N_JOBS, random_state=seed,
                             verbosity=0)
    if name == "LGBM":
        return LGBMClassifier(n_estimators=500, num_leaves=63, learning_rate=0.05,
                              min_child_samples=50, reg_lambda=1.0, n_jobs=N_JOBS,
                              random_state=seed, verbose=-1)
    if name == "MLP":
        return make_pipeline(*_log_scaler(), MLPClassifier(hidden_layer_sizes=(128, 64),
                                                           early_stopping=True, max_iter=40, batch_size=1024,
                                                           random_state=seed))
    raise ValueError(name)


MODELS = ["LR", "DT", "RF", "ET", "XGB", "LGBM", "MLP"]
EARLY_STOPPED = {"XGB", "LGBM"}
VAL_FRACTION = 0.1


def fit(name: str, model, X: np.ndarray, y: np.ndarray, seed: int):
    """Fit ``model``. Boosted models hold out 10% of the *training* data for
    early stopping, so the test set is never touched."""
    if name not in EARLY_STOPPED:
        model.fit(X, y)
        return model
    from sklearn.model_selection import train_test_split
    # Rows of very rare classes (<10 rows) always stay in the fitting part, so
    # every class is seen during fitting (XGBoost requires it).
    counts = np.bincount(y)
    rare = counts[y] < 10
    a, b = train_test_split(np.flatnonzero(~rare), test_size=VAL_FRACTION,
                            stratify=y[~rare], random_state=seed)
    a = np.concatenate([a, np.flatnonzero(rare)])
    if name == "XGB":
        model.fit(X[a], y[a], eval_set=[(X[b], y[b])], verbose=False)
    else:
        import lightgbm as lgb
        model.fit(X[a], y[a], eval_set=[(X[b], y[b])],
                  callbacks=[lgb.early_stopping(30, verbose=False)])
    return model
