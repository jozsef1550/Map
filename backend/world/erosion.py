"""
Erosion Layer
=============
Particle-based hydraulic erosion:
  • Drop water particles from random positions.
  • Particles flow downhill, erode terrain, carry sediment.
  • Deposit sediment when speed decreases or water evaporates.
  • River path tracking: accumulate flow for river visualisation.
  • Delta detection: high-sediment zones near sea level → Wetland biome hint.
"""
from __future__ import annotations

import math
import numpy as np


SEA_LEVEL = 0.35


def erode(
    heightmap: np.ndarray,
    iterations: int = 60_000,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns
    -------
    eroded_heightmap : float32 [H, W]
    river_map        : float32 [H, W]  — accumulated water flow (0-1)
    """
    H, W = heightmap.shape
    hmap = heightmap.copy().astype(np.float64)
    river_map = np.zeros((H, W), dtype=np.float64)

    rng = np.random.default_rng(seed + 42)

    # Erosion hyper-params
    inertia        = 0.05
    capacity_factor = 8.0
    deposition_spd  = 0.3
    erosion_spd     = 0.3
    evaporation     = 0.01
    min_slope       = 0.001
    gravity         = 4.0
    max_steps       = 64

    # Only erode land cells
    for _ in range(iterations):
        # Random start on land
        px = rng.uniform(0, W - 1)
        py = rng.uniform(0, H - 1)

        vx, vy = 0.0, 0.0
        water  = 1.0
        sediment = 0.0

        for _step in range(max_steps):
            ix, iy = int(px), int(py)
            if ix < 0 or ix >= W - 1 or iy < 0 or iy >= H - 1:
                break
            if hmap[iy, ix] < SEA_LEVEL:
                # Deposit all sediment at sea entry
                hmap[iy, ix] += sediment
                break

            # Bilinear height and gradient at (px, py)
            u = px - ix
            v = py - iy
            h00 = hmap[iy,   ix]
            h10 = hmap[iy,   ix+1]
            h01 = hmap[iy+1, ix]
            h11 = hmap[iy+1, ix+1]
            h_cur = h00*(1-u)*(1-v) + h10*u*(1-v) + h01*(1-u)*v + h11*u*v

            gx = (h10 - h00)*(1-v) + (h11 - h01)*v
            gy = (h01 - h00)*(1-u) + (h11 - h10)*u

            # Update velocity
            vx = vx * inertia - gx * (1 - inertia) * gravity
            vy = vy * inertia - gy * (1 - inertia) * gravity
            speed = math.sqrt(vx*vx + vy*vy)
            if speed < 1e-10:
                break
            vx /= speed
            vy /= speed

            # New position
            nx = px + vx
            ny = py + vy
            nix, niy = int(nx), int(ny)
            if nix < 0 or nix >= W-1 or niy < 0 or niy >= H-1:
                break

            # Height difference
            u2 = nx - nix
            v2 = ny - niy
            h_new = (hmap[niy,   nix]*(1-u2)*(1-v2)
                    + hmap[niy,   nix+1]*u2*(1-v2)
                    + hmap[niy+1, nix]*(1-u2)*v2
                    + hmap[niy+1, nix+1]*u2*v2)
            dh = h_new - h_cur

            # Sediment capacity
            capacity = max(-dh, min_slope) * speed * water * capacity_factor

            if sediment > capacity or dh > 0:
                # Deposit
                deposit = (dh > 0) * min(dh, sediment) + (dh <= 0) * (sediment - capacity) * deposition_spd
                sediment -= deposit
                # Deposit weight over bilinear footprint
                _deposit_bilinear(hmap, ix, iy, u, v, deposit)
            else:
                # Erode
                erode_amt = min((capacity - sediment) * erosion_spd, -dh)
                sediment += erode_amt
                _deposit_bilinear(hmap, ix, iy, u, v, -erode_amt)

            # River accumulation
            river_map[iy, ix] += water * 0.001

            px, py = nx, ny
            water *= (1 - evaporation)
            if water < 0.01:
                break

    # Normalise river map
    if river_map.max() > 0:
        river_map = (river_map / river_map.max()).astype(np.float32)

    return hmap.astype(np.float32), river_map.astype(np.float32)


def _deposit_bilinear(hmap: np.ndarray, ix: int, iy: int,
                      u: float, v: float, amount: float) -> None:
    H, W = hmap.shape
    if ix+1 >= W or iy+1 >= H:
        return
    hmap[iy,   ix]   += amount * (1-u) * (1-v)
    hmap[iy,   ix+1] += amount * u     * (1-v)
    hmap[iy+1, ix]   += amount * (1-u) * v
    hmap[iy+1, ix+1] += amount * u     * v
