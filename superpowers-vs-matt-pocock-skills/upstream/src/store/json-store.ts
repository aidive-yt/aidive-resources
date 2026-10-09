import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { CURRENT_SCHEMA_VERSION, migrate } from "./migrations";
import type { Counters, StoreData } from "./types";

export type Store = {
  read(): StoreData;
  /** Apply a change and persist it (when file-backed). */
  update(change: (data: StoreData) => StoreData): StoreData;
  nextId(kind: keyof Counters): number;
};

function empty(): StoreData {
  return {
    schemaVersion: CURRENT_SCHEMA_VERSION,
    counters: { customer: 0, invoice: 0, invoiceNumber: 0 },
    customers: [],
    invoices: [],
  };
}

/**
 * Open the store. With `file`, the JSON file is loaded and migrated to the current schema
 * (and written back if a migration ran); every update is persisted with an atomic rename.
 * Without `file`, the store is in memory (tests).
 */
export function openStore(opts: { file?: string } = {}): Store {
  const { file } = opts;
  let data: StoreData = empty();
  if (file && existsSync(file)) {
    const raw = JSON.parse(readFileSync(file, "utf8"));
    data = migrate(raw);
    if (raw.schemaVersion !== data.schemaVersion) persist(file, data);
  }

  function persist(path: string, value: StoreData): void {
    mkdirSync(dirname(path), { recursive: true });
    const tmp = `${path}.tmp`;
    writeFileSync(tmp, JSON.stringify(value, null, 2));
    renameSync(tmp, path);
  }

  return {
    read: () => data,
    update(change) {
      data = change(data);
      if (file) persist(file, data);
      return data;
    },
    nextId(kind) {
      let n = 0;
      this.update((d) => {
        n = d.counters[kind] + 1;
        return { ...d, counters: { ...d.counters, [kind]: n } };
      });
      return n;
    },
  };
}
