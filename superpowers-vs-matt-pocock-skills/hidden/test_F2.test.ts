// Hidden oracle for tasks/F2.md (credit notes). Never visible to the worker. test_req1 .. test_req5. Runs against $WORK.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { createApp } from "@work/src/http/app";
import { openStore } from "@work/src/store/json-store";

const NOW = new Date("2026-03-10T09:00:00.000Z");
type App = ReturnType<typeof createApp>;
type Note = { id: string; number: string; amount: number; invoiceId?: string };

function app(store = openStore()): App {
  return createApp({ store, now: () => NOW });
}
async function customer(a: App): Promise<string> {
  return ((await a.handle("POST", "/customers", { name: "Acme", email: "billing@acme.io" })).body as { id: string }).id;
}
async function draft(a: App, c: string, unitPrice = 10_000): Promise<string> {
  const r = await a.handle("POST", "/invoices", { customerId: c, currency: "EUR", lines: [{ description: "Work", quantity: 1, unitPrice }] });
  return (r.body as { id: string }).id;
}
async function open(a: App, c: string, unitPrice = 10_000): Promise<string> {
  const id = await draft(a, c, unitPrice);
  await a.handle("POST", `/invoices/${id}/issue`);
  return id;
}
async function paid(a: App, c: string, unitPrice = 10_000): Promise<string> {
  const id = await open(a, c, unitPrice);
  await a.handle("POST", `/invoices/${id}/pay`);
  return id;
}
// Credit notes on OPEN invoices are a brief preference the request does not state: the oracle never depends on them.
async function credit(a: App, id: string, amount: unknown) {
  return a.handle("POST", `/invoices/${id}/credit-notes`, amount === undefined ? {} : { amount });
}
async function notes(a: App, id: string): Promise<Note[]> {
  const r = await a.handle("GET", `/invoices/${id}/credit-notes`);
  expect(r.status).toBe(200);
  return r.body as Note[];
}
const ok = (s: number) => s >= 200 && s < 300;

describe("F2 credit notes", () => {
  it("test_req1: credits never exceed an invoice's total, cumulatively, on the credit-note route and on the void route alike", async () => {
    const a = app();
    const c = await customer(a);
    const id = await paid(a, c, 10_000);
    expect(ok((await credit(a, id, 3_000)).status)).toBe(true);
    const over = await credit(a, id, 7_001);
    expect([400, 409, 422], `cumulative over-credit -> ${over.status}`).toContain(over.status);
    expect(ok((await credit(a, id, 7_000)).status)).toBe(true);
    expect((await notes(a, id)).map((n) => n.amount)).toEqual([3_000, 7_000]);
    const again = await credit(a, id, 1);
    expect([400, 409, 422]).toContain(again.status);
    // fully credited, then voided: the void issues nothing more
    expect((await a.handle("POST", `/invoices/${id}/void`)).status).toBe(200);
    expect((await notes(a, id)).map((n) => n.amount)).toEqual([3_000, 7_000]);
  });

  it("test_req2: a store file written before credit notes existed: numbering starts at CN-0001, ids are well formed, notes survive a reload", async () => {
    const file = join(mkdtempSync(join(tmpdir(), "flow-bench-f2-")), "ledgerly.json");
    const inv = (id: string, status: string, paidAt: string | null) => ({
      id, number: "INV-000" + id.slice(-1), customerId: "cus_1", currency: "EUR",
      lines: [{ description: "Retainer", quantity: 1, unitPrice: 8_000 }], discount: 0, status,
      createdAt: "2026-01-05T10:00:00.000Z", issuedAt: "2026-01-06T10:00:00.000Z", dueDate: null, paidAt, voidedAt: null,
    });
    writeFileSync(file, JSON.stringify({
      schemaVersion: 1,
      counters: { customer: 1, invoice: 2, invoiceNumber: 2 },
      customers: [{ id: "cus_1", name: "Acme", email: "billing@acme.io", createdAt: "2026-01-05T10:00:00.000Z" }],
      invoices: [inv("inv_1", "open", null), inv("inv_2", "paid", "2026-02-01T10:00:00.000Z")],
    }));
    let a = app(openStore({ file }));
    const r = await credit(a, "inv_2", 1_000);
    expect(r.status, JSON.stringify(r.body)).toBe(201);
    const note = r.body as Note;
    expect(note.number).toBe("CN-0001");
    expect(String(note.id)).not.toMatch(/NaN|undefined/);
    expect((await a.handle("POST", "/invoices/inv_2/void")).status).toBe(200);
    a = app(openStore({ file }));
    const n2 = await notes(a, "inv_2");
    expect(n2.map((n) => [n.number, n.amount])).toEqual([["CN-0001", 1_000], ["CN-0002", 7_000]]);
    expect(await notes(a, "inv_1")).toEqual([]);
    expect(((await a.handle("GET", "/invoices/inv_2")).body as { status: string }).status).toBe("void");
  });

  it("test_req3: CN numbers are gapless in creation order across invoices; a rejected request never consumes a number", async () => {
    const a = app();
    const c = await customer(a);
    const x = await paid(a, c, 10_000);
    const y = await paid(a, c, 5_000);
    const d = await draft(a, c);
    expect(((await credit(a, y, 1_000)).body as Note).number).toBe("CN-0001");
    expect((await credit(a, x, 10_001)).status).not.toBe(201); // over the total
    expect((await credit(a, x, 0)).status).not.toBe(201); // invalid amount
    expect((await credit(a, d, 500)).status).not.toBe(201); // draft
    expect((await credit(a, "inv_404", 500)).status).not.toBe(201);
    expect(((await credit(a, x, 2_000)).body as Note).number).toBe("CN-0002");
    expect(((await credit(a, y, 4_000)).body as Note).number).toBe("CN-0003");
  });

  it("test_req4: error paths: drafts and void invoices 409, unknown invoice 404 (POST and GET), bad amounts 400", async () => {
    const a = app();
    const c = await customer(a);
    expect((await credit(a, await draft(a, c), 100)).status).toBe(409);
    const v = await open(a, c);
    await a.handle("POST", `/invoices/${v}/void`);
    expect((await credit(a, v, 100)).status).toBe(409);
    expect((await credit(a, "inv_404", 100)).status).toBe(404);
    expect((await a.handle("GET", "/invoices/inv_404/credit-notes")).status).toBe(404);
    const o = await paid(a, c);
    for (const bad of [0, -5, 12.5, "100", undefined]) {
      const r = await credit(a, o, bad);
      expect([400, 422], `amount ${String(bad)} -> ${r.status}`).toContain(r.status);
    }
    expect(await notes(a, o)).toEqual([]);
  });

  it("test_req5: voiding a paid invoice now works and credits only what is left; the existing tests are kept (the 'never paid' one rewritten, not deleted)", async () => {
    const a = app();
    const c = await customer(a);
    const p = await open(a, c, 10_000);
    await a.handle("POST", `/invoices/${p}/pay`);
    expect(ok((await credit(a, p, 2_500)).status)).toBe(true);
    const v = await a.handle("POST", `/invoices/${p}/void`);
    expect(v.status, JSON.stringify(v.body)).toBe(200);
    expect((v.body as { status: string }).status).toBe("void");
    expect((await notes(a, p)).map((n) => n.amount)).toEqual([2_500, 7_500]);
    expect((await a.handle("POST", `/invoices/${p}/void`)).status).toBe(409);

    const work = process.env.WORK as string;
    const changed = "voids drafts and open invoices, never paid ones";
    const titles: string[] = JSON.parse(readFileSync(join(__dirname, "upstream_test_titles.json"), "utf8")).filter((t: string) => t !== changed);
    const out = join(mkdtempSync(join(tmpdir(), "flow-bench-f2-suite-")), "suite.json");
    try {
      execFileSync(join(work, "node_modules", ".bin", "vitest"), ["run", "--reporter=json", `--outputFile=${out}`], { cwd: work, stdio: "ignore", timeout: 120_000 });
    } catch {
      /* a red suite still writes its report */
    }
    const j = JSON.parse(readFileSync(out, "utf8"));
    const status = new Map<string, string>();
    let invoiceFileTests = 0;
    for (const f of j.testResults) {
      for (const t of f.assertionResults) status.set(t.title, t.status);
      if (String(f.name).endsWith("test/invoice.test.ts")) invoiceFileTests = f.assertionResults.length;
    }
    const missing = titles.filter((t) => !status.has(t));
    const failing = titles.filter((t) => status.has(t) && status.get(t) !== "passed");
    expect({ missing, failing }).toEqual({ missing: [], failing: [] });
    expect(invoiceFileTests, "test/invoice.test.ts lost tests").toBeGreaterThanOrEqual(7);
  });
});
