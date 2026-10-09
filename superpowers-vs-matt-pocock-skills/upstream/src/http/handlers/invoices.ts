import { ValidationError } from "../../domain/errors";
import { type Invoice, type InvoiceStatus, issue, markPaid, voidInvoice } from "../../domain/invoice";
import { parseNewInvoice } from "../../domain/validation";
import type { AppContext } from "../context";
import type { Router } from "../router";
import { invoiceView } from "../views";

const STATUSES: InvoiceStatus[] = ["draft", "open", "paid", "void"];

export function invoiceRoutes(router: Router, ctx: AppContext): void {
  router.on("POST", "/invoices", ({ body }) => {
    const input = parseNewInvoice(body);
    if (!ctx.customers.exists(input.customerId)) {
      throw new ValidationError(`customer ${input.customerId} does not exist`, "customerId");
    }
    const invoice: Invoice = {
      id: `inv_${ctx.store.nextId("invoice")}`,
      number: null,
      ...input,
      status: "draft",
      createdAt: ctx.now().toISOString(),
      issuedAt: null,
      paidAt: null,
      voidedAt: null,
    };
    return { status: 201, body: invoiceView(ctx.invoices.insert(invoice)) };
  });

  router.on("GET", "/invoices", ({ query }) => {
    const status = query.get("status") ?? undefined;
    if (status !== undefined && !STATUSES.includes(status as InvoiceStatus)) {
      throw new ValidationError(`unknown status ${status}`, "status");
    }
    const customerId = query.get("customerId") ?? undefined;
    const list = ctx.invoices.list({ status: status as InvoiceStatus | undefined, customerId });
    return { status: 200, body: list.map(invoiceView) };
  });

  router.on("GET", "/invoices/:id", ({ params }) => ({ status: 200, body: invoiceView(ctx.invoices.get(params.id)) }));

  router.on("POST", "/invoices/:id/issue", ({ params }) => {
    const current = ctx.invoices.get(params.id);
    const n = ctx.store.nextId("invoiceNumber");
    const issued = issue(current, `INV-${String(n).padStart(4, "0")}`, ctx.now());
    return { status: 200, body: invoiceView(ctx.invoices.save(issued)) };
  });

  /** Marks an open invoice as paid in full (bank reconciliation does this today). */
  router.on("POST", "/invoices/:id/pay", ({ params }) => {
    const paid = markPaid(ctx.invoices.get(params.id), ctx.now());
    return { status: 200, body: invoiceView(ctx.invoices.save(paid)) };
  });

  router.on("POST", "/invoices/:id/void", ({ params }) => {
    const voided = voidInvoice(ctx.invoices.get(params.id), ctx.now());
    return { status: 200, body: invoiceView(ctx.invoices.save(voided)) };
  });
}
