import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // Ignore built artefacts and generated files
  { ignores: ["dist", "node_modules"] },

  // Base JS recommended + TypeScript strict + React rules
  {
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
    ],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      // ---- React Hooks ----
      // Enforce the Rules of Hooks and exhaustive dependency arrays.
      // exhaustive-deps catches missing deps that cause stale-closure bugs
      // (the most common source of subtle React interview-flow bugs in this project).
      ...reactHooks.configs.recommended.rules,

      // ---- React Refresh (Vite HMR) ----
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],

      // ---- TypeScript ----
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          // Underscore-prefixed params are intentionally unused (e.g. `_event`)
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],

      // ---- General JS quality ----
      "no-console": ["warn", { allow: ["error", "warn"] }],
      "no-debugger": "error",
      "prefer-const": "error",
      eqeqeq: ["error", "always", { null: "ignore" }],
    },
  },

  // Context and hook files intentionally co-locate a Provider component with a
  // useXxx hook export — this is idiomatic React and does not cause HMR problems
  // in practice. Suppress the react-refresh warning for these files only.
  {
    files: ["**/context/**/*.{ts,tsx}", "**/hooks/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
);
