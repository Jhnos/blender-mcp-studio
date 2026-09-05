import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// `catch` binds `unknown`, so turning it into a string is a decision every call
// site used to make for itself — five copies, one of which then reported the
// result somewhere different from the rest. src/lib/errorMessage.ts owns it now.
// The rule is verified by src/lib/errorMessage.gate.test.ts: a mis-typed
// selector silently matches nothing, and a config file gives no feedback of its
// own when that happens.
const noHandRolledErrorMessage = {
  selector: "BinaryExpression[operator='instanceof'][right.name='Error']",
  message:
    'Use errorMessage() from src/lib/errorMessage.ts instead of hand-rolling the Error check.',
}

export default defineConfig([
  globalIgnores(['dist', 'public/mockServiceWorker.js']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      'no-restricted-syntax': ['error', noHandRolledErrorMessage],
    },
  },
  {
    // The one place allowed to make the check — it is the implementation.
    files: ['src/lib/errorMessage.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
])
