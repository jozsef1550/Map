/**
 * ExportPanel — floating bottom-right panel for export and settings.
 */
import { useWorldStore } from '../store/worldStore'

export default function ExportPanel() {
  const world       = useWorldStore(s => s.world)
  const exportPng   = useWorldStore(s => s.exportPng)
  const exportSvg   = useWorldStore(s => s.exportSvg)
  const visualStyle = useWorldStore(s => s.visualStyle)

  if (!world) return null

  const worldId = world?.world_id

  return (
    <div className="absolute bottom-4 right-4 z-10 bg-gray-900/90 border border-gray-700 rounded-lg p-3 shadow-lg flex flex-col gap-2 min-w-40">
      <h3 className="text-xs font-semibold text-gray-400 uppercase">Export</h3>

      <button
        onClick={() => exportPng(visualStyle)}
        className="btn-secondary text-xs"
        title="Export high-res PNG with legend and scale bar"
      >
        📷 Export PNG
      </button>

      <button
        onClick={exportSvg}
        className="btn-secondary text-xs"
        title="Export as scalable SVG vector map"
      >
        📐 Export SVG
      </button>

      <div className="border-t border-gray-700 pt-2 text-xs text-gray-500 space-y-0.5">
        <div>ID: <span className="text-gray-400 font-mono text-[10px]">{worldId?.slice(0, 8)}…</span></div>
        <div>Era: <span className="text-amber-400">{world.current_era}</span></div>
        <div>Cities: <span className="text-amber-400">{world.cities?.length ?? 0}</span></div>
        <div>Resources: <span className="text-amber-400">{world.resources?.length ?? 0}</span></div>
        <div>Kingdoms: <span className="text-amber-400">{world.kingdoms?.length ?? 0}</span></div>
      </div>
    </div>
  )
}
