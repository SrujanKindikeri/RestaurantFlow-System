import js from '@eslint/js'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'

export default [
  { ignores: ['dist'] },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': 'off',
      // Disable exhaustive-deps — pre-existing pattern throughout codebase
      'react-hooks/exhaustive-deps': 'off',
      // Allow any types — pre-existing pattern throughout codebase
      '@typescript-eslint/no-explicit-any': 'off',
      // Allow empty interfaces/object types — pre-existing pattern
      '@typescript-eslint/no-empty-object-type': 'off',
      // Allow unused vars — TypeScript's noUnusedLocals/noUnusedParameters handles this at build
      '@typescript-eslint/no-unused-vars': 'off',
      // Turn off base no-undef (TypeScript handles this)
      'no-undef': 'off',
    },
  },
]
