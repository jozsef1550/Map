# ⚔️ Fantasy Map Engine & Editor

A full-stack procedural world generator and interactive map editor with a
layered simulation pipeline — from tectonic plates through climate, magic,
caves, economies, kingdoms, and history.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Three.js)                                 │
│  ┌──────────────┐  ┌────────────┐  ┌──────────┐            │
│  │  MapCanvas   │  │  Sidebar   │  │BrushTools│            │
│  │  (WebGL 3D + │  │ (params,   │  │(raise/   │            │
│  │   2D overlay)│  │  layers,   │  │lower/    │            │
│  └──────────────┘  │  timeline) │  │city/road)│            │
│  ┌─────────────────┴────────────┴──┴──────────┴──────────┐ │
│  │  RenderEngine  (Three.js ShaderMaterial)               │ │
│  │  Shaders: Parchment · 8-bit JRPG · Topographic        │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  WorldStore (Zustand)  ↔  FastAPI /api/*                ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI + NumPy + SciPy)                           │
│                                                              │
│  WorldState ─────────────────────────────────────────────── │
│  ├── Layer 0  Heightmap  (tectonic.py → erosion.py)         │
│  ├── Layer 1  Climate    (climate.py: Whittaker biomes)     │
│  ├── Layer 2  Mana       (mana.py: Simplex noise + warp)    │
│  ├── Layer -1 Caves      (caves.py: 3D Cellular Automata)   │
│  ├── Layer 3  Resources  (resources.py: geologic context)   │
│  ├── Layer 3  Roads      (pathfinding.py: A* + econ weight) │
│  ├── Layer 4  Kingdoms   (kingdoms.py: Influence Maps)      │
│  └── Layer 5  History    (history.py: Era simulation)       │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

### Phase 1 — Geophysical & Climate Foundation
| Feature | Implementation |
|---------|---------------|
| **Tectonic Layer** | Voronoi cells with motion vectors; mountains at convergent boundaries, rifts at divergent |
| **Climate Layer** | Whittaker Plot biome assignment; rain-shadow calculation; latitude + altitude temperature |
| **Season Slider** | Modifies snowline, precipitation, and river-freeze thresholds (0 = summer, 1 = winter) |
| **Hydraulic Erosion** | Particle-based erosion carves river paths; sediment deposits in deltas |

### Phase 2 — Magic & Subsurface
| Feature | Implementation |
|---------|---------------|
| **Mana Layer** | Fractal Simplex noise; cells above threshold trigger warped terrain (floating islands) |
| **Cave System (Layer −1)** | 3D Cellular Automata (26-neighbour); tunnels align with surface mountain ranges |

### Phase 3 — Economic & Political Simulation
| Feature | Implementation |
|---------|---------------|
| **Resource Nodes** | Iron (convergent plates), Gold (mountain summits), Fertile Soil (deltas), Mana Crystals, Timber, Fish |
| **A\* Road Pathfinding** | Cost = steepness + altitude; economic weight connects resources to ports |
| **Kingdoms** | Dijkstra flood-fill influence maps; Power = resources + cave access + territory area |

### Phase 4 — History & Naming
| Feature | Implementation |
|---------|---------------|
| **Timeline / Era System** | `Advance Era` simulates border friction, city growth, random destructions |
| **Ruin Nodes** | Destroyed cities become Ruins; renamed procedurally |
| **Toponymy Engine** | 6 linguistic seeds (Elvish, Dwarven, Eastern, Arabian, Latin, Slavic); prefixes + middles + suffixes |

### Phase 5 — Interactive Editor & Renderer
| Feature | Implementation |
|---------|---------------|
| **Sidebar Sliders** | Tectonic speed, rainfall, mana level, season, plates, erosion passes |
| **Brushes** | Raise / Lower / Smooth terrain; Place city; Draw road (2-point A*) |
| **Visual Styles** | GLSL shaders: `Parchment` (sepia + grain + vignette), `8-bit JRPG` (posterise + scanlines), `Topographic` (contours + hillshade + satellite) |
| **Layer Views** | Biome · Height · Mana · Climate · Cave · Kingdoms |
| **Overlay Toggles** | Roads · Cities · Borders · Rivers · Resources |
| **Export** | High-res PNG with legend + scale bar (server-side via Pillow); SVG vector export |
| **Cell Inspector** | Hover any cell to see biome, height, temperature, rainfall, mana |

---

## WorldState Object

```python
@dataclass
class WorldState:
    world_id: str          # UUID

    # Params
    params: WorldParams    # seed, width, height, num_plates, season, …

    # Layer 0 – Tectonic / Height
    heightmap:    list[float]   # [H×W]  0–1
    plate_map:    list[int]     # [H×W]  plate index
    plate_vectors: list[tuple]  # [num_plates]  (vx, vy)
    boundary_map: list[float]   # [H×W]  boundary stress

    # Layer 1 – Climate
    temperature:   list[float]  # [H×W]  °C
    precipitation: list[float]  # [H×W]  mm/yr
    biome_map:     list[int]    # [H×W]  Whittaker biome index
    river_map:     list[float]  # [H×W]  hydraulic flow accumulation

    # Layer 2 – Mana
    mana_map:  list[float]      # [H×W]  0–1
    warp_map:  list[float]      # [H×W]  terrain modification magnitude

    # Layer -1 – Caves
    cave_map:  list[int]        # [D×H×W]  0=rock / 1=open

    # Layer 3 – Resources & Economy
    resources: list[ResourceNode]
    roads:     list[RoadEdge]
    cities:    list[CityNode]

    # Layer 4 – Kingdoms
    kingdoms:      list[Kingdom]
    influence_map: list[int]    # [H×W]  kingdom_id (0 = unclaimed/ocean)

    # Layer 5 – History
    history:     list[HistoryEvent]
    current_era: int
```

## RenderEngine

The `RenderEngine` class (`frontend/src/engine/RenderEngine.js`) manages:

| Component | Description |
|-----------|-------------|
| `THREE.WebGLRenderer` | Hardware-accelerated terrain rendering |
| `THREE.ShaderMaterial` | Swappable GLSL shaders per visual style |
| `biomeTexture` | RGBA texture built from world biome/layer data |
| `heightTexture` | Greyscale heightmap for hillshade/contours |
| `Canvas2D overlay` | Roads, cities, resources, legend, scale bar |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

Or use the convenience scripts from the repo root:
```bash
./start-backend.sh   # terminal 1
./start-frontend.sh  # terminal 2
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate` | Generate a new world (params in body) |
| `GET`  | `/api/world/{id}` | Retrieve full WorldState as JSON |
| `POST` | `/api/world/{id}/advance` | Step timeline forward one era |
| `POST` | `/api/world/{id}/edit` | Apply a brush edit (raise/lower/smooth/city/road) |
| `GET`  | `/api/world/{id}/export/png?style=topo` | Export PNG map |
| `GET`  | `/api/world/{id}/export/svg` | Export SVG vector map |
| `WS`   | `/ws/{id}` | WebSocket for real-time updates |

### Generate Request Body
```json
{
  "seed": 42,
  "width": 256,
  "height": 256,
  "num_plates": 12,
  "tectonic_speed": 1.0,
  "rainfall": 1.0,
  "mana_level": 0.5,
  "mana_threshold": 0.75,
  "season": 0.0,
  "erosion_iterations": 60000
}
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend math | NumPy, SciPy |
| Backend API | FastAPI, Uvicorn |
| Image export | Pillow, svgwrite |
| Frontend framework | React 18, Vite 5 |
| 3D rendering | Three.js (WebGL) |
| GLSL shaders | Custom ShaderMaterial |
| State management | Zustand |
| HTTP client | Axios |
| Styling | Tailwind CSS |

---

## Biomes (Whittaker Plot)

| Index | Biome | Temp | Precip |
|-------|-------|------|--------|
| 0 | Ocean | — | — |
| 1 | Ice / Polar | < −5°C | any |
| 2 | Tundra | < 3°C | any |
| 3 | Boreal Forest | 3–8°C | > 250 mm |
| 4 | Temperate Forest | 8–15°C | 500–1500 mm |
| 5 | Temperate Rainforest | 8–15°C | > 1500 mm |
| 6 | Shrubland | 8–15°C | 250–500 mm |
| 7 | Woodland / Savanna | 15–20°C | 500–1000 mm |
| 8 | Subtropical Forest | 15–20°C | 1000–2000 mm |
| 9 | Tropical Forest | > 20°C | 1000–2000 mm |
| 10 | Tropical Rainforest | > 20°C | > 2000 mm |
| 11 | Desert | > 5°C | < 250 mm |
| 12 | Wetland / Delta | — | high flow |
| 13 | Snow / Glacier | high altitude | — |
| 14 | Beach | sea level | — |
