"""Subset-construction strategies compared in E4.

All of them draw ``budget`` rows from a training pool (positional indices
``pool`` into the full frame) and return positional indices.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .data import exact_duplicate_mask


def _alloc_proportional(counts: pd.Series, budget: int) -> pd.Series:
    # Eq. 1 of Martinez-Fuentes et al. (2026): S_c = int(P_c * S_total)
    return (counts / counts.sum() * budget).astype(int)


def _alloc_floor(counts: pd.Series, budget: int, floor: int) -> pd.Series:
    """Proportional allocation, but every class gets at least
    min(floor, available) rows. The extra rows are taken from the other
    classes in proportion to their size, so the total stays at the budget."""
    base = np.minimum(counts, floor)
    rest = budget - base.sum()
    spare = (counts - base).clip(lower=0)
    extra = (spare / spare.sum() * rest).astype(int)
    return np.minimum(base + extra, counts).astype(int)


def draw(df: pd.DataFrame, pool: np.ndarray, strategy: str, budget: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    attack = df[C.ATTACK].to_numpy()

    if strategy == "uniform":                       # non-stratified random baseline
        return np.sort(rng.choice(pool, size=min(budget, len(pool)), replace=False))

    if strategy == "proportional":                  # the original paper's Step 5
        cand = pool
        alloc_fn = _alloc_proportional
    elif strategy == "dedup_proportional":          # remove exact duplicates first
        dup = exact_duplicate_mask(df)
        cand = pool[~dup[pool]]
        alloc_fn = _alloc_proportional
    elif strategy == "floor":                       # proportional + minimum class floor
        cand = pool
        alloc_fn = lambda c, b: _alloc_floor(c, b, C.CLASS_FLOOR)  # noqa: E731
    else:
        raise ValueError(strategy)

    counts = pd.Series(attack[cand]).value_counts().sort_index()
    alloc = alloc_fn(counts, budget)
    picks = []
    for cls, n in alloc.items():
        members = cand[attack[cand] == cls]
        picks.append(rng.choice(members, size=int(min(n, len(members))), replace=False))
    return np.sort(np.concatenate(picks))


STRATEGIES = ["uniform", "proportional", "dedup_proportional", "floor"]
