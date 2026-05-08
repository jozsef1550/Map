"""
Climate Layer
=============
• Temperature  : latitude (row) + altitude cooling
• Prevailing winds & moisture advection → rainfall
• Rain-shadow  : moisture is blocked by mountains
• Biome        : Whittaker plot (temp × precipitation)
• Season slider: modifies snowline and river-freeze threshold
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

# ---------------------------------------------------------------------------
# Biome indices
# ---------------------------------------------------------------------------
BIOME_NAMES = [
    "Ocean",          # 0
    "Ice / Polar",    # 1
    "Tundra",         # 2
    "Boreal Forest",  # 3
    "Temperate Forest",  # 4
    "Temperate Rainforest",  # 5
    "Shrubland",      # 6
    "Woodland / Savanna",  # 7
    "Subtropical Forest",  # 8
    "Tropical Forest",  # 9
    "Tropical Rainforest",  # 10
    "Desert",         # 11
    "Wetland / Delta",  # 12
    "Snow / Glacier",  # 13
    "Beach",          # 14
]

SEA_LEVEL = 0.35   # anything below this is ocean


def _whittaker(temp_c: float, precip_mm: float) -> int:
    """Return biome index from temperature (°C) and precipitation (mm/yr)."""
    if precip_mm < 250:
        if temp_c < 5:
            return 1   # Polar ice
        return 11      # Desert
    if temp_c < -5:
        return 1       # Polar
    if temp_c < 3:
        return 2       # Tundra
    if temp_c < 8:
        if precip_mm < 500:
            return 3   # Boreal
        return 3
    if temp_c < 15:
        if precip_mm < 500:
            return 6   # Shrubland
        if precip_mm < 1500:
            return 4   # Temperate Forest
        return 5       # Temperate Rainforest
    if temp_c < 20:
        if precip_mm < 500:
            return 11  # Hot desert
        if precip_mm < 1000:
            return 7   # Savanna
        if precip_mm < 2000:
            return 8   # Subtropical
        return 9       # Tropical Forest
    # > 20°C
    if precip_mm < 500:
        return 11
    if precip_mm < 1000:
        return 7       # Savanna
    if precip_mm < 2000:
        return 9       # Tropical Forest
    return 10          # Tropical Rainforest


def generate_climate(
    heightmap: np.ndarray,
    seed: int,
    rainfall_factor: float = 1.0,
    season: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Parameters
    ----------
    heightmap       : float32 [H, W]  0-1
    seed            : RNG seed
    rainfall_factor : global scale for precipitation
    season          : 0=summer, 1=winter

    Returns
    -------
    temperature   : float32 [H, W]  in °C  (−40 … +35)
    precipitation : float32 [H, W]  in mm/yr
    biome_map     : int32   [H, W]
    """
    H, W = heightmap.shape
    rng = np.random.default_rng(seed + 1)

    # ---- 1. Base temperature: latitude gradient ----
    # Row 0 = "north pole" (cold), row H/2 = "equator" (hot), row H = "south pole"
    lat = np.linspace(0, 1, H)[:, None] * np.ones((1, W))
    lat_temp = 35.0 * np.sin(lat * np.pi) - 10.0  # −10 at poles, +35 at equator
    # Season modifier: shifts temperature by ±12°C
    lat_temp -= season * 12.0

    # Altitude cooling: −6.5°C per 1000 m; map 0-1 to 0-5000 m
    altitude_m = heightmap * 5000.0
    altitude_m[heightmap < SEA_LEVEL] = 0.0
    altitude_cooling = altitude_m / 1000.0 * 6.5

    temperature = (lat_temp - altitude_cooling).astype(np.float32)

    # ---- 2. Base moisture from ocean proximity ----
    ocean_mask = heightmap < SEA_LEVEL
    from scipy.ndimage import distance_transform_edt
    ocean_dist = distance_transform_edt(~ocean_mask).astype(np.float32)
    max_dist = max(ocean_dist.max(), 1.0)
    moisture_base = np.exp(-ocean_dist / (max_dist * 0.3)) * 2500.0 * rainfall_factor

    # ---- 3. Prevailing winds (simplified westerlies + trade winds) ----
    # Winds blow west→east in mid-latitudes, east→west in tropics
    wind_dir = np.zeros((H, W, 2), dtype=np.float32)  # (dy, dx)
    for i in range(H):
        fraction = i / H
        # Trade winds (0-30° lat equiv) blow towards equator (westward)
        if fraction < 0.25 or fraction > 0.75:
            wind_dir[i, :, 1] = -1.0   # blowing from east
        else:
            wind_dir[i, :, 1] = 1.0    # westerlies blowing eastward

    # Advect moisture along wind direction
    moisture = moisture_base.copy()
    steps = 40
    for _ in range(steps):
        # shift moisture eastward (where westerlies) / westward (trade)
        shifted_e = np.roll(moisture, -1, axis=1)  # eastward
        shifted_w = np.roll(moisture, 1, axis=1)   # westward
        wind_east = (wind_dir[:, :, 1] > 0).astype(np.float32)
        moisture_advected = wind_east * shifted_e + (1 - wind_east) * shifted_w
        # Mountain barrier: terrain above 0.65 blocks 30% per step
        barrier = np.clip((heightmap - 0.65) / 0.35, 0, 1)
        moisture = moisture_advected * (1 - barrier * 0.30)
        # Restore ocean moisture
        moisture[ocean_mask] = moisture_base[ocean_mask]

    # ---- 4. Rain shadow: leeward side of mountains ----
    # Gradient of heightmap along wind direction
    grad_x = np.gradient(heightmap, axis=1)
    # If wind is eastward, eastern slope is leeward
    leeward = np.clip(grad_x * wind_dir[:, :, 1], 0, None)
    rain_shadow_reduction = gaussian_filter(leeward * 3000.0, sigma=5)
    moisture = np.clip(moisture - rain_shadow_reduction, 50.0, None)

    # ---- 5. Season: winter → less precipitation ----
    moisture *= 1.0 - season * 0.35

    precipitation = moisture.astype(np.float32)

    # ---- 6. Biome assignment via Whittaker plot ----
    biome_map = np.zeros((H, W), dtype=np.int32)
    for iy in range(H):
        for ix in range(W):
            if heightmap[iy, ix] < SEA_LEVEL:
                biome_map[iy, ix] = 0   # Ocean
            else:
                t = float(temperature[iy, ix])
                p = float(precipitation[iy, ix])
                biome_map[iy, ix] = _whittaker(t, p)

    # Snow / glacier override: season winter + high altitude
    snowline = 0.70 - season * 0.20
    biome_map[heightmap > snowline] = 13  # Snow

    # Beach: just above sea level
    beach_mask = (heightmap >= SEA_LEVEL) & (heightmap < SEA_LEVEL + 0.03)
    biome_map[beach_mask] = 14

    return temperature, precipitation, biome_map
