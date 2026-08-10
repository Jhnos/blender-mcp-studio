import { useEffect, useState } from 'react'
import { Button, EmptyState } from './ui'

interface ModelViewportProps {
  imageUrl: string | null
  loading: boolean
  toast?: string | null
}

const MIN_ZOOM = 75
const MAX_ZOOM = 200
const ZOOM_STEP = 25

export function ModelViewport({ imageUrl, loading, toast = null }: ModelViewportProps) {
  const [zoom, setZoom] = useState(100)
  const [focused, setFocused] = useState(false)

  useEffect(() => {
    if (!focused) return
    const exitOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFocused(false)
    }
    window.addEventListener('keydown', exitOnEscape)
    return () => window.removeEventListener('keydown', exitOnEscape)
  }, [focused])

  return (
    <section
      data-testid="model-viewport"
      data-focused={focused}
      aria-label="3D 模型工作區"
      className={`model-viewport isolate min-h-0 overflow-hidden bg-surface-sunken ${
        focused
          ? 'fixed inset-0 z-[100] p-6 sm:p-10'
          : 'relative h-full w-full rounded-xl border border-border-strong'
      }`}
    >
      <div className="model-viewport-grid absolute inset-0" aria-hidden />
      <span className="viewport-corner viewport-corner-tl" aria-hidden />
      <span className="viewport-corner viewport-corner-tr" aria-hidden />
      <span className="viewport-corner viewport-corner-bl" aria-hidden />
      <span className="viewport-corner viewport-corner-br" aria-hidden />

      <div className="absolute left-4 top-4 z-20 flex items-center gap-2 rounded-md border border-border/80 bg-surface/85 px-2.5 py-1.5 backdrop-blur">
        <span className="h-1.5 w-1.5 rounded-full bg-warning shadow-[0_0_8px_var(--color-warning)]" />
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-fg-muted">Model viewport</span>
      </div>

      <div className="absolute right-4 top-4 z-20 flex items-center gap-1 rounded-lg border border-border/80 bg-surface/90 p-1 shadow-lg backdrop-blur">
        <Button
          variant="ghost"
          icon="zoom-out"
          iconOnly
          aria-label="縮小預覽"
          title="縮小預覽"
          disabled={!imageUrl || zoom === MIN_ZOOM}
          onClick={() => setZoom((value) => Math.max(MIN_ZOOM, value - ZOOM_STEP))}
        />
        <button
          type="button"
          aria-label="重設預覽倍率"
          className="min-w-14 rounded px-2 py-1.5 font-mono text-[10px] tabular-nums text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          onClick={() => setZoom(100)}
        >
          <span aria-live="polite">預覽倍率 {zoom}%</span>
        </button>
        <Button
          variant="ghost"
          icon="zoom-in"
          iconOnly
          aria-label="放大預覽"
          title="放大預覽"
          disabled={!imageUrl || zoom === MAX_ZOOM}
          onClick={() => setZoom((value) => Math.min(MAX_ZOOM, value + ZOOM_STEP))}
        />
        <span className="mx-0.5 h-4 w-px bg-border" aria-hidden />
        <Button
          variant="ghost"
          icon={focused ? 'minimize' : 'maximize'}
          iconOnly
          aria-label={focused ? '離開專注預覽' : '進入專注預覽'}
          title={focused ? '離開專注預覽 (Esc)' : '進入專注預覽'}
          disabled={!imageUrl}
          onClick={() => setFocused((value) => !value)}
        />
      </div>

      <div className="relative z-10 flex h-full w-full items-center justify-center overflow-hidden p-5 sm:p-8">
        {loading && !imageUrl && (
          <span className="animate-pulse font-mono text-xs uppercase tracking-widest text-fg-subtle">
            載入預覽中
          </span>
        )}
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="Blender 模型預覽"
            className="h-full w-full object-contain drop-shadow-[0_20px_45px_rgba(0,0,0,0.45)] transition-transform duration-200 ease-out"
            style={{ transform: `scale(${zoom / 100})` }}
          />
        ) : !loading && (
          <EmptyState icon="camera" title="無法取得預覽" hint="請確認 Blender 正在運行" />
        )}
      </div>

      {toast && (
        <div
          role="status"
          className="absolute bottom-4 left-1/2 z-30 -translate-x-1/2 rounded-md border border-border bg-surface-overlay px-3 py-2 text-xs text-fg-muted shadow-xl"
        >
          {toast}
        </div>
      )}
    </section>
  )
}
