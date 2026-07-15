import { Circle } from 'lucide-react'
import { ICON_MAP, type IconName } from './icon-map'

export type { IconName }

// ---------------------------------------------------------------------------
// Icon — semantic wrapper. Components ask for `name="delete"`, not `<Trash2/>`.
// Unknown names degrade to a neutral dot rather than crashing.
// ---------------------------------------------------------------------------

interface IconProps {
  name: IconName
  size?: number
  className?: string
  'aria-hidden'?: boolean
  'aria-label'?: string
}

export function Icon({ name, size = 16, className, ...rest }: IconProps) {
  const Cmp = ICON_MAP[name] ?? Circle
  const isLabelled = rest['aria-label'] != null
  return (
    <Cmp
      size={size}
      className={className}
      aria-hidden={isLabelled ? undefined : true}
      {...rest}
    />
  )
}
