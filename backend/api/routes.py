"""
FastAPI routes
==============
REST:
  POST /api/generate          — generate a new world
  GET  /api/world/{id}        — retrieve world state
  POST /api/world/{id}/advance — step timeline forward
  POST /api/world/{id}/edit   — apply a brush edit
  GET  /api/world/{id}/export/png
  GET  /api/world/{id}/export/svg

WebSocket:
  WS   /ws/{id}               — push progress updates
"""
from __future__ import annotations

import asyncio
import io
import json
import uuid
from dataclasses import asdict
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from world.world_state import WorldParams, WorldState, ResourceNode, CityNode
from world.generator import generate_world, advance_world_era
from world.climate import BIOME_NAMES, SEA_LEVEL
from world.pathfinding import astar, _build_cost_map

router = APIRouter()

# In-memory world store (for demo; swap for DB in production)
_worlds: dict[str, WorldState] = {}


# ---------------------------------------------------------------------------
# Pydantic I/O models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    seed: int = 42
    width: int = 256
    height: int = 256
    num_plates: int = 12
    tectonic_speed: float = 1.0
    rainfall: float = 1.0
    mana_level: float = 0.5
    mana_threshold: float = 0.75
    season: float = 0.0
    erosion_iterations: int = 60000


class EditRequest(BaseModel):
    tool: str           # "raise", "lower", "smooth", "place_city", "place_road"
    x: int
    y: int
    radius: int = 5
    strength: float = 0.05
    extra: dict = {}


# ---------------------------------------------------------------------------
# Helper — serialise WorldState to dict
# ---------------------------------------------------------------------------

def _state_dict(state: WorldState) -> dict:
    d = asdict(state)
    # Convert RoadEdge path lists of tuples (may be stored as lists already)
    return d


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate(req: GenerateRequest):
    params = WorldParams(
        seed=req.seed,
        width=req.width,
        height=req.height,
        num_plates=req.num_plates,
        tectonic_speed=req.tectonic_speed,
        rainfall=req.rainfall,
        mana_level=req.mana_level,
        mana_threshold=req.mana_threshold,
        season=req.season,
        erosion_iterations=req.erosion_iterations,
    )
    # Run in thread pool to avoid blocking event loop
    loop = asyncio.get_running_loop()
    state = await loop.run_in_executor(None, generate_world, params)
    _worlds[state.world_id] = state
    return {"world_id": state.world_id, "generated": True}


@router.get("/world/{world_id}")
async def get_world(world_id: str):
    state = _worlds.get(world_id)
    if not state:
        raise HTTPException(404, "World not found")
    return _state_dict(state)


@router.post("/world/{world_id}/advance")
async def advance_era_endpoint(world_id: str):
    state = _worlds.get(world_id)
    if not state:
        raise HTTPException(404, "World not found")
    loop = asyncio.get_running_loop()
    state = await loop.run_in_executor(None, advance_world_era, state)
    _worlds[world_id] = state
    return {"era": state.current_era, "events": [asdict(e) for e in state.history[-10:]]}


@router.post("/world/{world_id}/edit")
async def edit_world(world_id: str, req: EditRequest):
    state = _worlds.get(world_id)
    if not state:
        raise HTTPException(404, "World not found")

    H, W = state.params.height, state.params.width
    heightmap = np.array(state.heightmap, dtype=np.float32).reshape(H, W)

    if req.tool in ("raise", "lower"):
        sign = 1.0 if req.tool == "raise" else -1.0
        ys, xs = np.ogrid[0:H, 0:W]
        mask = ((xs - req.x)**2 + (ys - req.y)**2) <= req.radius**2
        heightmap[mask] = np.clip(
            heightmap[mask] + sign * req.strength, 0, 1
        )
        state.heightmap = heightmap.ravel().tolist()

    elif req.tool == "smooth":
        from scipy.ndimage import gaussian_filter
        ys, xs = np.ogrid[0:H, 0:W]
        mask = ((xs - req.x)**2 + (ys - req.y)**2) <= req.radius**2
        blurred = gaussian_filter(heightmap, sigma=req.radius / 3)
        heightmap[mask] = blurred[mask]
        state.heightmap = heightmap.ravel().tolist()

    elif req.tool == "place_city":
        from world.toponymy import ToponymyEngine
        topo = ToponymyEngine(state.params.seed)
        kid = req.extra.get("kingdom_id", 1)
        name = topo.city_name(kid)
        state.cities.append(CityNode(x=req.x, y=req.y, name=name, kingdom_id=kid))

    elif req.tool == "place_road":
        # Draw road from (x,y) to extra target
        tx, ty = req.extra.get("tx", req.x), req.extra.get("ty", req.y)
        cost_map = _build_cost_map(heightmap)
        from world.pathfinding import RoadEdge
        path = astar(cost_map, (req.y, req.x), (ty, tx))
        if path:
            xy_path = [(c, r) for r, c in path]
            state.roads.append(RoadEdge(x0=req.x, y0=req.y, x1=tx, y1=ty, path=xy_path))

    _worlds[world_id] = state
    return {"ok": True}


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

@router.get("/world/{world_id}/export/png")
async def export_png(world_id: str, style: str = "topo"):
    state = _worlds.get(world_id)
    if not state:
        raise HTTPException(404, "World not found")
    loop = asyncio.get_running_loop()
    img_bytes = await loop.run_in_executor(None, _render_png, state, style)
    return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png",
                             headers={"Content-Disposition": "attachment; filename=map.png"})


@router.get("/world/{world_id}/export/svg")
async def export_svg(world_id: str):
    state = _worlds.get(world_id)
    if not state:
        raise HTTPException(404, "World not found")
    loop = asyncio.get_running_loop()
    svg_str = await loop.run_in_executor(None, _render_svg, state)
    return StreamingResponse(io.StringIO(svg_str), media_type="image/svg+xml",
                             headers={"Content-Disposition": "attachment; filename=map.svg"})


# ---------------------------------------------------------------------------
# WebSocket — real-time progress (skeleton; extended by generator callbacks)
# ---------------------------------------------------------------------------

_ws_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/{world_id}")
async def websocket_endpoint(websocket: WebSocket, world_id: str):
    await websocket.accept()
    _ws_connections.setdefault(world_id, []).append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/keep-alive
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _ws_connections[world_id].remove(websocket)


# ---------------------------------------------------------------------------
# PNG / SVG renderers (server-side fallback)
# ---------------------------------------------------------------------------

BIOME_COLORS = {
    0:  (30,  80, 150),   # Ocean
    1:  (220, 240, 255),  # Ice
    2:  (180, 200, 190),  # Tundra
    3:  (40,  100, 60),   # Boreal
    4:  (60,  130, 50),   # Temperate Forest
    5:  (30,  90,  40),   # Temp Rainforest
    6:  (180, 160, 90),   # Shrubland
    7:  (200, 180, 80),   # Savanna
    8:  (100, 160, 60),   # Subtropical
    9:  (30,  120, 50),   # Tropical Forest
    10: (10,  90,  30),   # Tropical Rainforest
    11: (220, 200, 140),  # Desert
    12: (60,  140, 100),  # Wetland
    13: (240, 245, 255),  # Snow
    14: (230, 215, 170),  # Beach
}


def _render_png(state: WorldState, style: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    H, W = state.params.height, state.params.width

    img = Image.new("RGB", (W, H))
    pixels = img.load()

    heightmap = np.array(state.heightmap, dtype=np.float32).reshape(H, W)
    biome_map = np.array(state.biome_map, dtype=np.int32).reshape(H, W)
    influence = np.array(state.influence_map, dtype=np.int32).reshape(H, W)

    for y in range(H):
        for x in range(W):
            b = biome_map[y, x]
            col = list(BIOME_COLORS.get(b, (128, 128, 128)))

            if style == "parchment":
                # Sepia tone
                r, g, bv = col
                grey = int(0.299*r + 0.587*g + 0.114*bv)
                col = [
                    min(255, int(grey * 1.1 + 30)),
                    min(255, int(grey * 0.95 + 15)),
                    min(255, int(grey * 0.75)),
                ]
            elif style == "jrpg":
                # Posterise to 4 levels
                col = [min(255, (c // 64) * 64 + 32) for c in col]

            # Kingdom border tint
            kid = influence[y, x]
            if kid > 0:
                k = next((k for k in state.kingdoms if k.kingdom_id == kid), None)
                if k:
                    col = [
                        int(col[0] * 0.7 + k.color[0] * 0.3),
                        int(col[1] * 0.7 + k.color[1] * 0.3),
                        int(col[2] * 0.7 + k.color[2] * 0.3),
                    ]

            pixels[x, y] = tuple(col)

    draw = ImageDraw.Draw(img)

    # Draw roads
    for road in state.roads:
        for i in range(len(road.path) - 1):
            x0, y0 = road.path[i]
            x1, y1 = road.path[i+1]
            draw.line([(x0, y0), (x1, y1)], fill=(100, 70, 30), width=1)

    # Draw cities
    for city in state.cities:
        color = (255, 50, 50) if city.is_ruin else (255, 255, 50) if city.is_capital else (255, 200, 50)
        draw.ellipse([(city.x-3, city.y-3), (city.x+3, city.y+3)], fill=color)

    # Scale bar
    draw.line([(10, H-20), (60, H-20)], fill=(0,0,0), width=2)
    draw.text((10, H-35), "50 km", fill=(0,0,0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render_svg(state: WorldState) -> str:
    import svgwrite
    H, W = state.params.height, state.params.width
    dwg = svgwrite.Drawing(size=(W, H))

    influence = np.array(state.influence_map, dtype=np.int32).reshape(H, W)
    biome_map = np.array(state.biome_map, dtype=np.int32).reshape(H, W)

    # Draw biome rects (1×1 pixels as rects — efficient via groups)
    # Simplified: use 4×4 blocks for SVG file size
    block = 4
    for y in range(0, H, block):
        for x in range(0, W, block):
            b = biome_map[y, x]
            c = BIOME_COLORS.get(b, (128, 128, 128))
            kid = influence[y, x]
            if kid > 0:
                k = next((k for k in state.kingdoms if k.kingdom_id == kid), None)
                if k:
                    c = (
                        int(c[0]*0.7 + k.color[0]*0.3),
                        int(c[1]*0.7 + k.color[1]*0.3),
                        int(c[2]*0.7 + k.color[2]*0.3),
                    )
            fill = f"rgb({c[0]},{c[1]},{c[2]})"
            dwg.add(dwg.rect(insert=(x, y), size=(block, block), fill=fill))

    # Roads
    for road in state.roads:
        pts = [(p[0], p[1]) for p in road.path]
        if len(pts) > 1:
            dwg.add(dwg.polyline(pts, stroke="rgb(100,70,30)", fill="none", stroke_width=1))

    # Cities
    for city in state.cities:
        color = "red" if city.is_ruin else "gold" if city.is_capital else "orange"
        dwg.add(dwg.circle(center=(city.x, city.y), r=3, fill=color))
        dwg.add(dwg.text(city.name, insert=(city.x+4, city.y+4),
                         font_size="6px", fill="black"))

    # Legend
    legend_y = 10
    dwg.add(dwg.text("Map Legend", insert=(W-100, legend_y), font_size="10px", fill="black"))
    for i, (name, color) in enumerate(list(BIOME_COLORS.items())[:8]):
        c = BIOME_COLORS[color] if isinstance(color, int) else color
        # Only show first 8 biomes in legend
        biome_name = state.biome_names[i] if i < len(state.biome_names) else str(i)
        c = BIOME_COLORS.get(i, (128,128,128))
        fill = f"rgb({c[0]},{c[1]},{c[2]})"
        dwg.add(dwg.rect(insert=(W-100, legend_y + 15 + i*12), size=(10, 10), fill=fill))
        dwg.add(dwg.text(biome_name, insert=(W-86, legend_y + 24 + i*12),
                         font_size="8px", fill="black"))

    return dwg.tostring()
