"""
Resource Placement
==================
Procedurally place resource nodes based on geological context:

  Iron          → near convergent plate boundaries (high boundary stress, land)
  Gold          → near volcanic/high-stress mountain summits
  Fertile Soil  → river deltas (high river flow, near sea level)
  Mana Crystals → high mana density
  Timber        → forest biomes
  Fish          → coastal ocean cells
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .world_state import ResourceNode
from .climate import SEA_LEVEL, BIOME_NAMES

FOREST_BIOMES = {3, 4, 5, 8, 9, 10}  # boreal, temperate, rainforest …


def place_resources(
    heightmap: np.ndarray,
    boundary_map: np.ndarray,
    mana_map: np.ndarray,
    river_map: np.ndarray,
    biome_map: np.ndarray,
    seed: int,
    n_iron: int = 14,
    n_gold: int = 8,
    n_fertile: int = 12,
    n_mana: int = 10,
    n_timber: int = 10,
    n_fish: int = 12,
) -> list[ResourceNode]:
    rng = np.random.default_rng(seed + 999)
    H, W = heightmap.shape
    nodes: list[ResourceNode] = []

    land = heightmap >= SEA_LEVEL
    ocean = ~land

    # ---- Iron: convergent boundary stress + land ----
    iron_score = gaussian_filter(np.clip(boundary_map, 0, None), sigma=5) * land
    nodes += _sample_nodes(iron_score, n_iron, "iron", rng, H, W)

    # ---- Gold: high altitude + high stress ----
    gold_score = np.clip(boundary_map, 0, None) * np.clip(heightmap - 0.70, 0, None) * land
    gold_score = gaussian_filter(gold_score, sigma=3)
    nodes += _sample_nodes(gold_score, n_gold, "gold", rng, H, W)

    # ---- Fertile Soil: delta zones (high river flow near sea) ----
    near_sea = gaussian_filter(ocean.astype(np.float32), sigma=8)
    fertile_score = river_map * near_sea * land
    nodes += _sample_nodes(fertile_score, n_fertile, "fertile", rng, H, W)

    # ---- Mana Crystals: high mana density ----
    mana_score = mana_map * land
    nodes += _sample_nodes(mana_score, n_mana, "mana_crystal", rng, H, W)

    # ---- Timber: forest biomes ----
    forest_mask = np.zeros((H, W), dtype=np.float32)
    for b in FOREST_BIOMES:
        forest_mask[biome_map == b] = 1.0
    nodes += _sample_nodes(forest_mask, n_timber, "timber", rng, H, W)

    # ---- Fish: coastal ocean ----
    coast_dist = gaussian_filter(land.astype(np.float32), sigma=3)
    fish_score = coast_dist * ocean
    nodes += _sample_nodes(fish_score, n_fish, "fish", rng, H, W)

    return nodes


def _sample_nodes(
    score: np.ndarray,
    count: int,
    resource_type: str,
    rng: np.random.Generator,
    H: int,
    W: int,
) -> list[ResourceNode]:
    """Sample 'count' cells with probability proportional to score."""
    flat = score.ravel()
    total = flat.sum()
    if total <= 0:
        return []
    prob = flat / total
    chosen = rng.choice(H * W, size=min(count, (flat > 0).sum()), replace=False, p=prob)
    nodes = []
    for idx in chosen:
        iy, ix = divmod(int(idx), W)
        amount = float(score[iy, ix] / (score.max() + 1e-9))
        nodes.append(ResourceNode(x=ix, y=iy, resource_type=resource_type, amount=amount))
    return nodes
