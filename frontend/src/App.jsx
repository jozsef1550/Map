/**
 * App — root component.
 * Layout: sidebar (left) | map canvas (fill) with floating toolbars.
 */
import Sidebar     from './components/Sidebar'
import MapCanvas   from './components/MapCanvas'
import BrushTools  from './components/BrushTools'
import ExportPanel from './components/ExportPanel'

export default function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* Left sidebar */}
      <Sidebar />

      {/* Map area */}
      <main className="relative flex-1 overflow-hidden">
        <MapCanvas />
        <BrushTools />
        <ExportPanel />
      </main>
    </div>
  )
}
