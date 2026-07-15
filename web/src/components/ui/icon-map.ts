import {
  Send, Undo2, Redo2, Download, RefreshCw, Trash2, Pencil, Search, Check,
  Camera, RotateCcw, Play, Sparkles, ChevronDown, ChevronRight, Lightbulb,
  Box, Boxes, Palette, Sun, History, ScrollText, X, SlidersHorizontal,
  TriangleAlert, CircleCheck, CircleX, Info, Plus, Radio, ImagePlus,
  MousePointer2, Spline, Bone, Circle, Wifi, WifiOff, type LucideIcon,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Semantic icon map (data, not a component — kept out of Icon.tsx so that file
// exports only a component, per react-refresh). Swapping icon libraries only
// touches this map: one consistent visual vocabulary replacing emoji-as-icon.
// ---------------------------------------------------------------------------

export const ICON_MAP = {
  // actions
  send: Send,
  undo: Undo2,
  redo: Redo2,
  export: Download,
  refresh: RefreshCw,
  delete: Trash2,
  rename: Pencil,
  search: Search,
  apply: Check,
  snapshot: Camera,
  restore: RotateCcw,
  refine: Play,
  ai: Sparkles,
  upload: ImagePlus,
  select: MousePointer2,
  add: Plus,
  close: X,
  settings: SlidersHorizontal,
  // disclosure
  'chevron-down': ChevronDown,
  'chevron-right': ChevronRight,
  // scene object types
  mesh: Box,
  curve: Spline,
  light: Lightbulb,
  camera: Camera,
  empty: Circle,
  armature: Bone,
  // inspector sections
  scene: Boxes,
  material: Palette,
  hdri: Sun,
  history: History,
  log: ScrollText,
  // status
  success: CircleCheck,
  warning: TriangleAlert,
  danger: CircleX,
  info: Info,
  live: Radio,
  connected: Wifi,
  disconnected: WifiOff,
} satisfies Record<string, LucideIcon>

export type IconName = keyof typeof ICON_MAP
