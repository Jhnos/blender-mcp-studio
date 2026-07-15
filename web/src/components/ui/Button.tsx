import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

// ---------------------------------------------------------------------------
// Button primitive — one place for every button style in the app.
// Variants map to semantic tokens; sizes keep hit targets comfortable
// (Fitts's Law: important/frequent targets shouldn't be tiny).
// ---------------------------------------------------------------------------

type Variant = 'primary' | 'ghost' | 'subtle' | 'danger'
type Size = 'sm' | 'md'

const VARIANT: Record<Variant, string> = {
  primary: 'bg-accent hover:bg-accent-hover text-accent-fg',
  ghost: 'bg-transparent hover:bg-surface-overlay text-fg-muted hover:text-fg',
  subtle: 'bg-surface-overlay hover:bg-border text-fg-muted hover:text-fg',
  danger: 'bg-transparent hover:bg-danger-bg text-fg-muted hover:text-danger',
}

const SIZE: Record<Size, string> = {
  sm: 'text-xs px-2.5 py-1.5 gap-1.5 rounded-md min-h-[28px]',
  md: 'text-sm px-4 py-2 gap-2 rounded-lg min-h-[36px]',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  icon?: IconName
  iconOnly?: boolean
  children?: ReactNode
}

export function Button({
  variant = 'subtle',
  size = 'sm',
  icon,
  iconOnly = false,
  children,
  className = '',
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center font-medium transition-colors
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
                  disabled:opacity-40 disabled:cursor-not-allowed
                  ${VARIANT[variant]} ${SIZE[size]} ${iconOnly ? '!px-0 aspect-square' : ''} ${className}`}
      {...rest}
    >
      {icon && <Icon name={icon} size={size === 'sm' ? 14 : 16} />}
      {!iconOnly && children}
    </button>
  )
}
