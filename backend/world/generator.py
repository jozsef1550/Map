"""
WorldGenerator — orchestrates all layer generators into a single WorldState.
"""
from __future__ import annotations

import numpy as np

from .world_state import WorldState, WorldParams, HistoryEvent
from .tectonic import generate_tectonic
from .climate import generate_climate, BIOME_NAMES
from .erosion import erode
from .mana import generate_mana
from .caves import generate_caves
from .resources import place_resources
from .pathfinding import build_roads
from .kingdoms import generate_kingdoms
from .history import advance_era
from .toponymy import ToponymyEngine


def generate_world(params: WorldParams) -> WorldState:
    W = params.width
    H = params.height

    state = WorldState(params=params)
    state.biome_names = BIOME_NAMES

    topo = ToponymyEngine(params.seed)

    # ── Phase 1: Tectonic ──────────────────────────────────────────────────
    print("[gen] tectonic…")
    heightmap, plate_map, vectors, boundary = generate_tectonic(
        W, H, params.num_plates, params.tectonic_speed, params.seed
    )

    # ── Phase 1: Erosion ───────────────────────────────────────────────────
    print("[gen] erosion…")
    heightmap, river_map = erode(heightmap, params.erosion_iterations, params.seed)

    # ── Phase 1: Climate ───────────────────────────────────────────────────
    print("[gen] climate…")
    temperature, precipitation, biome_map = generate_climate(
        heightmap, params.seed, params.rainfall, params.season
    )

    # ── Phase 2: Mana ─────────────────────────────────────────────────────
    print("[gen] mana…")
    mana_map, warp_map, heightmap = generate_mana(
        heightmap, params.mana_level, params.mana_threshold, params.seed
    )

    # ── Phase 2: Caves ────────────────────────────────────────────────────
    print("[gen] caves…")
    cave_map = generate_caves(heightmap, seed=params.seed)

    # ── Phase 3: Resources ────────────────────────────────────────────────
    print("[gen] resources…")
    resources = place_resources(
        heightmap, boundary, mana_map, river_map, biome_map, params.seed
    )

    # ── Phase 3: Kingdoms ─────────────────────────────────────────────────
    print("[gen] kingdoms…")
    kingdoms, cities, influence_map = generate_kingdoms(
        heightmap, resources, cave_map, topo, params.seed
    )

    # ── Phase 3: Roads ────────────────────────────────────────────────────
    print("[gen] roads…")
    roads = build_roads(heightmap, resources, cities, params.seed)

    # ── Phase 4: Initial history ──────────────────────────────────────────
    print("[gen] history init…")
    kingdoms, cities, influence_map, events = advance_era(
        0, heightmap, kingdoms, cities, influence_map, resources, topo, params.seed
    )

    # ── Serialise into WorldState ─────────────────────────────────────────
    print("[gen] serialising…")
    state.heightmap = heightmap.ravel().tolist()
    state.plate_map = plate_map.ravel().tolist()
    state.plate_vectors = vectors
    state.boundary_map = boundary.ravel().tolist()

    state.temperature = temperature.ravel().tolist()
    state.precipitation = precipitation.ravel().tolist()
    state.biome_map = biome_map.ravel().tolist()
    state.river_map = river_map.ravel().tolist()

    state.mana_map = mana_map.ravel().tolist()
    state.warp_map = warp_map.ravel().tolist()

    state.cave_map = cave_map.ravel().tolist()
    state.cave_depth = cave_map.shape[0]

    state.resources = resources
    state.roads = roads
    state.cities = cities
    state.kingdoms = kingdoms
    state.influence_map = influence_map.ravel().tolist()

    state.history = events
    state.current_era = 0
    state.generated = True

    print("[gen] done.")
    return state


def advance_world_era(state: WorldState) -> WorldState:
    """Advance the world timeline by one era."""
    H, W = state.params.height, state.params.width
    topo = ToponymyEngine(state.params.seed)

    heightmap = np.array(state.heightmap, dtype=np.float32).reshape(H, W)
    influence_map = np.array(state.influence_map, dtype=np.int32).reshape(H, W)
    new_era = state.current_era + 1

    kingdoms, cities, influence_map, events = advance_era(
        new_era, heightmap, state.kingdoms, state.cities,
        influence_map, state.resources, topo, state.params.seed
    )

    state.kingdoms = kingdoms
    state.cities = cities
    state.influence_map = influence_map.ravel().tolist()
    state.history += events
    state.current_era = new_era
    return state
