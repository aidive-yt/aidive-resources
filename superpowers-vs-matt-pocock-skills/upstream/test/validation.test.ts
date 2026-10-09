import { describe, expect, it } from "vitest";
import { parseNewCustomer } from "../src/domain/customer";
import { ValidationError } from "../src/domain/errors";
import { parseNewInvoice } from "../src/domain/validation";

const valid = {
  customerId: "cus_1",
  currency: "EUR",
  lines: [{ description: "Audit", quantity: 1, unitPrice: 20_000 }],
};

describe("parseNewInvoice", () => {
  it("parses a minimal invoice", () => {
    expect(parseNewInvoice(valid)).toEqual({ ...valid, discount: 0, dueDate: null });
  });

  it("requires at least one line", () => {
    expect(() => parseNewInvoice({ ...valid, lines: [] })).toThrow(ValidationError);
  });

  it("rejects fractional cents in unit prices", () => {
    expect(() => parseNewInvoice({ ...valid, lines: [{ description: "x", quantity: 1, unitPrice: 9.99 }] })).toThrow(
      /unitPrice/,
    );
  });

  it("rejects a discount above the subtotal", () => {
    expect(() => parseNewInvoice({ ...valid, discount: 20_001 })).toThrow(/discount cannot exceed/);
  });

  it("validates the currency and due date", () => {
    expect(() => parseNewInvoice({ ...valid, currency: "JPY" })).toThrow(/currency/);
    expect(() => parseNewInvoice({ ...valid, dueDate: "10/03/2026" })).toThrow(/dueDate/);
  });
});

describe("parseNewCustomer", () => {
  it("normalises the email", () => {
    expect(parseNewCustomer({ name: " Acme ", email: "Billing@Acme.io" })).toEqual({
      name: "Acme",
      email: "billing@acme.io",
    });
  });

  it("rejects a bad email", () => {
    expect(() => parseNewCustomer({ name: "Acme", email: "nope" })).toThrow(ValidationError);
  });
});
