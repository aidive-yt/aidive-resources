import { ValidationError } from "./errors";

export const CURRENCIES = ["EUR", "USD", "GBP"] as const;
export type Currency = (typeof CURRENCIES)[number];

/** Amounts are integer cents. */
export type Cents = number;

export function isCurrency(value: unknown): value is Currency {
  return typeof value === "string" && (CURRENCIES as readonly string[]).includes(value);
}

export function assertCents(value: unknown, field: string, opts: { min?: number } = {}): Cents {
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new ValidationError(`${field} must be an integer number of cents`, field);
  }
  const min = opts.min ?? 0;
  if (value < min) {
    throw new ValidationError(`${field} must be >= ${min}`, field);
  }
  return value;
}

export function formatCents(amount: Cents, currency: Currency): string {
  const sign = amount < 0 ? "-" : "";
  const abs = Math.abs(amount);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, "0")} ${currency}`;
}

export function sum(amounts: Cents[]): Cents {
  return amounts.reduce((acc, a) => acc + a, 0);
}
