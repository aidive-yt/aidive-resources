import { ValidationError } from "./errors";
import { computeTotals, type LineItem } from "./invoice";
import { assertCents, type Currency, isCurrency } from "./money";

export type NewInvoiceInput = {
  customerId: string;
  currency: Currency;
  lines: LineItem[];
  discount: number;
  dueDate: string | null;
};

const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function parseLineItems(value: unknown): LineItem[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new ValidationError("lines must be a non-empty array", "lines");
  }
  return value.map((raw, i) => {
    if (typeof raw !== "object" || raw === null) {
      throw new ValidationError(`lines[${i}] must be an object`, `lines[${i}]`);
    }
    const { description, quantity, unitPrice } = raw as Record<string, unknown>;
    if (typeof description !== "string" || description.trim() === "") {
      throw new ValidationError(`lines[${i}].description is required`, `lines[${i}].description`);
    }
    if (typeof quantity !== "number" || !Number.isInteger(quantity) || quantity < 1) {
      throw new ValidationError(`lines[${i}].quantity must be a positive integer`, `lines[${i}].quantity`);
    }
    return { description: description.trim(), quantity, unitPrice: assertCents(unitPrice, `lines[${i}].unitPrice`) };
  });
}

export function parseNewInvoice(body: unknown): NewInvoiceInput {
  if (typeof body !== "object" || body === null) {
    throw new ValidationError("body must be an object");
  }
  const b = body as Record<string, unknown>;
  if (typeof b.customerId !== "string" || b.customerId === "") {
    throw new ValidationError("customerId is required", "customerId");
  }
  if (!isCurrency(b.currency)) {
    throw new ValidationError("currency must be one of EUR, USD, GBP", "currency");
  }
  const lines = parseLineItems(b.lines);
  const discount = b.discount === undefined ? 0 : assertCents(b.discount, "discount");
  const { subtotal } = computeTotals({ lines, discount: 0 });
  if (discount > subtotal) {
    throw new ValidationError("discount cannot exceed the subtotal", "discount");
  }
  let dueDate: string | null = null;
  if (b.dueDate !== undefined && b.dueDate !== null) {
    if (typeof b.dueDate !== "string" || !DATE.test(b.dueDate)) {
      throw new ValidationError("dueDate must be YYYY-MM-DD", "dueDate");
    }
    dueDate = b.dueDate;
  }
  return { customerId: b.customerId, currency: b.currency, lines, discount, dueDate };
}
