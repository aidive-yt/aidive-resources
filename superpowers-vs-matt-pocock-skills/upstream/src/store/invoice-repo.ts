import { NotFoundError } from "../domain/errors";
import type { Invoice, InvoiceStatus } from "../domain/invoice";
import type { Store } from "./json-store";

export function invoiceRepo(store: Store) {
  return {
    get(id: string): Invoice {
      const found = store.read().invoices.find((i) => i.id === id);
      if (!found) throw new NotFoundError("invoice", id);
      return found;
    },
    list(filter: { status?: InvoiceStatus; customerId?: string } = {}): Invoice[] {
      return store
        .read()
        .invoices.filter((i) => (filter.status ? i.status === filter.status : true))
        .filter((i) => (filter.customerId ? i.customerId === filter.customerId : true));
    },
    insert(invoice: Invoice): Invoice {
      store.update((d) => ({ ...d, invoices: [...d.invoices, invoice] }));
      return invoice;
    },
    save(invoice: Invoice): Invoice {
      store.update((d) => ({ ...d, invoices: d.invoices.map((i) => (i.id === invoice.id ? invoice : i)) }));
      return invoice;
    },
  };
}
