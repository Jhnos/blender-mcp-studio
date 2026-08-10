import type { CommandDefinition, CommandRegistry } from './types'

const normalize = (value: string): string => value.trim().toLocaleLowerCase()

const matchRank = (command: CommandDefinition, query: string): number | null => {
  const title = normalize(command.title)
  if (title.startsWith(query)) return 0
  if (title.includes(query)) return 1
  if (command.keywords.some((keyword) => normalize(keyword).includes(query))) return 2
  return null
}

export function createCommandRegistry(): CommandRegistry {
  const commands = new Map<string, CommandDefinition>()

  const list = (): CommandDefinition[] => (
    [...commands.values()].filter((command) => command.isAvailable())
  )

  return {
    register: (command) => {
      if (!command.id.trim() || !command.title.trim()) {
        throw new Error('Command id and title are required')
      }
      if (commands.has(command.id)) {
        throw new Error(`Duplicate command id: ${command.id}`)
      }
      commands.set(command.id, command)
    },
    list,
    search: (rawQuery) => {
      const query = normalize(rawQuery)
      if (!query) return list()
      return list()
        .map((command, index) => ({ command, index, rank: matchRank(command, query) }))
        .filter((item): item is typeof item & { rank: number } => item.rank !== null)
        .sort((left, right) => left.rank - right.rank || left.index - right.index)
        .map((item) => item.command)
    },
  }
}
