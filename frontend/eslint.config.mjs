import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // These match Vercel's stricter rules
      "@typescript-eslint/no-unused-vars": "error",
      "no-unused-vars": "off", // Use the TypeScript rule instead
      "import/no-extraneous-dependencies": "error",
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/explicit-module-boundary-types": "warn",
    },
  },
];

export default eslintConfig;
