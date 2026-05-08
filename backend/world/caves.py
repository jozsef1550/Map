"""
Cave System — Layer −1
======================
3-D Cellular Automata to generate an interconnected tunnel network.

Rules (similar to cave-gen CA):
  Birth : a rock cell becomes empty if < BIRTH_LIMIT  neighbours are rock.
  Survive: an empty cell fills with rock if > DEATH_LIMIT neighbours are rock.

The cave grid is then biased toward mountain-range cells (high altitude)
so tunnels preferentially run through mountain ranges.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import label


def generate_caves(
    heightmap: np.ndarray,
    depth: int = 8,
    seed: int = 0,
    fill_prob: float = 0.48,
    iterations: int = 5,
    birth_limit: int = 13,
    death_limit: int = 13,
) -> np.ndarray:
    """
    Returns
    -------
    cave_map : uint8 [D, H, W]  — 0 = rock, 1 = open tunnel
    """
    H, W = heightmap.shape
    D = depth
    rng = np.random.default_rng(seed + 555)

    # ---- 1. Initial random fill biased by mountain height ----
    # High-altitude cells are more likely to start as rock (caves are
    # more likely beneath mountains — they start with more material).
    mountain_bias = np.clip((heightmap - 0.55) / 0.45, 0, 1)  # 0 at low, 1 at peaks

    cave = np.zeros((D, H, W), dtype=np.uint8)
    for d in range(D):
        depth_factor = 1.0 - d / (D - 1)   # deeper = sparser caves
        prob = fill_prob - mountain_bias * 0.15 * depth_factor
        cave[d] = (rng.random((H, W)) > prob).astype(np.uint8)

    # ---- 2. CA iterations ----
    for _ in range(iterations):
        cave = _ca_step(cave, birth_limit, death_limit)

    # ---- 3. Keep only the largest connected component ----
    cave = _keep_largest(cave)

    # ---- 4. Align with mountain ranges: force tunnels open under peaks ----
    peak_mask = heightmap > 0.80
    for d in range(D):
        # beneath peaks → guarantee some open cells at deeper layers
        if d >= D // 4:
            cave[d][peak_mask] = 1

    return cave.astype(np.uint8)


def _ca_step(cave: np.ndarray, birth_limit: int, death_limit: int) -> np.ndarray:
    """One generation of 3-D cellular automata (26-neighbour)."""
    D, H, W = cave.shape
    # Sum 3×3×3 neighbourhood (rock=0, open=1; count ROCK neighbours)
    from scipy.ndimage import uniform_filter
    # uniform_filter counts sum in 3x3x3 window including self
    neighbour_sum = np.zeros_like(cave, dtype=np.int32)
    from scipy.ndimage import generic_filter

    # Use convolution for speed
    from scipy.signal import fftconvolve
    kernel = np.ones((3, 3, 3), dtype=np.float32)
    rock_count = fftconvolve((1 - cave).astype(np.float32), kernel, mode='same')
    rock_count = np.round(rock_count).astype(np.int32) - (1 - cave).astype(np.int32)

    new_cave = cave.copy()
    # Open cell (1): survives if rock_count <= death_limit
    new_cave[cave == 1] = (rock_count[cave == 1] <= death_limit).astype(np.uint8)
    # Rock cell (0): born open if rock_count < birth_limit
    new_cave[cave == 0] = (rock_count[cave == 0] < birth_limit).astype(np.uint8)

    return new_cave


def _keep_largest(cave: np.ndarray) -> np.ndarray:
    """Retain only the largest connected component of open cells."""
    labeled, num = label(cave)
    if num == 0:
        return cave
    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0   # background
    largest = sizes.argmax()
    return (labeled == largest).astype(np.uint8)
