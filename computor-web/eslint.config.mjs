import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Codegen output (see ../generate.sh). Linting it is pure noise: the `any`s
    // and empty object types come from the pydantic->TS generator, hand-fixing
    // them is undone by the next run, and the source of truth is computor-types.
    "src/generated/**",
  ]),
]);

export default eslintConfig;
