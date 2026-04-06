import { useState, useCallback } from 'react'

const _base = import.meta.env.BASE_URL.replace(/\/$/, '')

interface PHAsset {
  id: string
  name: string
  categories: string[]
  tags: string[]
  thumbnail_url: string
  download_count: number
}

const ASSET_TYPES = [
  { value: 'hdri', label: '🌅 HDRI 環境光' },
  { value: 'texture', label: '🎨 材質貼圖' },
]

const RESOLUTIONS = ['1k', '2k', '4k']

export function MaterialBrowserPanel() {
  const [query, setQuery] = useState('')
  const [assetType, setAssetType] = useState('hdri')
  const [resolution, setResolution] = useState('1k')
  const [results, setResults] = useState<PHAsset[]>([])
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)

  const showStatus = (msg: string) => {
    setStatus(msg)
    setTimeout(() => setStatus(null), 3000)
  }

  const handleSearch = useCallback(async () => {
    setLoading(true)
    setSearched(true)
    try {
      const params = new URLSearchParams({ q: query, asset_type: assetType, limit: '24' })
      const res = await fetch(`${_base}/api/materials/search?${params.toString()}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as { results: PHAsset[] }
      setResults(data.results)
    } catch (e) {
      showStatus(`❌ 搜尋失敗：${String(e)}`)
    } finally {
      setLoading(false)
    }
  }, [query, assetType])

  const handleApply = useCallback(async (asset: PHAsset) => {
    setApplying(asset.id)
    try {
      const fileFormat = assetType === 'hdri' ? 'hdr' : 'jpg'
      const applyAs = assetType === 'hdri' ? 'hdri' : 'texture'

      const res = await fetch(`${_base}/api/materials/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: asset.id,
          resolution,
          file_format: fileFormat,
          apply_as: applyAs,
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText })) as { detail: string }
        throw new Error(err.detail)
      }

      showStatus(`✅ 已套用：${asset.name} (${resolution})`)
    } catch (e) {
      showStatus(`❌ 套用失敗：${String(e)}`)
    } finally {
      setApplying(null)
    }
  }, [assetType, resolution])

  return (
    <div className="flex flex-col gap-2 p-3 h-full overflow-auto">
      {/* Controls */}
      <div className="flex flex-col gap-2">
        {/* Type selector */}
        <div className="flex gap-1">
          {ASSET_TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => { setAssetType(t.value); setResults([]); setSearched(false) }}
              className={`flex-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
                assetType === t.value
                  ? 'bg-violet-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Search bar */}
        <div className="flex gap-1.5">
          <input
            className="flex-1 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            placeholder="搜尋 Poly Haven 資產..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void handleSearch() }}
          />
          <button
            onClick={() => void handleSearch()}
            disabled={loading}
            className="rounded bg-violet-600 px-3 py-1 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
          >
            {loading ? '⟳' : '搜尋'}
          </button>
        </div>

        {/* Resolution */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>解析度:</span>
          {RESOLUTIONS.map((r) => (
            <button
              key={r}
              onClick={() => setResolution(r)}
              className={`rounded px-2 py-0.5 transition-colors ${
                resolution === r
                  ? 'bg-blue-700 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Status */}
      {status && (
        <div className="rounded bg-gray-700 px-3 py-1 text-center text-sm text-white">
          {status}
        </div>
      )}

      {/* Results grid */}
      {!searched && (
        <p className="text-center text-sm text-gray-500 mt-4">
          搜尋 Poly Haven 免費 HDRI 和材質
        </p>
      )}
      {searched && results.length === 0 && !loading && (
        <p className="text-center text-sm text-gray-500 mt-4">沒有找到結果</p>
      )}

      <div className="grid grid-cols-2 gap-2">
        {results.map((asset) => (
          <div
            key={asset.id}
            className="rounded border border-gray-700 bg-gray-800 overflow-hidden"
          >
            {/* Thumbnail */}
            {asset.thumbnail_url ? (
              <img
                src={asset.thumbnail_url}
                alt={asset.name}
                className="w-full h-20 object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-20 bg-gray-700 flex items-center justify-center text-2xl">
                🌐
              </div>
            )}

            {/* Info + apply */}
            <div className="p-1.5">
              <p className="text-xs font-medium text-white truncate" title={asset.name}>
                {asset.name}
              </p>
              <p className="text-[10px] text-gray-500 truncate">
                {asset.categories.slice(0, 2).join(' · ')}
              </p>
              <button
                onClick={() => void handleApply(asset)}
                disabled={applying === asset.id}
                className="mt-1 w-full rounded bg-green-700 py-0.5 text-xs text-white hover:bg-green-600 disabled:opacity-50 transition-colors"
              >
                {applying === asset.id ? '套用中...' : `✓ 套用 ${resolution}`}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
