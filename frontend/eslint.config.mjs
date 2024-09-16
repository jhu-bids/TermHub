import globals from "globals";
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import jestPlugin from "eslint-plugin-jest";

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{js,mjs,cjs,ts,jsx,tsx}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node
      },
      parserOptions: {
        ecmaFeatures: {
          jsx: true
        }
      }
    },
    plugins: {
      react: reactPlugin,
      '@typescript-eslint': tseslint.plugin,
    },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      '@typescript-eslint/no-unused-expressions': ['error', {
        allowShortCircuit: true,
        allowTernary: true
      }]
    }
  },
  {
    files: ["**/*.{test,spec}.{js,mjs,cjs,ts,jsx,tsx}"],
    plugins: {
      jest: jestPlugin
    },
    rules: {
      ...jestPlugin.configs.recommended.rules
    }
  }
];