"""
Pathfinding — A* for Roads
===========================
Cost function combines:
  • terrain steepness (gradient magnitude)
  • elevation (high altitude = expensive)
  • economic_weight inverse (roads prioritise connecting resources to ports)
"""
from __future__ import annotations

import heapq
import math
import numpy as np

from .world_state import ResourceNode, RoadEdge
from .climate import SEA_LEVEL


def build_roads(
    heightmap: np.ndarray,
    resources: list[ResourceNode],
    cities: list,   # list of CityNode
    seed: int,
) -> list[RoadEdge]:
    """
    Connect each capital city to its nearest port/coast and to the
    two nearest resource nodes using A*.
    """
    H, W = heightmap.shape
    cost_map = _build_cost_map(heightmap)
    roads: list[RoadEdge] = []

    # Find port cells (ocean cells adjacent to land)
    from scipy.ndimage import binary_dilation
    land = heightmap >= SEA_LEVEL
    ocean = ~land
    coast = binary_dilation(ocean) & land

    coast_coords = list(zip(*np.where(coast)))
    if not coast_coords:
        return roads

    for city in cities:
        cx, cy = city.x, city.y
        # 1) Road to nearest coast
        nearest_port = min(coast_coords, key=lambda p: abs(p[0]-cy) + abs(p[1]-cx))
        path = astar(cost_map, (cy, cx), nearest_port)
        if path:
            roads.append(_path_to_edge(cx, cy, int(nearest_port[1]), int(nearest_port[0]), path))

        # 2) Roads to nearest 2 resource nodes
        res_land = [r for r in resources if heightmap[r.y, r.x] >= SEA_LEVEL]
        sorted_res = sorted(res_land, key=lambda r: abs(r.y-cy) + abs(r.x-cx))
        for res in sorted_res[:2]:
            path = astar(cost_map, (cy, cx), (res.y, res.x))
            if path:
                roads.append(_path_to_edge(cx, cy, int(res.x), int(res.y), path))

    return roads


def astar(
    cost_map: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """A* on a grid. Returns list of (row, col) from start to goal, or []."""
    H, W = cost_map.shape
    sr, sc = start
    gr, gc = goal
    if not (_valid(sr, sc, H, W) and _valid(gr, gc, H, W)):
        return []
    if start == goal:
        return [start]

    def h(r: int, c: int) -> float:
        return math.sqrt((r - gr)**2 + (c - gc)**2)

    open_heap: list[tuple[float, int, int]] = []
    heapq.heappush(open_heap, (h(sr, sc), sr, sc))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {(sr, sc): 0.0}
    closed: set[tuple[int, int]] = set()

    while open_heap:
        _, r, c = heapq.heappop(open_heap)
        node = (r, c)
        if node == (gr, gc):
            return _reconstruct(came_from, node)
        if node in closed:
            continue
        closed.add(node)

        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            nr, nc = r + dr, c + dc
            if not _valid(nr, nc, H, W) or (nr, nc) in closed:
                continue
            step_cost = cost_map[nr, nc] * (1.414 if dr != 0 and dc != 0 else 1.0)
            tent_g = g_score[node] + step_cost
            if tent_g < g_score.get((nr, nc), float('inf')):
                came_from[(nr, nc)] = node
                g_score[(nr, nc)] = tent_g
                heapq.heappush(open_heap, (tent_g + h(nr, nc), nr, nc))
    return []


def _reconstruct(came_from: dict, current: tuple[int, int]) -> list[tuple[int, int]]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _build_cost_map(heightmap: np.ndarray) -> np.ndarray:
    """Higher cost for steep terrain and deep ocean."""
    gy, gx = np.gradient(heightmap)
    steepness = np.sqrt(gx**2 + gy**2)
    # Ocean is impassable (high cost)
    ocean_cost = (heightmap < SEA_LEVEL).astype(np.float32) * 50.0
    cost = 1.0 + steepness * 30.0 + ocean_cost
    return cost.astype(np.float32)


def _valid(r: int, c: int, H: int, W: int) -> bool:
    return 0 <= r < H and 0 <= c < W


def _path_to_edge(x0: int, y0: int, x1: int, y1: int,
                  path: list[tuple[int, int]]) -> RoadEdge:
    # path is [(row,col),...]; convert to (x,y)
    xy_path = [(c, r) for r, c in path]
    return RoadEdge(x0=x0, y0=y0, x1=x1, y1=y1, path=xy_path)
