"""
Tectonic Layer
==============
• Generate N Voronoi plates with random motion vectors.
• Compute convergent / divergent boundary stress.
• Uplift at convergent boundaries → mountains.
• Subsidence at divergent boundaries → rifts / oceans.
• RBF-smooth the raw stress signal into a heightmap.
"""
from __future__ import annotations

import math
import random
import numpy as np
from scipy.spatial import Voronoi, cKDTree


def generate_tectonic(
    width: int,
    height: int,
    num_plates: int,
    tectonic_speed: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, list[tuple[float, float]], np.ndarray]:
    """
    Returns
    -------
    heightmap   : float32 [H, W]  0-1
    plate_map   : int32   [H, W]
    vectors     : list of (vx, vy) per plate
    boundary    : float32 [H, W]  boundary stress
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    W, H = width, height

    # ---- 1. Seed plate centres (with border wrap via mirroring) ----
    pts = rng.random((num_plates, 2)) * [W, H]

    # ---- 2. Voronoi partition ----
    # Tile by mirroring for wraparound-like effect on borders
    tiled = np.concatenate([
        pts + [0, 0],
        pts + [W, 0], pts + [-W, 0],
        pts + [0, H], pts + [0, -H],
    ])
    tree = cKDTree(tiled)

    ys, xs = np.mgrid[0:H, 0:W]
    coords = np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float32)
    _, idx = tree.query(coords)
    plate_map = (idx % num_plates).reshape(H, W).astype(np.int32)

    # ---- 3. Motion vectors ----
    angles = rng.uniform(0, 2 * math.pi, num_plates)
    speeds = rng.uniform(0.3, 1.0, num_plates) * tectonic_speed
    vectors: list[tuple[float, float]] = [
        (float(math.cos(a) * s), float(math.sin(a) * s))
        for a, s in zip(angles, speeds)
    ]

    # ---- 4. Boundary stress ----
    # For each pixel, check neighbouring pixels belonging to other plates.
    boundary = np.zeros((H, W), dtype=np.float32)
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        shifted = np.roll(np.roll(plate_map, dy, axis=0), dx, axis=1)
        is_boundary = (shifted != plate_map).astype(np.float32)
        # dot product of the two plate velocities towards each other
        for p in range(num_plates):
            mask_p = plate_map == p
            vx_p, vy_p = vectors[p]
            for q in range(p + 1, num_plates):
                mask_q = plate_map == q
                vx_q, vy_q = vectors[q]
                rel_vx = vx_p - vx_q
                rel_vy = vy_p - vy_q
                # direction of boundary normal (simplified as dx,dy)
                dot = rel_vx * dx + rel_vy * dy
                both = (mask_p | mask_q) & is_boundary.astype(bool)
                boundary[both] += dot
    boundary = _smooth(boundary, sigma=3)

    # ---- 5. Base heightmap from boundary stress + large-scale noise ----
    # Convergent (positive stress) → mountains
    # Divergent (negative stress) → rifts
    noise_base = _fractal_noise(H, W, seed=seed, octaves=6, persistence=0.55)
    # Normalise stress
    stress_norm = _normalise(boundary)

    height_raw = noise_base * 0.5 + stress_norm * 0.5

    # Ocean basins at divergent boundaries
    divergent = np.clip(-boundary, 0, None)
    divergent_norm = _normalise(divergent)
    height_raw -= divergent_norm * 0.35

    # ---- 6. Sea-level clamp and normalise ----
    heightmap = _normalise(height_raw).astype(np.float32)

    return heightmap, plate_map, vectors, boundary.astype(np.float32)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fractal_noise(H: int, W: int, seed: int, octaves: int = 6, persistence: float = 0.5) -> np.ndarray:
    """Pure-numpy fractal (fBm) noise via summed sine/cosine waves."""
    rng = np.random.default_rng(seed + 9999)
    ys, xs = np.mgrid[0:H, 0:W]
    result = np.zeros((H, W), dtype=np.float64)
    amplitude = 1.0
    frequency = 1.0
    max_val = 0.0
    for _ in range(octaves):
        # random sinusoidal components
        n_waves = 8
        angles = rng.uniform(0, 2 * math.pi, n_waves)
        phases = rng.uniform(0, 2 * math.pi, n_waves)
        layer = np.zeros((H, W), dtype=np.float64)
        for angle, phase in zip(angles, phases):
            kx = math.cos(angle) * frequency / W * 2 * math.pi
            ky = math.sin(angle) * frequency / H * 2 * math.pi
            layer += np.sin(xs * kx + ys * ky + phase)
        result += layer / n_waves * amplitude
        max_val += amplitude
        amplitude *= persistence
        frequency *= 2.0
    return result / max_val


def _smooth(arr: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Fast Gaussian blur via separable 1-D convolution."""
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(arr, sigma=sigma)


def _normalise(arr: np.ndarray) -> np.ndarray:
    lo, hi = arr.min(), arr.max()
    if hi == lo:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)
