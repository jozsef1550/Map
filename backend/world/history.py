"""
History & Timeline Simulation
==============================
Era system — each call to `advance_era` simulates one epoch:
  • Border friction between adjacent kingdoms (wars / territory shifts).
  • City population growth.
  • Random city destruction → Ruin nodes.
  • New minor cities founded.
"""
from __future__ import annotations

import math
import numpy as np

from .world_state import CityNode, Kingdom, HistoryEvent, ResourceNode
from .toponymy import ToponymyEngine
from .climate import SEA_LEVEL


def advance_era(
    era: int,
    heightmap: np.ndarray,
    kingdoms: list[Kingdom],
    cities: list[CityNode],
    influence_map: np.ndarray,
    resources: list[ResourceNode],
    toponymy: ToponymyEngine,
    seed: int,
) -> tuple[list[Kingdom], list[CityNode], np.ndarray, list[HistoryEvent]]:
    """
    Simulate one era step. Returns updated data + list of events.
    """
    H, W = heightmap.shape
    rng = np.random.default_rng(seed + era * 7777)
    events: list[HistoryEvent] = []

    # ---- 1. Border friction: kingdoms fight over shared borders ----
    new_influence = influence_map.copy()
    kingdom_power = {k.kingdom_id: k.power for k in kingdoms}

    # Find border pixels (adjacency)
    from scipy.ndimage import binary_erosion
    for kid_a in range(1, len(kingdoms) + 1):
        mask_a = influence_map == kid_a
        if not mask_a.any():
            continue
        # Erode mask; border pixels = mask_a & ~eroded_a
        eroded = binary_erosion(mask_a)
        border_pixels = mask_a & ~eroded
        border_rows, border_cols = np.where(border_pixels)

        for r, c in zip(border_rows, border_cols):
            # Check all neighbours
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if not (0 <= nr < H and 0 <= nc < W):
                    continue
                kid_b = influence_map[nr, nc]
                if kid_b == 0 or kid_b == kid_a:
                    continue
                # War: higher power kingdom takes the border cell
                pa = kingdom_power.get(kid_a, 1.0)
                pb = kingdom_power.get(kid_b, 1.0)
                if rng.random() < (pa / (pa + pb)):
                    new_influence[nr, nc] = kid_a
                    # chance of major war event
                    if rng.random() < 0.002:
                        ka = next((k for k in kingdoms if k.kingdom_id == kid_a), None)
                        kb = next((k for k in kingdoms if k.kingdom_id == kid_b), None)
                        if ka and kb:
                            events.append(HistoryEvent(
                                era=era,
                                event_type="war",
                                description=f"{ka.name} wages war on {kb.name}",
                                x=int(c), y=int(r),
                            ))

    # ---- 2. City growth ----
    for city in cities:
        if not city.is_ruin:
            growth = rng.integers(100, 1000)
            # bonus near resources
            near_res = sum(1 for r in resources
                           if abs(r.x - city.x) + abs(r.y - city.y) < 15)
            city.population += growth + near_res * 200
            if rng.random() < 0.04 * era:
                events.append(HistoryEvent(
                    era=era,
                    event_type="growth",
                    description=f"{city.name} grows to pop {city.population:,}",
                    x=city.x, y=city.y,
                ))

    # ---- 3. Random city destruction ----
    living = [c for c in cities if not c.is_ruin and not c.is_capital]
    if living and rng.random() < 0.15:
        target = rng.choice(living)
        target.is_ruin = True
        target.name = toponymy.ruin_name(target.kingdom_id)
        events.append(HistoryEvent(
            era=era,
            event_type="destroyed",
            description=f"{target.name} was razed",
            x=target.x, y=target.y,
        ))

    # ---- 4. Found new minor cities ----
    if rng.random() < 0.6:
        land_cells = list(zip(*np.where(heightmap >= SEA_LEVEL)))
        if land_cells:
            idx = rng.integers(0, len(land_cells))
            nr, nc = land_cells[idx]
            kid = int(new_influence[nr, nc]) or 1
            new_name = toponymy.city_name(kid, is_capital=False)
            cities.append(CityNode(
                x=int(nc), y=int(nr),
                name=new_name,
                kingdom_id=kid,
                population=rng.integers(200, 5000),
            ))
            events.append(HistoryEvent(
                era=era,
                event_type="founded",
                description=f"{new_name} was founded",
                x=int(nc), y=int(nr),
            ))

    # ---- 5. Update kingdom power ----
    for kingdom in kingdoms:
        kid = kingdom.kingdom_id
        mask = new_influence == kid
        res_count = sum(1 for r in resources if new_influence[r.y, r.x] == kid)
        area = int(mask.sum())
        kingdom.power = 1.0 + res_count * 2.0 + area / 500.0

    return kingdoms, cities, new_influence, events
