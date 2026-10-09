import { createApp } from "../src/http/app";
import { openStore, type Store } from "../src/store/json-store";

export const NOW = new Date("2026-03-10T09:00:00.000Z");

export function testApp(store: Store = openStore()) {
  return createApp({ store, now: () => NOW });
}

type App = ReturnType<typeof testApp>;

export async function seedCustomer(app: App, name = "Acme"): Promise<string> {
  const res = await app.handle("POST", "/customers", { name, email: `${name.toLowerCase()}@example.com` });
  return (res.body as { id: string }).id;
}

/** Creates and issues an invoice; returns its id. Total = sum(qty * unitPrice) - discount. */
export async function seedOpenInvoice(
  app: App,
  opts: { customerId: string; unitPrice?: number; quantity?: number; discount?: number; currency?: string; dueDate?: string },
): Promise<string> {
  const created = await app.handle("POST", "/invoices", {
    customerId: opts.customerId,
    currency: opts.currency ?? "EUR",
    lines: [{ description: "Consulting", quantity: opts.quantity ?? 1, unitPrice: opts.unitPrice ?? 10_000 }],
    discount: opts.discount,
    dueDate: opts.dueDate,
  });
  const id = (created.body as { id: string }).id;
  await app.handle("POST", `/invoices/${id}/issue`);
  return id;
}
