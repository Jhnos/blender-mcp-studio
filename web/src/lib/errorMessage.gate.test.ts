import { execFileSync } from 'node:child_process'
import { describe, expect, it } from 'vitest'

/**
 * Wiring proof for the `no-restricted-syntax` rule that bans hand-rolled
 * `instanceof Error` checks.
 *
 * An eslint config gives no feedback when a selector matches nothing — a typo in
 * the AST selector produces a rule that is present, loaded, and completely
 * inert. So the rule is exercised the way a developer would hit it: real eslint,
 * real source on stdin, and an assertion on the exit code.
 *
 * Both directions are covered. The should-fire case proves it still catches; the
 * should-pass case proves it does not flag the ordinary code around it, which is
 * the failure mode a too-broad selector would produce.
 */
const runEslint = (source: string, filename: string): { code: number; output: string } => {
  try {
    const output = execFileSync(
      'npx',
      ['eslint', '--no-color', '--stdin', '--stdin-filename', filename],
      { input: source, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] },
    )
    return { code: 0, output }
  } catch (error) {
    const failure = error as { status?: number; stdout?: string; stderr?: string }
    return { code: failure.status ?? 1, output: `${failure.stdout ?? ''}${failure.stderr ?? ''}` }
  }
}

describe('the hand-rolled error-message rule', () => {
  it('rejects a hand-rolled instanceof Error check', () => {
    const source = 'export const f = (e: unknown) => (e instanceof Error ? e.message : String(e))\n'
    const { code, output } = runEslint(source, 'src/components/Sample.ts')

    expect(code).not.toBe(0)
    expect(output).toContain('no-restricted-syntax')
  }, 60_000)

  it('accepts code that calls the shared helper', () => {
    const source = [
      "import { errorMessage } from '../lib/errorMessage'",
      'export const f = (e: unknown) => errorMessage(e)',
      '',
    ].join('\n')
    const { code } = runEslint(source, 'src/components/Sample.ts')

    expect(code).toBe(0)
  }, 60_000)

  it('still allows the implementation itself', () => {
    const source = 'export const f = (e: unknown) => (e instanceof Error ? e.message : String(e))\n'
    const { code } = runEslint(source, 'src/lib/errorMessage.ts')

    expect(code).toBe(0)
  }, 60_000)
})
