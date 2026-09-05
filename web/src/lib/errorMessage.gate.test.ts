import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// Resolve the installed binary rather than shelling out to `npx`: npx performs
// its own resolution step and can stall under load, which would make this gate
// flake. A gate that fails for reasons unrelated to the rule teaches people to
// re-run it instead of reading it.
const WEB_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const ESLINT_BIN = resolve(WEB_ROOT, 'node_modules', '.bin', 'eslint')

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
      ESLINT_BIN,
      ['--no-color', '--stdin', '--stdin-filename', filename],
      { input: source, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], cwd: WEB_ROOT },
    )
    return { code: 0, output }
  } catch (error) {
    const failure = error as { status?: number; stdout?: string; stderr?: string }
    return { code: failure.status ?? 1, output: `${failure.stdout ?? ''}${failure.stderr ?? ''}` }
  }
}

describe('the hand-rolled error-message rule', () => {
  it('has an eslint binary to drive', () => {
    // Without this, a missing install would make every case below "pass" by
    // failing for the wrong reason.
    expect(existsSync(ESLINT_BIN)).toBe(true)
  })

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
