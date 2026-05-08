/**
 * BrushTools — floating toolbar for terrain editing tools.
 */
import { useWorldStore } from '../store/worldStore'

const TOOLS = [
  { id: 'none',        label: '🖱️',  title: 'Select / Pan' },
  { id: 'raise',       label: '⬆️',  title: 'Raise Terrain' },
  { id: 'lower',       label: '⬇️',  title: 'Lower Terrain' },
  { id: 'smooth',      label: '〰️', title: 'Smooth Terrain' },
  { id: 'place_city',  label: '🏙️', title: 'Place City' },
  { id: 'place_road',  label: '🛣️', title: 'Draw Road (click 2 points)' },
]

export default function BrushTools() {
  const activeTool    = useWorldStore(s => s.activeTool)
  const setActiveTool = useWorldStore(s => s.setActiveTool)
  const toolRadius    = useWorldStore(s => s.toolRadius)
  const toolStrength  = useWorldStore(s => s.toolStrength)
  const setRadius     = useWorldStore(s => s.setToolRadius)
  const setStrength   = useWorldStore(s => s.setToolStrength)
  const world         = useWorldStore(s => s.world)
  const roadStart     = useWorldStore(s => s.roadStart)

  if (!world) return null

  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 bg-gray-900/90 border border-gray-700 rounded-full px-4 py-2 shadow-lg">
      {/* Tool buttons */}
      {TOOLS.map(tool => (
        <button
          key={tool.id}
          title={tool.title}
          onClick={() => setActiveTool(tool.id)}
          className={`text-xl px-2 py-1 rounded-full transition-all ${
            activeTool === tool.id
              ? 'bg-amber-600 shadow-md scale-110'
              : 'hover:bg-gray-700'
          }`}
        >
          {tool.label}
        </button>
      ))}

      {/* Brush controls */}
      {['raise', 'lower', 'smooth'].includes(activeTool) && (
        <div className="flex items-center gap-3 ml-2 border-l border-gray-600 pl-3">
          <label className="text-xs text-gray-400">
            Size
            <input
              type="range" min={2} max={30} step={1}
              value={toolRadius}
              onChange={e => setRadius(parseInt(e.target.value))}
              className="ml-1 w-16 accent-amber-500"
            />
            <span className="ml-1 text-amber-400">{toolRadius}</span>
          </label>
          <label className="text-xs text-gray-400">
            Strength
            <input
              type="range" min={0.01} max={0.3} step={0.01}
              value={toolStrength}
              onChange={e => setStrength(parseFloat(e.target.value))}
              className="ml-1 w-16 accent-amber-500"
            />
            <span className="ml-1 text-amber-400">{toolStrength.toFixed(2)}</span>
          </label>
        </div>
      )}

      {/* Road placement hint */}
      {activeTool === 'place_road' && (
        <span className="text-xs text-amber-400 ml-2 border-l border-gray-600 pl-3">
          {roadStart ? '🖱️ Click destination' : '🖱️ Click start point'}
        </span>
      )}
    </div>
  )
}
