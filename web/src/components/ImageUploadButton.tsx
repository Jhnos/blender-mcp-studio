import { useRef, useState } from 'react'

const _base = import.meta.env.BASE_URL.replace(/\/$/, '')

interface Props {
  /** Called with the description string when vision analysis succeeds */
  onDescription: (desc: string) => void
  disabled?: boolean
}

/**
 * ImageUploadButton — paperclip button that sends an image to POST /api/chat/image
 * and returns the vision description as text the user can inject into chat.
 */
export function ImageUploadButton({ onDescription, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setLoading(true)
    try {
      const form = new FormData()
      form.append('image', file)
      const res = await fetch(`${_base}/api/chat/image`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText })) as { detail: string }
        throw new Error(err.detail)
      }
      const data = await res.json() as { description: string; suggestions: string[] }
      // Build a prompt-ready summary
      let text = `[圖片分析] ${data.description}`
      if (data.suggestions?.length) {
        text += `\n建議：${data.suggestions.slice(0, 3).join('；')}`
      }
      onDescription(text)
    } catch (e) {
      setError(String(e))
      setTimeout(() => setError(null), 4000)
    } finally {
      setLoading(false)
      // Reset so same file can be re-selected
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) void handleFile(file)
        }}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || loading}
        title="上傳圖片作為參考（需要 Vision LLM）"
        className="rounded p-1.5 text-slate-400 hover:text-violet-400 hover:bg-slate-700 disabled:opacity-40 transition-colors"
      >
        {loading ? (
          <span className="animate-pulse text-sm">🔍</span>
        ) : (
          <span className="text-sm">📎</span>
        )}
      </button>
      {error && (
        <div className="absolute bottom-9 left-0 w-48 rounded bg-red-900/90 border border-red-700 px-2 py-1 text-xs text-red-200 z-10">
          {error}
        </div>
      )}
    </div>
  )
}
