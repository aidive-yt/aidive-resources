import { defineConfig } from "vitest/config";

// The oracle runs from OUTSIDE the work copy: WORK = absolute path of the work copy under test.
const work = process.env.WORK;
if (!work) throw new Error("WORK is not set");

export default defineConfig({
  resolve: { alias: { "@work": work } },
  server: { fs: { strict: false } },
  test: { include: [`test_${process.env.TASK ?? "F1"}.test.ts`], testTimeout: 20_000, fileParallelism: false },
});
