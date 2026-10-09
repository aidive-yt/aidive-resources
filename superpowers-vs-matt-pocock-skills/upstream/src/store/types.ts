import type { Customer } from "../domain/customer";
import type { Invoice } from "../domain/invoice";

export type Counters = { customer: number; invoice: number; invoiceNumber: number };

/** The shape of the JSON file at CURRENT_SCHEMA_VERSION. */
export type StoreData = {
  schemaVersion: number;
  counters: Counters;
  customers: Customer[];
  invoices: Invoice[];
};
