import type { Customer } from "../domain/customer";
import { NotFoundError } from "../domain/errors";
import type { Store } from "./json-store";

export function customerRepo(store: Store) {
  return {
    get(id: string): Customer {
      const found = store.read().customers.find((c) => c.id === id);
      if (!found) throw new NotFoundError("customer", id);
      return found;
    },
    exists(id: string): boolean {
      return store.read().customers.some((c) => c.id === id);
    },
    insert(customer: Customer): Customer {
      store.update((d) => ({ ...d, customers: [...d.customers, customer] }));
      return customer;
    },
  };
}
