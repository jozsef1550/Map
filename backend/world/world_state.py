"""
WorldState — central data container for all simulation layers.
All 2-D layers are stored as flat Python lists so they can be
JSON-serialised directly from FastAPI without extra conversion.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldParams:
    seed: int = 42
    width: int = 256
    height: int = 256
    num_plates: int = 12
    tectonic_speed: float = 1.0
    rainfall: float = 1.0
    mana_level: float = 0.5
    mana_threshold: float = 0.75
    season: float = 0.0          # 0 = summer, 1 = winter
    erosion_iterations: int = 60000
    era: int = 0


@dataclass
class CityNode:
    x: int
    y: int
    name: str
    kingdom_id: int
    population: int = 1000
    is_capital: bool = False
    is_ruin: bool = False


@dataclass
class ResourceNode:
    x: int
    y: int
    resource_type: str   # "iron","gold","fertile","mana_crystal","timber","fish"
    amount: float = 1.0


@dataclass
class RoadEdge:
    x0: int
    y0: int
    x1: int
    y1: int
    path: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Kingdom:
    kingdom_id: int
    name: str
    capital_x: int
    capital_y: int
    color: tuple[int, int, int] = (128, 128, 128)
    power: float = 1.0


@dataclass
class HistoryEvent:
    era: int
    event_type: str   # "war","founded","destroyed","growth"
    description: str
    x: int = 0
    y: int = 0


@dataclass
class WorldState:
    world_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    params: WorldParams = field(default_factory=WorldParams)

    # --- Layer 0: Tectonic / Height ---
    heightmap: list[float] = field(default_factory=list)          # [H*W]
    plate_map: list[int] = field(default_factory=list)             # [H*W] plate index
    plate_vectors: list[tuple[float, float]] = field(default_factory=list)  # [num_plates]
    boundary_map: list[float] = field(default_factory=list)        # [H*W] boundary stress

    # --- Layer 1: Climate ---
    temperature: list[float] = field(default_factory=list)         # [H*W]
    precipitation: list[float] = field(default_factory=list)       # [H*W]
    biome_map: list[int] = field(default_factory=list)             # [H*W] biome index
    river_map: list[float] = field(default_factory=list)           # [H*W] water flow

    # --- Layer 2: Mana ---
    mana_map: list[float] = field(default_factory=list)            # [H*W]
    warp_map: list[float] = field(default_factory=list)            # [H*W] terrain modification

    # --- Layer -1: Caves ---
    cave_map: list[int] = field(default_factory=list)              # [D*H*W] 0=rock 1=open
    cave_depth: int = 8

    # --- Layer 3: Resources & Economy ---
    resources: list[ResourceNode] = field(default_factory=list)
    roads: list[RoadEdge] = field(default_factory=list)
    cities: list[CityNode] = field(default_factory=list)

    # --- Layer 4: Kingdoms ---
    kingdoms: list[Kingdom] = field(default_factory=list)
    influence_map: list[int] = field(default_factory=list)         # [H*W] kingdom_id

    # --- Layer 5: History ---
    history: list[HistoryEvent] = field(default_factory=list)
    current_era: int = 0

    # --- Metadata ---
    biome_names: list[str] = field(default_factory=list)
    generated: bool = False
