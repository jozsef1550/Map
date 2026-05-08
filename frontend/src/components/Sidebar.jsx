/**
 * Sidebar — parameter sliders, layer selectors, visual style picker.
 */
import { useWorldStore } from '../store/worldStore'

const LAYERS = [
  { id: 'biome',    label: '🌿 Biome' },
  { id: 'height',   label: '⛰️ Height' },
  { id: 'mana',     label: '✨ Mana' },
  { id: 'climate',  label: '🌡️ Climate' },
  { id: 'cave',     label: '🕳️ Cave (L-1)' },
  { id: 'kingdoms', label: '👑 Kingdoms' },
]

const STYLES = [
  { id: 'topo',      label: '🗺️ Topographic' },
  { id: 'parchment', label: '📜 Parchment' },
  { id: 'jrpg',      label: '🎮 8-bit JRPG' },
]

function Slider({ label, paramKey, min, max, step = 0.01, format }) {
  const value  = useWorldStore(s => s.params[paramKey])
  const setParam = useWorldStore(s => s.setParam)
  const display = format ? format(value) : value.toFixed(2)

  return (
    <div className="slider-row">
      <span className="text-xs text-gray-400 w-32 shrink-0">{label}</span>
      <input
        type="range" min={min} max={max} step={step}
        value={value}
        onChange={e => setParam(paramKey, parseFloat(e.target.value))}
        className="flex-1"
      />
      <span className="text-xs text-amber-400 w-10 text-right">{display}</span>
    </div>
  )
}

function Toggle({ label, storeKey }) {
  const value  = useWorldStore(s => s[storeKey])
  const toggle = useWorldStore(s => s.toggleLayer)
  return (
    <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer select-none">
      <input
        type="checkbox" checked={value}
        onChange={() => toggle(storeKey)}
        className="accent-amber-500"
      />
      {label}
    </label>
  )
}

export default function Sidebar() {
  const generate    = useWorldStore(s => s.generate)
  const generating  = useWorldStore(s => s.generating)
  const loadingMsg  = useWorldStore(s => s.loadingMessage)
  const error       = useWorldStore(s => s.error)
  const world       = useWorldStore(s => s.world)
  const activeLayer = useWorldStore(s => s.activeLayer)
  const visualStyle = useWorldStore(s => s.visualStyle)
  const setLayer    = useWorldStore(s => s.setActiveLayer)
  const setStyle    = useWorldStore(s => s.setVisualStyle)
  const advanceEra  = useWorldStore(s => s.advanceEra)
  const hoveredCell = useWorldStore(s => s.hoveredCell)
  const currentEra  = world?.current_era ?? 0

  const hoveredInfo = () => {
    if (!hoveredCell || !world) return null
    const { x, y } = hoveredCell
    const { width: W, height: H } = world.params
    if (x < 0 || x >= W || y < 0 || y >= H) return null
    const i = y * W + x
    const biomeNames = world.biome_names ?? []
    return {
      biome:  biomeNames[world.biome_map?.[i]] ?? '?',
      height: (world.heightmap?.[i] * 100 | 0) / 10,
      mana:   (world.mana_map?.[i] * 100 | 0) / 100,
      temp:   (world.temperature?.[i] | 0),
      rain:   (world.precipitation?.[i] | 0),
    }
  }
  const hInfo = hoveredInfo()

  return (
    <aside className="w-64 shrink-0 h-full overflow-y-auto bg-gray-950 border-r border-gray-800 flex flex-col gap-3 p-3">
      {/* Title */}
      <div className="text-center">
        <h1 className="text-lg font-bold text-amber-400">⚔️ Fantasy Map Engine</h1>
        <p className="text-xs text-gray-500">Full-Stack World Generator</p>
      </div>

      {/* ── Generate ─────────────────────────────── */}
      <div className="panel">
        <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">World Parameters</h2>
        <Slider label="Seed"           paramKey="seed"            min={0}     max={99999} step={1} format={v=>Math.round(v)} />
        <Slider label="World Size"     paramKey="width"           min={128}   max={512}   step={128} format={v=>`${v}²`} />
        <Slider label="Tectonic Plates" paramKey="num_plates"     min={4}     max={24}    step={1} format={v=>Math.round(v)} />
        <Slider label="Tectonic Speed" paramKey="tectonic_speed"  min={0.1}   max={3.0}   step={0.1} />
        <Slider label="Rainfall"       paramKey="rainfall"        min={0.1}   max={3.0}   step={0.1} />
        <Slider label="Mana Level"     paramKey="mana_level"      min={0.0}   max={1.0} />
        <Slider label="Mana Threshold" paramKey="mana_threshold"  min={0.3}   max={1.0} />
        <Slider label="Season"         paramKey="season"          min={0.0}   max={1.0}   step={0.05} format={v=>v<0.5?'Summer':'Winter'} />
        <Slider label="Erosion Passes" paramKey="erosion_iterations" min={5000} max={200000} step={5000} format={v=>`${(v/1000).toFixed(0)}k`} />

        <button
          onClick={generate}
          disabled={generating}
          className="btn-primary w-full mt-3"
        >
          {generating ? (loadingMsg || '⏳ Generating…') : '🌍 Generate World'}
        </button>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {/* ── Layers ───────────────────────────────── */}
      <div className="panel">
        <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Active Layer</h2>
        <div className="grid grid-cols-2 gap-1">
          {LAYERS.map(l => (
            <button
              key={l.id}
              onClick={() => setLayer(l.id)}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                activeLayer === l.id
                  ? 'bg-amber-700 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Visual Style ─────────────────────────── */}
      <div className="panel">
        <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Visual Style</h2>
        <div className="flex flex-col gap-1">
          {STYLES.map(s => (
            <button
              key={s.id}
              onClick={() => setStyle(s.id)}
              className={`text-xs px-2 py-1 rounded text-left transition-colors ${
                visualStyle === s.id
                  ? 'bg-amber-700 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Overlay Toggles ──────────────────────── */}
      <div className="panel">
        <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Overlays</h2>
        <div className="grid grid-cols-2 gap-1">
          <Toggle label="🛣️ Roads"     storeKey="showRoads" />
          <Toggle label="🏙️ Cities"   storeKey="showCities" />
          <Toggle label="👑 Borders"  storeKey="showBorders" />
          <Toggle label="🌊 Rivers"   storeKey="showRivers" />
          <Toggle label="💎 Resources" storeKey="showResources" />
        </div>
      </div>

      {/* ── Timeline ─────────────────────────────── */}
      {world && (
        <div className="panel">
          <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Timeline — Era {currentEra}</h2>
          <button onClick={advanceEra} className="btn-secondary w-full text-xs">
            ⏭️ Advance Era
          </button>
          {/* Recent history events */}
          <div className="mt-2 max-h-24 overflow-y-auto text-xs text-gray-400 space-y-1">
            {[...(world.history ?? [])].reverse().slice(0, 10).map((evt, i) => (
              <div key={i} className="border-l-2 border-amber-800 pl-2 py-0.5">
                <span className="text-amber-600">Era {evt.era}</span> {evt.description}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Kingdom Info ──────────────────────────── */}
      {world?.kingdoms?.length > 0 && (
        <div className="panel">
          <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2">Kingdoms</h2>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {world.kingdoms.map(k => (
              <div key={k.kingdom_id} className="flex items-center gap-2 text-xs">
                <span
                  className="w-3 h-3 rounded-sm shrink-0"
                  style={{ background: `rgb(${k.color[0]},${k.color[1]},${k.color[2]})` }}
                />
                <span className="text-gray-300 truncate flex-1">{k.name}</span>
                <span className="text-amber-400">⚡{k.power.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Hover Cell Info ───────────────────────── */}
      {hInfo && (
        <div className="panel text-xs text-gray-300 space-y-1">
          <h2 className="text-xs font-semibold text-gray-400 uppercase">Cell Info</h2>
          <div>🌿 {hInfo.biome}</div>
          <div>⛰️ Height: {hInfo.height}%</div>
          <div>🌡️ Temp: {hInfo.temp}°C</div>
          <div>🌧️ Rain: {hInfo.rain} mm/yr</div>
          <div>✨ Mana: {hInfo.mana}</div>
        </div>
      )}
    </aside>
  )
}
