import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { openStore } from "../src/store/json-store";
import { CURRENT_SCHEMA_VERSION, migrate } from "../src/store/migrations";

function tmpFile(): string {
  return join(mkdtempSync(join(tmpdir(), "ledgerly-")), "data.json");
}

describe("store", () => {
  it("starts empty in memory", () => {
    const store = openStore();
    expect(store.read().invoices).toEqual([]);
    expect(store.nextId("invoice")).toBe(1);
    expect(store.nextId("invoice")).toBe(2);
  });

  it("persists updates to the file and reloads them", () => {
    const file = tmpFile();
    const store = openStore({ file });
    store.nextId("customer");
    const again = openStore({ file });
    expect(again.read().counters.customer).toBe(1);
    expect(JSON.parse(readFileSync(file, "utf8")).schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
  });

  it("migrates a v0 file (embedded customer) on load and writes it back", () => {
    const file = tmpFile();
    writeFileSync(
      file,
      JSON.stringify({
        counters: { customer: 1, invoice: 1, invoiceNumber: 0 },
        customers: [{ id: "cus_1", name: "Acme", email: "a@acme.io", createdAt: "2025-01-01T00:00:00.000Z" }],
        invoices: [{ id: "inv_1", customer: { id: "cus_1", name: "Acme" }, status: "draft" }],
      }),
    );
    const store = openStore({ file });
    expect(store.read().invoices[0]).toMatchObject({ id: "inv_1", customerId: "cus_1" });
    expect(store.read().invoices[0]).not.toHaveProperty("customer");
    expect(JSON.parse(readFileSync(file, "utf8")).schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
  });

  it("refuses a file from a newer build", () => {
    expect(() => migrate({ schemaVersion: CURRENT_SCHEMA_VERSION + 1 })).toThrow(/newer/);
  });
});
