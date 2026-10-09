import { describe, expect, it } from "vitest";
import { seedCustomer, seedOpenInvoice, testApp } from "./helpers";

describe("invoices API", () => {
  it("creates a draft with computed totals", async () => {
    const app = testApp();
    const customerId = await seedCustomer(app);
    const res = await app.handle("POST", "/invoices", {
      customerId,
      currency: "EUR",
      lines: [{ description: "Audit", quantity: 3, unitPrice: 1_000 }],
      discount: 500,
    });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({ status: "draft", number: null, subtotal: 3_000, discount: 500, total: 2_500 });
  });

  it("rejects an invoice for an unknown customer", async () => {
    const app = testApp();
    const res = await app.handle("POST", "/invoices", {
      customerId: "cus_9",
      currency: "EUR",
      lines: [{ description: "Audit", quantity: 1, unitPrice: 1_000 }],
    });
    expect(res).toMatchObject({ status: 400, body: { error: { code: "validation_error", field: "customerId" } } });
  });

  it("issues with sequential numbers", async () => {
    const app = testApp();
    const customerId = await seedCustomer(app);
    const a = await seedOpenInvoice(app, { customerId });
    const b = await seedOpenInvoice(app, { customerId });
    expect((await app.handle("GET", `/invoices/${a}`)).body).toMatchObject({ status: "open", number: "INV-0001" });
    expect((await app.handle("GET", `/invoices/${b}`)).body).toMatchObject({ number: "INV-0002" });
  });

  it("marks an open invoice paid in full", async () => {
    const app = testApp();
    const id = await seedOpenInvoice(app, { customerId: await seedCustomer(app) });
    const res = await app.handle("POST", `/invoices/${id}/pay`);
    expect(res).toMatchObject({ status: 200, body: { status: "paid", paidAt: "2026-03-10T09:00:00.000Z" } });
  });

  it("returns 409 when paying a void invoice and 404 for unknown invoices", async () => {
    const app = testApp();
    const id = await seedOpenInvoice(app, { customerId: await seedCustomer(app) });
    await app.handle("POST", `/invoices/${id}/void`);
    expect((await app.handle("POST", `/invoices/${id}/pay`)).status).toBe(409);
    expect((await app.handle("POST", "/invoices/inv_404/pay")).status).toBe(404);
  });

  it("filters the list by status and rejects unknown statuses", async () => {
    const app = testApp();
    const customerId = await seedCustomer(app);
    const id = await seedOpenInvoice(app, { customerId });
    await seedOpenInvoice(app, { customerId });
    await app.handle("POST", `/invoices/${id}/pay`);
    const paid = await app.handle("GET", "/invoices?status=paid");
    expect((paid.body as unknown[]).length).toBe(1);
    expect((await app.handle("GET", "/invoices?status=late")).status).toBe(400);
  });

  it("returns 404 for unknown routes", async () => {
    expect((await testApp().handle("DELETE", "/invoices")).status).toBe(404);
  });
});
