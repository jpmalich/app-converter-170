// ESLint v9 flat config — pins the project's actual linting standard.
// See /app/CODE_QUALITY.md for the philosophy.
const reactPlugin = require("eslint-plugin-react");
const reactHooks = require("eslint-plugin-react-hooks");
const globals = require("globals");

module.exports = [
  {
    ignores: [
      "build/**",
      "node_modules/**",
      "public/**",
      "src/components/ui/**", // shadcn vendored UI primitives — third-party
    ],
  },
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.jest,
      },
    },
    plugins: {
      react: reactPlugin,
      "react-hooks": reactHooks,
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      // The real bug-catching rules:
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "no-unused-vars": ["warn", {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
      }],
      "no-undef": "error",
      "no-dupe-keys": "error",
      "no-dupe-args": "error",
      "no-unreachable": "error",
      "no-console": ["warn", { allow: ["error"] }],

      // Intentionally OFF (noise, not real bugs):
      "react/prop-types": "off",
      "react/no-unescaped-entities": "off",
      "react/react-in-jsx-scope": "off",

      // Iter 79j.21 — stale-closure smell detector. Short-delay
      // setTimeout wrapping a component-scoped function call is
      // almost always a React state-update race (see the AI Measure
      // "Run anyway" bug: the setTimeout captured runMeasure from
      // the render before setState took effect, so the closure re-fired
      // the same guard). Threshold: any setTimeout with a numeric
      // literal delay < 500ms.  If a real debounce/animation timer
      // needs this, use `// eslint-disable-next-line no-restricted-syntax`
      // above the call with a short comment explaining why.
      "no-restricted-syntax": [
        "warn",
        {
          selector: "CallExpression[callee.name='setTimeout'][arguments.1.type='Literal'][arguments.1.value<500]",
          message:
            "Short-delay setTimeout is a stale-closure smell. If you're bouncing off a setState, pass the value explicitly (e.g. fn({ bypass: true })) instead of relying on a state sentinel being read via closure.",
        },
      ],
    },
  },
];

