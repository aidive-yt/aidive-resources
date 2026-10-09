// Hidden oracle for tasks/F1.md (partial payments). Never visible to the worker.
// One `it` per requirement: test_req1 .. test_req5. Runs against $WORK; $BASE = the commit the run started from.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { createApp } from "@work/src/http/app";
import { openStore } from "@work/src/store/json-store";

const NOW = new Date("2026-03-10T09:00:00.000Z");
type App = ReturnType<typeof createApp>;
type Inv = { id: string; status: string; amountPaid: number; balance: number; total: number; paidAt: string | null };

function app(store = openStore()): App {
  return createApp({ store, now: () => NOW });
}

async function customer(a: App): Promise<string> {
  const r = await a.handle("POST", "/customers", { name: "Acme", email: "billing@acme.io" });
  return (r.body as { id: string }).id;
}

async function draftInvoice(a: App, customerId: string, unitPrice = 10_000): Promise<string> {
  const r = await a.handle("POST", "/invoices", {
    customerId,
    currency: "EUR",
    lines: [{ description: "Consulting", quantity: 1, unitPrice }],
  });
  return (r.body as { id: string }).id;
}

async function openInvoice(a: App, customerId: string, unitPrice = 10_000): Promise<string> {
  const id = await draftInvoice(a, customerId, unitPrice);
  await a.handle("POST", `/invoices/${id}/issue`);
  return id;
}

async function get(a: App, id: string): Promise<Inv> {
  const r = await a.handle("GET", `/invoices/${id}`);
  expect(r.status).toBe(200);
  return r.body as Inv;
}

async function pay(a: App, id: string, amount: unknown) {
  return a.handle("POST", `/invoices/${id}/payments`, amount === undefined ? {} : { amount });
}

const ok = (s: number) => s >= 200 && s < 300;

describe("F1 partial payments", () => {
  it("test_req1: partial payments accumulate, the exact remainder flips to paid, the outstanding report uses balances", async () => {
    const a = app();
    const c = await customer(a);
    const id = await openInvoice(a, c, 10_000);

    expect(ok((await pay(a, id, 3_000)).status)).toBe(true);
    let inv = await get(a, id);
    expect(inv).toMatchObject({ amountPaid: 3_000, balance: 7_000, total: 10_000 });
    expect(inv.status).not.toBe("paid");

    expect(ok((await pay(a, id, 2_500)).status)).toBe(true);
    inv = await get(a, id);
    expect(inv).toMatchObject({ amountPaid: 5_500, balance: 4_500 });
    expect(inv.status).not.toBe("paid");

    expect(ok((await pay(a, id, 4_500)).status)).toBe(true);
    inv = await get(a, id);
    expect(inv).toMatchObject({ amountPaid: 10_000, balance: 0, status: "paid" });
    expect(inv.paidAt).toBeTruthy();

    // A second, partially paid invoice: the report must count what is still owed, not the total.
    const other = await openInvoice(a, c, 10_000);
    expect(ok((await pay(a, other, 4_000)).status)).toBe(true);
    const report = await a.handle("GET", "/reports/outstanding");
    expect((report.body as { totals: Record<string, number> }).totals.EUR).toBe(6_000);
    expect((report.body as { count: number }).count).toBe(1);
  });

  it("test_req2: invalid amounts and overpayments are rejected and change nothing", async () => {
    const a = app();
    const id = await openInvoice(a, await customer(a), 10_000);
    for (const bad of [0, -100, 12.5, "100", null, undefined]) {
      const r = await pay(a, id, bad);
      expect([400, 422], `amount ${String(bad)} -> ${r.status}`).toContain(r.status);
    }
    const over = await pay(a, id, 10_001);
    expect([400, 409, 422], `overpayment -> ${over.status}`).toContain(over.status);
    expect(ok((await pay(a, id, 6_000)).status)).toBe(true);
    const over2 = await pay(a, id, 4_001);
    expect([400, 409, 422], `overpayment of the balance -> ${over2.status}`).toContain(over2.status);
    expect(await get(a, id)).toMatchObject({ amountPaid: 6_000, balance: 4_000, status: "open" });
  });

  it("test_req3: existing data stays consistent (legacy paid invoices, /pay, persisted payments)", async () => {
    const dir = mkdtempSync(join(tmpdir(), "flow-bench-"));
    const file = join(dir, "ledgerly.json");
    const line = (unitPrice: number) => [{ description: "Retainer", quantity: 1, unitPrice }];
    const base = { number: null, customerId: "cus_1", currency: "EUR", discount: 0, createdAt: "2026-01-05T10:00:00.000Z", dueDate: null, voidedAt: null };
    // A production file written by the current build (schemaVersion 1), before payments existed.
    writeFileSync(
      file,
      JSON.stringify({
        schemaVersion: 1,
        counters: { customer: 1, invoice: 3, invoiceNumber: 3 },
        customers: [{ id: "cus_1", name: "Acme", email: "billing@acme.io", createdAt: "2026-01-05T10:00:00.000Z" }],
        invoices: [
          { ...base, id: "inv_1", number: "INV-0001", lines: line(10_000), status: "open", issuedAt: "2026-01-06T10:00:00.000Z", paidAt: null },
          { ...base, id: "inv_2", number: "INV-0002", lines: line(5_000), status: "paid", issuedAt: "2026-01-06T10:00:00.000Z", paidAt: "2026-02-01T10:00:00.000Z" },
          { ...base, id: "inv_3", number: "INV-0003", lines: line(2_000), status: "void", issuedAt: "2026-01-06T10:00:00.000Z", paidAt: null, voidedAt: "2026-01-20T10:00:00.000Z" },
        ],
      }),
    );
    let a = app(openStore({ file }));
    expect(await get(a, "inv_2")).toMatchObject({ status: "paid", amountPaid: 5_000, balance: 0 });
    expect(await get(a, "inv_1")).toMatchObject({ status: "open", amountPaid: 0, balance: 10_000 });
    const report = await a.handle("GET", "/reports/outstanding");
    expect((report.body as { totals: Record<string, number> }).totals.EUR).toBe(10_000);

    // A partial payment survives a reload of the file.
    expect(ok((await pay(a, "inv_1", 3_000)).status)).toBe(true);
    a = app(openStore({ file }));
    expect(await get(a, "inv_1")).toMatchObject({ status: "open", amountPaid: 3_000, balance: 7_000 });
    expect(await get(a, "inv_2")).toMatchObject({ status: "paid", amountPaid: 5_000, balance: 0 });
    expect(JSON.parse(readFileSync(file, "utf8")).invoices.length).toBe(3);

    // The existing full-payment endpoint still works and leaves a consistent balance.
    const fresh = await openInvoice(a, "cus_1", 8_000);
    expect((await a.handle("POST", `/invoices/${fresh}/pay`)).status).toBe(200);
    expect(await get(a, fresh)).toMatchObject({ status: "paid", amountPaid: 8_000, balance: 0 });
  });

  it("test_req4: unknown invoices are 404, drafts and void invoices cannot take payments (409)", async () => {
    const a = app();
    const c = await customer(a);
    expect((await pay(a, "inv_404", 1_000)).status).toBe(404);
    const draft = await draftInvoice(a, c, 10_000);
    expect((await pay(a, draft, 1_000)).status).toBe(409);
    const voided = await openInvoice(a, c, 10_000);
    await a.handle("POST", `/invoices/${voided}/void`);
    expect((await pay(a, voided, 1_000)).status).toBe(409);
    expect(await get(a, draft)).toMatchObject({ status: "draft", amountPaid: 0 });
    expect(await get(a, voided)).toMatchObject({ status: "void", amountPaid: 0 });
  });

  it("test_req5: the change ships with tests in the repo suite that exercise payments", () => {
    const work = process.env.WORK as string;
    const base = process.env.BASE as string;
    const git = (...args: string[]) => execFileSync("git", ["-C", work, ...args], { encoding: "utf8" });
    const changed = git("diff", "--name-only", base, "--").split("\n");
    const untracked = git("ls-files", "--others", "--exclude-standard").split("\n");
    const tests = [...changed, ...untracked].filter((f) => /\.test\.ts$/.test(f) && !f.startsWith(".claude/"));
    const exercising = tests.filter((f) => {
      try {
        return /payments/.test(readFileSync(join(work, f), "utf8"));
      } catch {
        return false;
      }
    });
    expect(exercising.length, `test files touched: ${tests.join(", ") || "none"}`).toBeGreaterThan(0);
  });
});
