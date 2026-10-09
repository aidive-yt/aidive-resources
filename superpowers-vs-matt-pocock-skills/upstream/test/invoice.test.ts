import { describe, expect, it } from "vitest";
import { ConflictError } from "../src/domain/errors";
import { computeTotals, type Invoice, isOverdue, issue, markPaid, voidInvoice } from "../src/domain/invoice";

const NOW = new Date("2026-03-10T09:00:00.000Z");

function draft(overrides: Partial<Invoice> = {}): Invoice {
  return {
    id: "inv_1",
    number: null,
    customerId: "cus_1",
    currency: "EUR",
    lines: [
      { description: "Design", quantity: 2, unitPrice: 5_000 },
      { description: "Hosting", quantity: 1, unitPrice: 1_500 },
    ],
    discount: 500,
    status: "draft",
    createdAt: NOW.toISOString(),
    issuedAt: null,
    dueDate: null,
    paidAt: null,
    voidedAt: null,
    ...overrides,
  };
}

describe("invoice domain", () => {
  it("computes totals", () => {
    expect(computeTotals(draft())).toEqual({ subtotal: 11_500, discount: 500, total: 11_000 });
  });

  it("issues a draft without mutating it", () => {
    const d = draft();
    const issued = issue(d, "INV-0001", NOW);
    expect(issued.status).toBe("open");
    expect(issued.number).toBe("INV-0001");
    expect(d.status).toBe("draft");
  });

  it("refuses to issue twice", () => {
    expect(() => issue(draft({ status: "open" }), "INV-0002", NOW)).toThrow(ConflictError);
  });

  it("marks an open invoice paid", () => {
    const paid = markPaid(draft({ status: "open" }), NOW);
    expect(paid.status).toBe("paid");
    expect(paid.paidAt).toBe(NOW.toISOString());
  });

  it("refuses to pay drafts and void invoices", () => {
    expect(() => markPaid(draft(), NOW)).toThrow(ConflictError);
    expect(() => markPaid(draft({ status: "void" }), NOW)).toThrow(ConflictError);
  });

  it("voids drafts and open invoices, never paid ones", () => {
    expect(voidInvoice(draft(), NOW).status).toBe("void");
    expect(() => voidInvoice(draft({ status: "paid" }), NOW)).toThrow(ConflictError);
  });

  it("knows when an open invoice is overdue", () => {
    expect(isOverdue(draft({ status: "open", dueDate: "2026-03-01" }), NOW)).toBe(true);
    expect(isOverdue(draft({ status: "open", dueDate: "2026-04-01" }), NOW)).toBe(false);
    expect(isOverdue(draft({ status: "paid", dueDate: "2026-03-01" }), NOW)).toBe(false);
  });
});
