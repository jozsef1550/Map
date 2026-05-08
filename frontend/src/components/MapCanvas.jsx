/**
 * MapCanvas
 * =========
 * Houses two overlapping canvases:
 *   1. canvas3d  — Three.js WebGL renderer (terrain + shaders)
 *   2. canvas2d  — 2D overlay (roads, cities, borders, legend)
 *
 * Handles mouse events for brush editing and city placement.
 */
import { useEffect, useRef, useCallback } from 'react'
import { useWorldStore } from '../store/worldStore'
import { RenderEngine } from '../engine/RenderEngine'

export default function MapCanvas() {
  const canvas3d = useRef(null)
  const canvas2d = useRef(null)
  const engineRef = useRef(null)
  const containerRef = useRef(null)

  const world        = useWorldStore(s => s.world)
  const activeLayer  = useWorldStore(s => s.activeLayer)
  const visualStyle  = useWorldStore(s => s.visualStyle)
  const activeTool   = useWorldStore(s => s.activeTool)
  const roadStart    = useWorldStore(s => s.roadStart)
  const showRoads    = useWorldStore(s => s.showRoads)
  const showCities   = useWorldStore(s => s.showCities)
  const showBorders  = useWorldStore(s => s.showBorders)
  const showRivers   = useWorldStore(s => s.showRivers)
  const showResources = useWorldStore(s => s.showResources)
  const applyEdit    = useWorldStore(s => s.applyEdit)
  const setRoadStart = useWorldStore(s => s.setActiveTool)
  const setHovered   = useWorldStore(s => s.setHoveredCell)

  // Init engine
  useEffect(() => {
    const engine = new RenderEngine(canvas3d.current, canvas2d.current)
    engineRef.current = engine

    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      engine.resize(width, height)
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      engine.dispose()
    }
  }, [])

  // World data changes
  useEffect(() => {
    if (engineRef.current && world) {
      engineRef.current.loadWorld(world)
    }
  }, [world])

  // Layer / style / overlay changes
  useEffect(() => { engineRef.current?.setActiveLayer(activeLayer) }, [activeLayer])
  useEffect(() => { engineRef.current?.setStyle(visualStyle)       }, [visualStyle])
  useEffect(() => {
    engineRef.current?.setOverlay('roads',     showRoads)
    engineRef.current?.setOverlay('cities',    showCities)
    engineRef.current?.setOverlay('borders',   showBorders)
    engineRef.current?.setOverlay('rivers',    showRivers)
    engineRef.current?.setOverlay('resources', showResources)
    engineRef.current?.renderOverlay()
  }, [showRoads, showCities, showBorders, showRivers, showResources])

  const canvasToWorld = useCallback((e) => {
    if (!world) return null
    const rect = canvas2d.current.getBoundingClientRect()
    const cw = rect.width
    const ch = rect.height
    const cx = e.clientX - rect.left
    const cy = e.clientY - rect.top
    const { width: W, height: H } = world.params
    return {
      x: Math.round((cx / cw) * W),
      y: Math.round((cy / ch) * H),
    }
  }, [world])

  const handleMouseMove = useCallback((e) => {
    const pos = canvasToWorld(e)
    if (pos) setHovered(pos)
  }, [canvasToWorld, setHovered])

  const handleClick = useCallback(async (e) => {
    const pos = canvasToWorld(e)
    if (!pos || !world) return

    if (activeTool === 'raise' || activeTool === 'lower' || activeTool === 'smooth') {
      await applyEdit(activeTool, pos.x, pos.y)
    } else if (activeTool === 'place_city') {
      await applyEdit('place_city', pos.x, pos.y)
    } else if (activeTool === 'place_road') {
      const rs = useWorldStore.getState().roadStart
      if (!rs) {
        useWorldStore.setState({ roadStart: pos })
      } else {
        await applyEdit('place_road', rs.x, rs.y, { tx: pos.x, ty: pos.y })
        useWorldStore.setState({ roadStart: null })
      }
    }
  }, [activeTool, applyEdit, canvasToWorld, world])

  const handleMouseDown = useCallback((e) => {
    if (['raise', 'lower', 'smooth'].includes(activeTool)) {
      handleClick(e)
    }
  }, [activeTool, handleClick])

  const getCursor = () => {
    switch (activeTool) {
      case 'raise':
      case 'lower':
      case 'smooth':
        return 'crosshair'
      case 'place_city':
      case 'place_road':
        return 'cell'
      default:
        return 'default'
    }
  }

  return (
    <div ref={containerRef} className="relative w-full h-full bg-black">
      {/* WebGL layer */}
      <canvas
        ref={canvas3d}
        className="absolute inset-0 w-full h-full"
        style={{ display: 'block' }}
      />
      {/* 2D overlay layer */}
      <canvas
        ref={canvas2d}
        className="absolute inset-0 w-full h-full"
        style={{ display: 'block', cursor: getCursor() }}
        onMouseMove={handleMouseMove}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
      />
    </div>
  )
}
