import type { StoreData } from "./types";

export const CURRENT_SCHEMA_VERSION = 1;

type RawData = Record<string, unknown> & { schemaVersion?: number };
type Migration = (data: RawData) => RawData;

/**
 * v0 -> v1: invoices embedded the customer (`customer: { id, name }`); v1 stores `customerId` only.
 * Files written before schemaVersion existed are v0.
 */
const v0ToV1: Migration = (data) => {
  const invoices = (data.invoices as Record<string, unknown>[] | undefined) ?? [];
  return {
    ...data,
    schemaVersion: 1,
    invoices: invoices.map((inv) => {
      const { customer, ...rest } = inv as { customer?: { id: string } } & Record<string, unknown>;
      return customer ? { ...rest, customerId: customer.id } : rest;
    }),
  };
};

/** migrations[n] upgrades a file from version n to n + 1. */
const migrations: Record<number, Migration> = {
  0: v0ToV1,
};

export function migrate(raw: unknown): StoreData {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("store file is not a JSON object");
  }
  let data = raw as RawData;
  let version = data.schemaVersion ?? 0;
  if (version > CURRENT_SCHEMA_VERSION) {
    throw new Error(`store file schemaVersion ${version} is newer than this build (${CURRENT_SCHEMA_VERSION})`);
  }
  while (version < CURRENT_SCHEMA_VERSION) {
    const step = migrations[version];
    if (!step) throw new Error(`no migration from schemaVersion ${version}`);
    data = step(data);
    version = data.schemaVersion as number;
  }
  return {
    schemaVersion: CURRENT_SCHEMA_VERSION,
    counters: (data.counters as StoreData["counters"]) ?? { customer: 0, invoice: 0, invoiceNumber: 0 },
    customers: (data.customers as StoreData["customers"]) ?? [],
    invoices: (data.invoices as StoreData["invoices"]) ?? [],
  };
}
