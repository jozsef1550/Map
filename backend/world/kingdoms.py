"""
Kingdom Generation — Influence Maps
====================================
• Place N capital cities on land, spread apart.
• Grow kingdom borders outward using a weighted Dijkstra flood-fill.
• Kingdom 'Power' depends on resources within borders + cave access.
• Colour each kingdom uniquely.
"""
from __future__ import annotations

import heapq
import math
import numpy as np

from .world_state import CityNode, Kingdom, ResourceNode
from .climate import SEA_LEVEL


KINGDOM_COLORS = [
    (180, 40,  40),   # crimson
    (40,  80, 180),   # royal blue
    (40, 160,  60),   # forest green
    (160, 120, 20),   # gold
    (140,  40, 140),  # purple
    (20,  160, 160),  # teal
    (200, 100,  20),  # orange
    (80,  20, 160),   # violet
    (160,  80,  80),  # rose
    (20,  100,  60),  # dark green
    (80,  80, 160),   # slate
    (160,  60,  20),  # brown
]


def generate_kingdoms(
    heightmap: np.ndarray,
    resources: list[ResourceNode],
    cave_map: np.ndarray,
    toponymy_engine,
    seed: int,
    num_kingdoms: int = 6,
) -> tuple[list[Kingdom], list[CityNode], np.ndarray]:
    """
    Returns
    -------
    kingdoms      : list of Kingdom
    cities        : list of CityNode (capitals only)
    influence_map : int32 [H, W] — kingdom_id (0 = unclaimed/ocean)
    """
    H, W = heightmap.shape
    rng = np.random.default_rng(seed + 2024)

    land_cells = list(zip(*np.where(heightmap >= SEA_LEVEL)))
    if len(land_cells) < num_kingdoms:
        num_kingdoms = max(1, len(land_cells) // 4)

    # ---- 1. Place capitals well spread apart ----
    capitals: list[tuple[int, int]] = []   # (row, col)
    attempts = 0
    min_dist = min(H, W) // (num_kingdoms + 1)
    while len(capitals) < num_kingdoms and attempts < 5000:
        attempts += 1
        idx = rng.integers(0, len(land_cells))
        r, c = land_cells[idx]
        if all(math.sqrt((r-cr)**2+(c-cc)**2) > min_dist for cr, cc in capitals):
            capitals.append((r, c))

    num_kingdoms = len(capitals)

    # ---- 2. Build kingdoms metadata ----
    kingdoms: list[Kingdom] = []
    cities: list[CityNode] = []
    for kid, (cr, cc) in enumerate(capitals, start=1):
        color = KINGDOM_COLORS[(kid - 1) % len(KINGDOM_COLORS)]
        name = toponymy_engine.kingdom_name(kid)
        kingdoms.append(Kingdom(
            kingdom_id=kid,
            name=name,
            capital_x=int(cc),
            capital_y=int(cr),
            color=color,
            power=1.0,
        ))
        capital_name = toponymy_engine.city_name(kid, is_capital=True)
        cities.append(CityNode(
            x=int(cc), y=int(cr),
            name=capital_name,
            kingdom_id=kid,
            population=int(rng.integers(5000, 50000)),
            is_capital=True,
        ))

    # ---- 3. Flood-fill influence map ----
    # Cost = terrain ruggedness; kingdom with lower cost claims cell
    influence_map = np.zeros((H, W), dtype=np.int32)
    dist = np.full((H, W), np.inf)

    heap: list[tuple[float, int, int, int]] = []
    for kid, (cr, cc) in enumerate(capitals, start=1):
        dist[cr, cc] = 0.0
        influence_map[cr, cc] = kid
        heapq.heappush(heap, (0.0, kid, cr, cc))

    gy, gx = np.gradient(heightmap)
    steepness = np.sqrt(gx**2 + gy**2)

    while heap:
        d, kid, r, c = heapq.heappop(heap)
        if d > dist[r, c]:
            continue
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if not (0 <= nr < H and 0 <= nc < W):
                continue
            if heightmap[nr, nc] < SEA_LEVEL:
                continue
            nd = d + 1.0 + steepness[nr, nc] * 10.0
            if nd < dist[nr, nc]:
                dist[nr, nc] = nd
                influence_map[nr, nc] = kid
                heapq.heappush(heap, (nd, kid, nr, nc))

    # ---- 4. Compute kingdom power ----
    res_resource = {r.resource_type: r.amount for r in resources}
    cave_surface = cave_map.any(axis=0).astype(np.float32)  # any tunnel below

    for kingdom in kingdoms:
        kid = kingdom.kingdom_id
        mask = influence_map == kid
        res_count = sum(1 for r in resources if influence_map[r.y, r.x] == kid)
        cave_access = int(cave_surface[mask].sum() > 10)
        area = int(mask.sum())
        kingdom.power = 1.0 + res_count * 2.0 + cave_access * 3.0 + area / 500.0

    return kingdoms, cities, influence_map
