import { ConflictError } from "./errors";
import { type Cents, type Currency, sum } from "./money";

export type InvoiceStatus = "draft" | "open" | "paid" | "void";

export type LineItem = {
  description: string;
  quantity: number;
  /** cents */
  unitPrice: Cents;
};

export type Invoice = {
  id: string;
  /** Assigned when the invoice is issued (INV-0001, ...). */
  number: string | null;
  customerId: string;
  currency: Currency;
  lines: LineItem[];
  /** Flat discount in cents, never above the subtotal. */
  discount: Cents;
  status: InvoiceStatus;
  createdAt: string;
  issuedAt: string | null;
  dueDate: string | null;
  paidAt: string | null;
  voidedAt: string | null;
};

export type InvoiceTotals = { subtotal: Cents; discount: Cents; total: Cents };

export function lineTotal(line: LineItem): Cents {
  return line.quantity * line.unitPrice;
}

export function computeTotals(invoice: Pick<Invoice, "lines" | "discount">): InvoiceTotals {
  const subtotal = sum(invoice.lines.map(lineTotal));
  return { subtotal, discount: invoice.discount, total: subtotal - invoice.discount };
}

export function issue(invoice: Invoice, number: string, now: Date): Invoice {
  if (invoice.status !== "draft") {
    throw new ConflictError(`invoice ${invoice.id} is ${invoice.status}, only drafts can be issued`);
  }
  return { ...invoice, status: "open", number, issuedAt: now.toISOString() };
}

export function markPaid(invoice: Invoice, now: Date): Invoice {
  if (invoice.status !== "open") {
    throw new ConflictError(`invoice ${invoice.id} is ${invoice.status}, only open invoices can be paid`);
  }
  return { ...invoice, status: "paid", paidAt: now.toISOString() };
}

export function voidInvoice(invoice: Invoice, now: Date): Invoice {
  if (invoice.status === "paid" || invoice.status === "void") {
    throw new ConflictError(`invoice ${invoice.id} is ${invoice.status} and cannot be voided`);
  }
  return { ...invoice, status: "void", voidedAt: now.toISOString() };
}

export function isOverdue(invoice: Invoice, now: Date): boolean {
  return invoice.status === "open" && invoice.dueDate !== null && invoice.dueDate < now.toISOString().slice(0, 10);
}
