/**
 * Turn an unknown thrown value into a message a person can read.
 *
 * `catch` binds `unknown`, so every call site had written the same ternary —
 * five copies, one of which reported into a panel-local state while the others
 * reported into the shared operation store. Sharing the conversion is what makes
 * that inconsistency visible instead of invisible.
 */
export const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : String(error)
