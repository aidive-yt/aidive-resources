import { ValidationError } from "./errors";

export type Customer = {
  id: string;
  name: string;
  email: string;
  createdAt: string;
};

export type NewCustomerInput = { name: string; email: string };

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function parseNewCustomer(body: unknown): NewCustomerInput {
  if (typeof body !== "object" || body === null) {
    throw new ValidationError("body must be an object");
  }
  const { name, email } = body as Record<string, unknown>;
  if (typeof name !== "string" || name.trim() === "") {
    throw new ValidationError("name is required", "name");
  }
  if (typeof email !== "string" || !EMAIL.test(email)) {
    throw new ValidationError("email is invalid", "email");
  }
  return { name: name.trim(), email: email.toLowerCase() };
}
