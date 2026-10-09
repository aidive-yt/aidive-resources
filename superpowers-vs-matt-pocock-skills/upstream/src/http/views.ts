import { computeTotals, type Invoice } from "../domain/invoice";

/** The JSON shape returned for an invoice: stored fields plus computed totals. */
export function invoiceView(invoice: Invoice) {
  return { ...invoice, ...computeTotals(invoice) };
}
