import js from "@eslint/js";
import typescript from "@typescript-eslint/eslint-plugin";
import typescriptParser from "@typescript-eslint/parser";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";

// Browser globals (including Node.js-like globals for compatibility)
const browserGlobals = {
  // React (for JSX transform and types when not using automatic runtime)
  React: true,
  // DOM
  window: true,
  document: true,
  navigator: true,
  location: true,
  history: true,
  // DOM Elements and Types
  HTMLElement: true,
  HTMLDivElement: true,
  HTMLParagraphElement: true,
  HTMLHeadingElement: true,
  HTMLButtonElement: true,
  HTMLInputElement: true,
  HTMLAnchorElement: true,
  HTMLImageElement: true,
  // DOM Collections
  NodeList: true,
  Node: true,
  EventTarget: true,
  // Events
  addEventListener: true,
  removeEventListener: true,
  Event: true,
  MouseEvent: true,
  KeyboardEvent: true,
  TouchEvent: true,
  CustomEvent: true,
  // Timers
  setTimeout: true,
  setInterval: true,
  clearTimeout: true,
  clearInterval: true,
  // Fetch
  fetch: true,
  Request: true,
  Response: true,
  Headers: true,
  // Storage
  localStorage: true,
  sessionStorage: true,
  // Others
  console: true,
  alert: true,
  confirm: true,
  prompt: true,
  URL: true,
  Blob: true,
  File: true,
  FileReader: true,
  ResizeObserver: true,
  performance: true,
  crypto: true,
  // Node.js-like globals for compatibility (in browser context)
  process: true
};

// Node globals
const nodeGlobals = {
  // Core modules
  require: true,
  module: true,
  exports: true,
  __dirname: true,
  __filename: true,
  process: true,
  Buffer: true,
  // Node.js globals
  global: true,
  // Others
  setTimeout: true,
  setInterval: true,
  clearTimeout: true,
  clearInterval: true,
  console: true
};

export default [
  js.configs.recommended,
  {
    ignores: ["dist/", "node_modules/"],
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      parser: typescriptParser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true
        }
      },
      globals: browserGlobals
    },
    plugins: {
      "@typescript-eslint": typescript,
      react: reactPlugin,
      "react-hooks": reactHooksPlugin
    },
    settings: {
      react: {
        version: "detect"
      }
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": ["error", {
        "argsIgnorePattern": "^_",
        "varsIgnorePattern": "^_"
      }],
      "@typescript-eslint/no-empty-interface": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "no-console": ["warn", {
        "allow": ["warn", "error"]
      }],
      "no-debugger": "warn",
      "no-unused-vars": "off",
      "react/jsx-filename-extension": ["warn", {
        "extensions": [".tsx"]
      }],
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off"
    }
  },
  {
    files: ["**/*.test.ts", "**/*.test.tsx"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off"
    }
  },
  {
    files: ["**/*.config.ts", "**/*.config.js"],
    rules: {
      "@typescript-eslint/no-var-requires": "off"
    },
    languageOptions: {
      globals: nodeGlobals
    }
  },
  {
    files: ["tailwind.config.js"],
    rules: {
      "@typescript-eslint/no-var-requires": "off"
    },
    languageOptions: {
      globals: nodeGlobals
    }
  }
];
