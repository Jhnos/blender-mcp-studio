// Dummy fixtures for the T3 dummy run. Prefixed conceptually as mock data —
// they feed the REAL frontend + REAL MDR engine; only the backend is swapped.
// This proves axis M (mechanism), NOT axis Q (real Blender output quality).

export const MOCK_OBJECTS = [
  { name: 'Cube', type: 'MESH' },
  { name: 'Table_Top', type: 'MESH' },
  { name: 'Sun', type: 'LIGHT' },
  { name: 'Camera', type: 'CAMERA' },
  { name: 'Bezier', type: 'CURVE' },
]

export const MOCK_SNAPSHOTS = [
  { id: 'snap_1', label: '初始場景', created_at: '2026-07-15T10:00:00Z', session_id: 'mock', thumbnail: null },
  { id: 'snap_2', label: '加了燈光', created_at: '2026-07-15T10:12:00Z', session_id: 'mock', thumbnail: null },
]

export const MOCK_MATERIALS = Array.from({ length: 6 }, (_, i) => ({
  id: `asset_${i}`,
  name: ['Studio HDRI', 'Sunset Sky', 'Wood Planks', 'Concrete', 'Brick Wall', 'Marble'][i],
  categories: ['indoor', 'studio'],
  tags: ['pbr'],
  thumbnail_url: '',
  download_count: 1000 + i,
}))

// A crisp SVG stands in for the rendered viewport (returned as a blob; <img>
// renders SVG blobs fine, avoiding hand-crafted PNG bytes).
export const MOCK_PREVIEW_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
  <rect width="480" height="360" fill="#0b0d12"/>
  <ellipse cx="240" cy="300" rx="150" ry="24" fill="#12151c"/>
  <path d="M240 90 L360 150 L240 210 L120 150 Z" fill="#8f72ff"/>
  <path d="M240 210 L360 150 L360 250 L240 310 Z" fill="#7c5cff"/>
  <path d="M240 210 L120 150 L120 250 L240 310 Z" fill="#5f45cc"/>
  <text x="240" y="345" fill="#7b8494" font-family="system-ui" font-size="13" text-anchor="middle">dummy viewport (mock)</text>
</svg>`
