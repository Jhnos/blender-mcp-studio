import { AppHeader } from './components/AppHeader'
import { ChatRail } from './components/ChatRail'
import { PreviewStage } from './components/PreviewStage'
import { InspectorShell } from './mdr'
import './index.css'

// Three-zone layout: conversation (input) · preview stage (focal point) ·
// inspector (schema-driven management). Replaces the old chat + 6-tab panel.
function App() {
  return (
    <div className="flex h-full flex-col bg-surface text-fg">
      <AppHeader />
      {/* Desktop-first three-zone layout. Below the min-width floor the row
          scrolls horizontally rather than squishing the preview stage
          (verified failure mode at narrow widths). */}
      <div className="min-h-0 flex-1 overflow-x-auto">
        <div className="flex h-full min-w-[1100px]">
          <ChatRail />
          <PreviewStage />
          <aside className="flex w-[340px] shrink-0 flex-col border-l border-border bg-surface-raised">
            <InspectorShell />
          </aside>
        </div>
      </div>
    </div>
  )
}

export default App
