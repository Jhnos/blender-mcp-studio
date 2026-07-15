import { useCallback, useState } from 'react'
import { Button, EmptyState, Icon, SegmentedControl } from '../../components/ui'
import type { NodeProps } from '../registry'
import type { PHAsset } from '../apiActions'

// ---------------------------------------------------------------------------
// asset-browser — search & apply Poly Haven HDRI / textures via dispatch.
// ---------------------------------------------------------------------------

type AssetType = 'hdri' | 'texture'
const RESOLUTIONS = ['1k', '2k', '4k'] as const

export function AssetBrowserNode({ dispatch }: NodeProps) {
  const [query, setQuery] = useState('')
  const [assetType, setAssetType] = useState<AssetType>('hdri')
  const [resolution, setResolution] = useState<string>('1k')
  const [results, setResults] = useState<PHAsset[]>([])
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)

  const toast = (msg: string) => { setStatus(msg); setTimeout(() => setStatus(null), 3000) }

  const search = useCallback(async () => {
    setLoading(true); setSearched(true)
    try {
      const { results } = await dispatch('material.search', { query, assetType }) as { results: PHAsset[] }
      setResults(results ?? [])
    } catch (e) { toast(`搜尋失敗：${String(e)}`) }
    finally { setLoading(false) }
  }, [dispatch, query, assetType])

  const apply = useCallback(async (asset: PHAsset) => {
    setApplying(asset.id)
    try {
      await dispatch('material.apply', {
        assetId: asset.id,
        resolution,
        fileFormat: assetType === 'hdri' ? 'hdr' : 'jpg',
        applyAs: assetType === 'hdri' ? 'hdri' : 'texture',
      })
      toast(`已套用：${asset.name} (${resolution})`)
    } catch (e) { toast(`套用失敗：${String(e)}`) }
    finally { setApplying(null) }
  }, [dispatch, resolution, assetType])

  return (
    <div className="flex flex-col gap-2 px-2">
      <SegmentedControl<AssetType>
        aria-label="資產類型"
        value={assetType}
        onChange={(v) => { setAssetType(v); setResults([]); setSearched(false) }}
        options={[
          { value: 'hdri', label: 'HDRI 環境光', icon: 'hdri' },
          { value: 'texture', label: '材質貼圖', icon: 'material' },
        ]}
        className="w-full [&>*]:flex-1"
      />

      <div className="flex gap-1.5">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void search() }}
          placeholder="搜尋 Poly Haven 資產..."
          className="flex-1 rounded-md border border-border bg-surface-sunken px-2 py-1 text-sm
                     text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <Button variant="primary" icon="search" onClick={() => void search()} disabled={loading}>
          {loading ? '搜尋中' : '搜尋'}
        </Button>
      </div>

      <div className="flex items-center gap-2 text-xs text-fg-subtle">
        <span>解析度</span>
        <SegmentedControl
          aria-label="解析度"
          value={resolution}
          onChange={setResolution}
          options={RESOLUTIONS.map((r) => ({ value: r, label: r }))}
        />
      </div>

      {status && (
        <div className="rounded-md bg-surface-overlay px-3 py-1 text-center text-xs text-fg-muted">{status}</div>
      )}

      {!searched && <EmptyState icon="material" title="搜尋免費 HDRI 和材質" hint="來自 Poly Haven" />}
      {searched && !loading && results.length === 0 && (
        <EmptyState icon="search" title="沒有找到結果" />
      )}

      <div className="grid grid-cols-2 gap-2">
        {results.map((asset) => (
          <div key={asset.id} className="overflow-hidden rounded-md border border-border bg-surface-raised">
            {asset.thumbnail_url ? (
              <img src={asset.thumbnail_url} alt={asset.name} loading="lazy" className="h-20 w-full object-cover" />
            ) : (
              <div className="flex h-20 w-full items-center justify-center bg-surface-overlay">
                <Icon name="hdri" size={22} className="text-fg-subtle" />
              </div>
            )}
            <div className="p-1.5">
              <p className="truncate text-xs font-medium text-fg" title={asset.name}>{asset.name}</p>
              <p className="truncate text-[10px] text-fg-subtle">{asset.categories.slice(0, 2).join(' · ')}</p>
              <Button
                variant="primary" size="sm" icon="apply"
                className="mt-1 w-full"
                onClick={() => void apply(asset)}
                disabled={applying === asset.id}
              >
                {applying === asset.id ? '套用中' : `套用 ${resolution}`}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
