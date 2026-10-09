import type { Store } from "../store/json-store";
import { customerRepo } from "../store/customer-repo";
import { invoiceRepo } from "../store/invoice-repo";

export type AppContext = {
  store: Store;
  now: () => Date;
  customers: ReturnType<typeof customerRepo>;
  invoices: ReturnType<typeof invoiceRepo>;
};

export function createContext(store: Store, now: () => Date = () => new Date()): AppContext {
  return { store, now, customers: customerRepo(store), invoices: invoiceRepo(store) };
}
