/**
 * WorldStore — Zustand global state for the Fantasy Map Engine.
 * Mirrors the backend WorldState structure and manages API calls.
 */
import { create } from 'zustand'
import axios from 'axios'

const API = '/api'

const defaultParams = {
  seed: 42,
  width: 128,
  height: 128,
  num_plates: 8,
  tectonic_speed: 1.0,
  rainfall: 1.0,
  mana_level: 0.5,
  mana_threshold: 0.75,
  season: 0.0,
  erosion_iterations: 10000,
}

export const useWorldStore = create((set, get) => ({
  // Generation state
  generating: false,
  loadingMessage: '',
  error: null,

  // Parameters
  params: { ...defaultParams },

  // World data
  worldId: null,
  world: null,

  // UI state
  activeLayer: 'biome',   // biome | height | mana | climate | cave | kingdoms
  visualStyle: 'topo',    // topo | parchment | jrpg
  activeTool: 'none',     // none | raise | lower | smooth | place_city | place_road
  toolRadius: 8,
  toolStrength: 0.05,
  roadStart: null,        // {x, y} for road-drawing first click
  selectedCity: null,
  hoveredCell: null,
  showRoads: true,
  showCities: true,
  showBorders: true,
  showRivers: true,
  showResources: true,

  // WebSocket
  ws: null,

  // Actions
  setParam: (key, value) => set(s => ({ params: { ...s.params, [key]: value } })),

  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setVisualStyle: (style) => set({ visualStyle: style }),
  setActiveTool: (tool) => set({ activeTool: tool, roadStart: null }),
  setToolRadius: (r) => set({ toolRadius: r }),
  setToolStrength: (v) => set({ toolStrength: v }),
  setHoveredCell: (cell) => set({ hoveredCell: cell }),
  setSelectedCity: (city) => set({ selectedCity: city }),
  toggleLayer: (key) => set(s => ({ [key]: !s[key] })),

  generate: async () => {
    const { params } = get()
    set({ generating: true, loadingMessage: 'Generating world…', error: null })
    try {
      const { data } = await axios.post(`${API}/generate`, params)
      const worldId = data.world_id
      set({ loadingMessage: 'Loading world data…' })
      const { data: world } = await axios.get(`${API}/world/${worldId}`)
      set({ worldId, world, generating: false, loadingMessage: '' })
    } catch (e) {
      set({ error: e.message, generating: false, loadingMessage: '' })
    }
  },

  advanceEra: async () => {
    const { worldId } = get()
    if (!worldId) return
    try {
      await axios.post(`${API}/world/${worldId}/advance`)
      const { data: world } = await axios.get(`${API}/world/${worldId}`)
      set({ world })
    } catch (e) {
      set({ error: e.message })
    }
  },

  applyEdit: async (tool, x, y, extra = {}) => {
    const { worldId, toolRadius, toolStrength } = get()
    if (!worldId) return
    try {
      await axios.post(`${API}/world/${worldId}/edit`, {
        tool, x, y,
        radius: toolRadius,
        strength: toolStrength,
        extra,
      })
      const { data: world } = await axios.get(`${API}/world/${worldId}`)
      set({ world })
    } catch (e) {
      set({ error: e.message })
    }
  },

  exportPng: async (style = 'topo') => {
    const { worldId } = get()
    if (!worldId) return
    const url = `${API}/world/${worldId}/export/png?style=${style}`
    window.open(url, '_blank')
  },

  exportSvg: async () => {
    const { worldId } = get()
    if (!worldId) return
    window.open(`${API}/world/${worldId}/export/svg`, '_blank')
  },

  connectWs: (worldId) => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws/${worldId}`)
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'update') {
        set(s => ({ world: { ...s.world, ...msg.data } }))
      }
    }
    set({ ws })
  },
}))
