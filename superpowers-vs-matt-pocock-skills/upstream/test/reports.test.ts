import { describe, expect, it } from "vitest";
import { seedCustomer, seedOpenInvoice, testApp } from "./helpers";

describe("outstanding report", () => {
  it("sums open invoices per currency and counts overdue ones", async () => {
    const app = testApp();
    const customerId = await seedCustomer(app);
    await seedOpenInvoice(app, { customerId, unitPrice: 10_000, dueDate: "2026-03-01" });
    await seedOpenInvoice(app, { customerId, unitPrice: 2_500, currency: "USD" });
    const paid = await seedOpenInvoice(app, { customerId, unitPrice: 7_000 });
    await app.handle("POST", `/invoices/${paid}/pay`);
    const res = await app.handle("GET", "/reports/outstanding");
    expect(res.body).toEqual({ totals: { EUR: 10_000, USD: 2_500 }, count: 2, overdue: 1 });
  });

  it("ignores drafts and void invoices", async () => {
    const app = testApp();
    const customerId = await seedCustomer(app);
    const voided = await seedOpenInvoice(app, { customerId });
    await app.handle("POST", `/invoices/${voided}/void`);
    await app.handle("POST", "/invoices", {
      customerId,
      currency: "EUR",
      lines: [{ description: "Draft", quantity: 1, unitPrice: 999 }],
    });
    expect((await app.handle("GET", "/reports/outstanding")).body).toEqual({ totals: {}, count: 0, overdue: 0 });
  });
});
