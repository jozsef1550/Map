"""
Mana Layer
==========
• Simplex-like fractal noise map for mana density (0-1).
• Cells with mana > threshold trigger 'Warped Terrain':
    – heightmap is modified to create floating-island-like features
      (local uplift + inversion of surrounding terrain).
• Returns updated heightmap and the warp magnitude map.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.ndimage import gaussian_filter


def generate_mana(
    heightmap: np.ndarray,
    mana_level: float,
    mana_threshold: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns
    -------
    mana_map         : float32 [H, W]  (0-1)
    warp_map         : float32 [H, W]  (0-1) modification magnitude
    warped_heightmap : float32 [H, W]
    """
    H, W = heightmap.shape

    # ---- 1. Fractal noise for mana ----
    mana_raw = _mana_noise(H, W, seed, octaves=5, persistence=0.6)
    mana_map = (mana_raw * mana_level).clip(0, 1).astype(np.float32)

    # ---- 2. Warp terrain where mana > threshold ----
    warp_mask = (mana_map > mana_threshold).astype(np.float32)
    # Smooth warp zones
    warp_zone = gaussian_filter(warp_mask, sigma=4.0)

    # Warped terrain: invert and uplift — creates "floating island" pockets
    warp_delta = np.zeros_like(heightmap)
    high_mana = warp_zone > 0.1
    # Uplift the centre of high-mana zones
    warp_delta[high_mana] = warp_zone[high_mana] * 0.4
    # Create inverse hollow around them (visual floating-island effect)
    hollow = gaussian_filter(warp_zone, sigma=10.0) * 0.2
    warp_delta -= hollow

    warped_heightmap = np.clip(heightmap + warp_delta, 0, 1).astype(np.float32)
    warp_map = np.abs(warp_delta).astype(np.float32)
    if warp_map.max() > 0:
        warp_map /= warp_map.max()

    return mana_map, warp_map, warped_heightmap


# ---------------------------------------------------------------------------
# Fractal noise (numpy-only OpenSimplex approximation)
# ---------------------------------------------------------------------------

def _mana_noise(H: int, W: int, seed: int, octaves: int = 5, persistence: float = 0.5) -> np.ndarray:
    rng = np.random.default_rng(seed + 77777)
    ys, xs = np.mgrid[0:H, 0:W]
    result = np.zeros((H, W), dtype=np.float64)
    amplitude = 1.0
    frequency = 1.0
    max_val = 0.0
    for _ in range(octaves):
        n_waves = 6
        angles = rng.uniform(0, 2 * math.pi, n_waves)
        phases = rng.uniform(0, 2 * math.pi, n_waves)
        layer = np.zeros((H, W), dtype=np.float64)
        for angle, phase in zip(angles, phases):
            kx = math.cos(angle) * frequency / W * 2 * math.pi * 3
            ky = math.sin(angle) * frequency / H * 2 * math.pi * 3
            layer += np.sin(xs * kx + ys * ky + phase)
        result += layer / n_waves * amplitude
        max_val += amplitude
        amplitude *= persistence
        frequency *= 2.2  # slightly irrational to avoid aliasing
    result = result / max_val
    lo, hi = result.min(), result.max()
    return ((result - lo) / (hi - lo + 1e-9)).astype(np.float32)
