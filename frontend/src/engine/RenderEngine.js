/**
 * RenderEngine
 * ============
 * Manages a Three.js scene for the Fantasy Map.
 *
 * Architecture:
 *  • An OrthographicCamera views a flat plane (the map).
 *  • The map plane uses a ShaderMaterial that composites:
 *      - biome colour texture
 *      - heightmap texture (for hillshade / contours)
 *      - mana overlay texture
 *  • A second overlay Canvas2D (drawn on top) handles:
 *      - Roads, city dots, kingdom borders, resource icons
 *      - This avoids complexity of mixing Three.js geometry for
 *        every feature while keeping WebGL for the terrain style.
 *  • Visual style is switched by swapping the fragment shader.
 */

import * as THREE from 'three'
import { parchmentVertexShader, parchmentFragmentShader } from '../shaders/parchmentShader'
import { jrpgVertexShader, jrpgFragmentShader } from '../shaders/jrpgShader'
import { topoVertexShader, topoFragmentShader } from '../shaders/topoShader'

// Biome colour palette (index → RGB 0-255)
export const BIOME_COLORS = [
  [30,  80,  150],  // 0  Ocean
  [220, 240, 255],  // 1  Ice / Polar
  [180, 200, 190],  // 2  Tundra
  [40,  100,  60],  // 3  Boreal Forest
  [60,  130,  50],  // 4  Temperate Forest
  [30,   90,  40],  // 5  Temperate Rainforest
  [180, 160,  90],  // 6  Shrubland
  [200, 180,  80],  // 7  Woodland / Savanna
  [100, 160,  60],  // 8  Subtropical Forest
  [30,  120,  50],  // 9  Tropical Forest
  [10,   90,  30],  // 10 Tropical Rainforest
  [220, 200, 140],  // 11 Desert
  [60,  140, 100],  // 12 Wetland / Delta
  [240, 245, 255],  // 13 Snow / Glacier
  [230, 215, 170],  // 14 Beach
]

const RESOURCE_ICONS = {
  iron:         '⚙',
  gold:         '✦',
  fertile:      '🌾',
  mana_crystal: '✦',
  timber:       '🌲',
  fish:         '🐟',
}

const RESOURCE_COLORS = {
  iron:         '#aaa',
  gold:         '#ffd700',
  fertile:      '#90ee40',
  mana_crystal: '#cc88ff',
  timber:       '#228b22',
  fish:         '#1e90ff',
}

export class RenderEngine {
  constructor(canvas3d, canvas2d) {
    this.canvas3d = canvas3d
    this.canvas2d = canvas2d
    this.world = null
    this.style = 'topo'
    this.activeLayer = 'biome'
    this.zoom = 1.0
    this.panX = 0
    this.panY = 0
    this.overlayFlags = {
      roads: true, cities: true, borders: true,
      rivers: true, resources: true,
    }

    this._initThree()
    this._animate()
  }

  _initThree() {
    const W = this.canvas3d.clientWidth || 800
    const H = this.canvas3d.clientHeight || 600

    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas3d, antialias: false })
    this.renderer.setSize(W, H, false)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    this.scene = new THREE.Scene()
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10)
    this.camera.position.z = 1

    // Placeholder grey texture until world data loads
    this.biomeTexture = new THREE.DataTexture(
      new Uint8Array([80, 80, 80, 255]), 1, 1, THREE.RGBAFormat
    )
    this.heightTexture = new THREE.DataTexture(
      new Uint8Array([128, 128, 128, 255]), 1, 1, THREE.RGBAFormat
    )
    this.biomeTexture.needsUpdate = true
    this.heightTexture.needsUpdate = true

    this._buildMaterial()

    const geo = new THREE.PlaneGeometry(2, 2)
    this.mapMesh = new THREE.Mesh(geo, this.material)
    this.scene.add(this.mapMesh)
  }

  _buildMaterial() {
    let vShader, fShader
    switch (this.style) {
      case 'parchment':
        vShader = parchmentVertexShader
        fShader = parchmentFragmentShader
        break
      case 'jrpg':
        vShader = jrpgVertexShader
        fShader = jrpgFragmentShader
        break
      default: // topo
        vShader = topoVertexShader
        fShader = topoFragmentShader
    }

    if (this.material) this.material.dispose()

    this.material = new THREE.ShaderMaterial({
      uniforms: {
        tMap:             { value: this.biomeTexture },
        tHeight:          { value: this.heightTexture },
        uContourInterval: { value: 0.05 },
        uHillshade:       { value: 0.6 },
        uSatellite:       { value: false },
        uResolution:      { value: new THREE.Vector2(800, 600) },
        uTime:            { value: 0 },
      },
      vertexShader: vShader,
      fragmentShader: fShader,
      transparent: false,
    })

    if (this.mapMesh) this.mapMesh.material = this.material
  }

  setStyle(style) {
    this.style = style
    this._buildMaterial()
    this.renderOverlay()
  }

  setActiveLayer(layer) {
    this.activeLayer = layer
    if (this.world) this._uploadTextures(this.world)
    this.renderOverlay()
  }

  setOverlay(key, value) {
    this.overlayFlags[key] = value
    this.renderOverlay()
  }

  loadWorld(world) {
    this.world = world
    this._uploadTextures(world)
    this.renderOverlay()
  }

  _uploadTextures(world) {
    const { width: W, height: H } = world.params
    const biomeData   = new Uint8Array(W * H * 4)
    const heightData  = new Uint8Array(W * H * 4)

    const heightmap    = world.heightmap
    const biome_map    = world.biome_map
    const mana_map     = world.mana_map
    const temperature  = world.temperature
    const precipitation = world.precipitation
    const influence    = world.influence_map

    for (let i = 0; i < W * H; i++) {
      let r, g, b
      const layer = this.activeLayer
      if (layer === 'height') {
        const v = Math.round(heightmap[i] * 255)
        r = g = b = v
      } else if (layer === 'mana') {
        const v = mana_map[i]
        r = Math.round(v * 200)
        g = Math.round(v * 80)
        b = Math.round(255 - v * 100)
      } else if (layer === 'climate') {
        // Temperature hue: cold=blue, hot=red
        const t = Math.max(0, Math.min(1, (temperature[i] + 40) / 75))
        r = Math.round(t * 220)
        g = Math.round((1 - Math.abs(t - 0.5) * 2) * 180)
        b = Math.round((1 - t) * 220)
      } else if (layer === 'cave') {
        const caveIdx = i % (world.cave_map.length / world.cave_depth | 0)
        const open = world.cave_map[caveIdx * world.cave_depth]
        r = open ? 180 : 40
        g = open ? 100 : 40
        b = open ? 220 : 40
      } else if (layer === 'kingdoms') {
        const kid = influence[i]
        if (kid > 0) {
          const k = world.kingdoms.find(k => k.kingdom_id === kid)
          if (k) { r = k.color[0]; g = k.color[1]; b = k.color[2] }
          else { r = g = b = 80 }
        } else { r = 30; g = 60; b = 100 }
      } else {
        // Biome layer (default)
        const bio = biome_map[i] ?? 0
        const col = BIOME_COLORS[bio] ?? [128, 128, 128]
        r = col[0]; g = col[1]; b = col[2]

        // Tint by kingdom
        if (this.overlayFlags.borders) {
          const kid = influence[i]
          if (kid > 0) {
            const k = world.kingdoms.find(k => k.kingdom_id === kid)
            if (k) {
              r = Math.round(r * 0.75 + k.color[0] * 0.25)
              g = Math.round(g * 0.75 + k.color[1] * 0.25)
              b = Math.round(b * 0.75 + k.color[2] * 0.25)
            }
          }
        }
      }

      biomeData[i * 4]     = r
      biomeData[i * 4 + 1] = g
      biomeData[i * 4 + 2] = b
      biomeData[i * 4 + 3] = 255

      const hv = Math.round(heightmap[i] * 255)
      heightData[i * 4]     = hv
      heightData[i * 4 + 1] = hv
      heightData[i * 4 + 2] = hv
      heightData[i * 4 + 3] = 255
    }

    this.biomeTexture  = new THREE.DataTexture(biomeData,  W, H, THREE.RGBAFormat)
    this.heightTexture = new THREE.DataTexture(heightData, W, H, THREE.RGBAFormat)
    this.biomeTexture.needsUpdate  = true
    this.heightTexture.needsUpdate = true

    this.material.uniforms.tMap.value    = this.biomeTexture
    this.material.uniforms.tHeight.value = this.heightTexture
    this.material.uniforms.uResolution.value.set(W, H)
  }

  renderOverlay() {
    const ctx = this.canvas2d.getContext('2d')
    const W2 = this.canvas2d.width
    const H2 = this.canvas2d.height
    ctx.clearRect(0, 0, W2, H2)

    if (!this.world) return

    const { width: MW, height: MH } = this.world.params
    const scaleX = W2 / MW
    const scaleY = H2 / MH

    const tx = (mx) => mx * scaleX
    const ty = (my) => my * scaleY

    // ── Rivers ──────────────────────────────────────────────────────────────
    if (this.overlayFlags.rivers) {
      const river = this.world.river_map
      ctx.strokeStyle = 'rgba(60,140,220,0.55)'
      for (let i = 0; i < MW * MH; i++) {
        if (river[i] > 0.1) {
          const x = i % MW
          const y = (i / MW) | 0
          ctx.fillStyle = `rgba(60,140,220,${Math.min(1, river[i] * 2)})`
          ctx.fillRect(tx(x), ty(y), Math.max(1, scaleX), Math.max(1, scaleY))
        }
      }
    }

    // ── Roads ───────────────────────────────────────────────────────────────
    if (this.overlayFlags.roads && this.world.roads) {
      ctx.strokeStyle = 'rgba(150,110,50,0.85)'
      ctx.lineWidth = Math.max(1, scaleX * 1.5)
      for (const road of this.world.roads) {
        if (!road.path || road.path.length < 2) continue
        ctx.beginPath()
        ctx.moveTo(tx(road.path[0][0]), ty(road.path[0][1]))
        for (let k = 1; k < road.path.length; k++) {
          ctx.lineTo(tx(road.path[k][0]), ty(road.path[k][1]))
        }
        ctx.stroke()
      }
    }

    // ── Resources ───────────────────────────────────────────────────────────
    if (this.overlayFlags.resources && this.world.resources) {
      for (const res of this.world.resources) {
        const px = tx(res.x)
        const py = ty(res.y)
        const color = RESOURCE_COLORS[res.resource_type] || '#fff'
        ctx.beginPath()
        ctx.arc(px, py, Math.max(3, scaleX * 3), 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()
        ctx.strokeStyle = '#000'
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }

    // ── Cities ──────────────────────────────────────────────────────────────
    if (this.overlayFlags.cities && this.world.cities) {
      for (const city of this.world.cities) {
        const px = tx(city.x)
        const py = ty(city.y)
        const r = city.is_capital ? 6 : 4
        ctx.beginPath()
        ctx.arc(px, py, r * Math.max(scaleX, 0.5), 0, Math.PI * 2)
        if (city.is_ruin) {
          ctx.fillStyle = 'rgba(150,80,80,0.9)'
        } else if (city.is_capital) {
          ctx.fillStyle = 'rgba(255,215,0,0.95)'
        } else {
          ctx.fillStyle = 'rgba(255,200,80,0.9)'
        }
        ctx.fill()
        ctx.strokeStyle = '#222'
        ctx.lineWidth = 0.8
        ctx.stroke()

        // City label (only when zoomed in)
        if (scaleX > 1.5) {
          ctx.font = `${Math.round(6 + scaleX * 2)}px sans-serif`
          ctx.fillStyle = '#fff'
          ctx.strokeStyle = '#000'
          ctx.lineWidth = 2
          ctx.strokeText(city.name, px + 5, py - 3)
          ctx.fillText(city.name, px + 5, py - 3)
        }
      }
    }

    // ── Legend ──────────────────────────────────────────────────────────────
    this._drawLegend(ctx, W2, H2)
  }

  _drawLegend(ctx, W, H) {
    const biomeNames = this.world?.biome_names ?? []
    const x0 = W - 160, y0 = 10
    ctx.fillStyle = 'rgba(0,0,0,0.6)'
    ctx.roundRect(x0 - 5, y0 - 5, 155, biomeNames.length * 16 + 30, 6)
    ctx.fill()

    ctx.font = 'bold 11px sans-serif'
    ctx.fillStyle = '#eee'
    ctx.fillText('Legend', x0, y0 + 10)

    biomeNames.forEach((name, i) => {
      const col = BIOME_COLORS[i] ?? [128, 128, 128]
      ctx.fillStyle = `rgb(${col[0]},${col[1]},${col[2]})`
      ctx.fillRect(x0, y0 + 22 + i * 16, 12, 12)
      ctx.fillStyle = '#ddd'
      ctx.font = '9px sans-serif'
      ctx.fillText(name, x0 + 16, y0 + 32 + i * 16)
    })

    // Scale bar
    const sbX = 10, sbY = H - 30
    ctx.fillStyle = 'rgba(0,0,0,0.5)'
    ctx.fillRect(sbX - 4, sbY - 20, 90, 28)
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(sbX, sbY)
    ctx.lineTo(sbX + 80, sbY)
    ctx.stroke()
    ;[0, 40, 80].forEach(tick => {
      ctx.beginPath()
      ctx.moveTo(sbX + tick, sbY - 4)
      ctx.lineTo(sbX + tick, sbY + 4)
      ctx.stroke()
    })
    ctx.font = '10px sans-serif'
    ctx.fillStyle = '#fff'
    ctx.fillText('0', sbX - 2, sbY - 6)
    ctx.fillText('100 km', sbX + 44, sbY - 6)
  }

  resize(W, H) {
    this.renderer.setSize(W, H, false)
    this.canvas2d.width  = W
    this.canvas2d.height = H
    this.material.uniforms.uResolution?.value.set(W, H)
    this.renderOverlay()
  }

  _animate() {
    this._rafId = requestAnimationFrame(() => this._animate())
    this.material.uniforms.uTime && (this.material.uniforms.uTime.value += 0.01)
    this.renderer.render(this.scene, this.camera)
  }

  dispose() {
    cancelAnimationFrame(this._rafId)
    this.renderer.dispose()
  }
}
