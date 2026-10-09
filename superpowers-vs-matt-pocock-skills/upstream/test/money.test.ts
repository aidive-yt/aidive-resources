import { describe, expect, it } from "vitest";
import { ValidationError } from "../src/domain/errors";
import { assertCents, formatCents, isCurrency, sum } from "../src/domain/money";

describe("money", () => {
  it("accepts integer cents", () => {
    expect(assertCents(1250, "amount")).toBe(1250);
  });

  it("rejects floats and strings", () => {
    expect(() => assertCents(12.5, "amount")).toThrow(ValidationError);
    expect(() => assertCents("12", "amount")).toThrow(ValidationError);
  });

  it("enforces the minimum", () => {
    expect(() => assertCents(0, "amount", { min: 1 })).toThrow(/>= 1/);
  });

  it("formats cents", () => {
    expect(formatCents(123456, "EUR")).toBe("1234.56 EUR");
    expect(formatCents(-5, "USD")).toBe("-0.05 USD");
  });

  it("knows its currencies and sums", () => {
    expect(isCurrency("GBP")).toBe(true);
    expect(isCurrency("JPY")).toBe(false);
    expect(sum([1, 2, 3])).toBe(6);
  });
});
