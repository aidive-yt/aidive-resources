import { describe, expect, it } from "vitest";
import { seedCustomer, seedOpenInvoice, testApp } from "./helpers";

describe("credit note numbering", () => {
  it("does not burn a number on a rejected request", async () => {
    const app = testApp();
    const customerId = await seedCustomer(app);
    const id = await seedOpenInvoice(app, { customerId, unitPrice: 10_000 });
    await app.handle("POST", `/invoices/${id}/pay`);
    const url = `/invoices/${id}/credit-notes`;

    const first = await app.handle("POST", url, { amount: 4_000 });
    expect(first.body).toMatchObject({ number: "CN-0001" });

    const rejected = await app.handle("POST", url, { amount: 6_001 });
    expect(rejected.status).not.toBe(201);

    const next = await app.handle("POST", url, { amount: 6_000 });
    expect(next.status).toBe(201);
    expect(next.body).toMatchObject({ number: "CN-0002" });
  });
});
