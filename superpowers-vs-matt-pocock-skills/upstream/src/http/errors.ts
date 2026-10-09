import { ConflictError, NotFoundError, ValidationError } from "../domain/errors";
import type { Response } from "./router";

export function errorResponse(err: unknown): Response {
  if (err instanceof ValidationError) {
    return { status: 400, body: { error: { code: "validation_error", message: err.message, field: err.field } } };
  }
  if (err instanceof NotFoundError) {
    return { status: 404, body: { error: { code: "not_found", message: err.message } } };
  }
  if (err instanceof ConflictError) {
    return { status: 409, body: { error: { code: "conflict", message: err.message } } };
  }
  return { status: 500, body: { error: { code: "internal", message: "internal error" } } };
}
