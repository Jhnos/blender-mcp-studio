export interface CommandDefinition {
  id: string
  title: string
  keywords: readonly string[]
  isAvailable: () => boolean
  run: () => void | Promise<void>
}

export interface CommandRegistry {
  register: (command: CommandDefinition) => void
  list: () => CommandDefinition[]
  search: (query: string) => CommandDefinition[]
}
