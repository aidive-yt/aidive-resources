import { computeTotals, isOverdue } from "../../domain/invoice";
import type { Currency } from "../../domain/money";
import type { AppContext } from "../context";
import type { Router } from "../router";

export function reportRoutes(router: Router, ctx: AppContext): void {
  /** What customers still owe us, per currency, over every open invoice. */
  router.on("GET", "/reports/outstanding", () => {
    const now = ctx.now();
    const totals: Partial<Record<Currency, number>> = {};
    let count = 0;
    let overdue = 0;
    for (const invoice of ctx.invoices.list({ status: "open" })) {
      const { total } = computeTotals(invoice);
      totals[invoice.currency] = (totals[invoice.currency] ?? 0) + total;
      count += 1;
      if (isOverdue(invoice, now)) overdue += 1;
    }
    return { status: 200, body: { totals, count, overdue } };
  });
}
