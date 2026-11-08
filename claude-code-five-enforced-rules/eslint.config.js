// Conventions as lint rules. Run on every edited file by .claude/hooks/lint-edit.sh.
import tseslint from "typescript-eslint";

export default [
  {
    files: ["src/**/*.ts", "test/**/*.ts"],
    languageOptions: { parser: tseslint.parser },
    plugins: { "@typescript-eslint": tseslint.plugin },
    rules: {
      "no-restricted-syntax": [
        "error",
        { selector: "TSInterfaceDeclaration", message: "Use `type`, never `interface` (project convention)." },
        { selector: "TSEnumDeclaration", message: "Use a const object or a union type, never `enum` (project convention)." },
      ],
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  {
    files: ["src/domain/**/*.ts"],
    rules: { "no-restricted-imports": ["error", { patterns: [
      { group: ["node:fs", "node:http", "fs", "http"], message: "src/domain has no I/O." },
      { group: ["../store/*", "../http/*", "**/store/*", "**/http/*"], message: "src/domain imports nothing from store or http." },
    ] }] },
  },
  {
    files: ["src/http/handlers/**/*.ts"],
    rules: { "no-restricted-imports": ["error", { patterns: [
      { group: ["../../store/*", "**/store/*"], message: "Handlers reach the store through the app context only." },
    ] }] },
  },
];
