export class DomainError extends Error {
  constructor(message: string) {
    super(message);
    this.name = new.target.name;
  }
}

/** Input that can never be valid (bad shape, out of range). Maps to HTTP 400. */
export class ValidationError extends DomainError {
  constructor(
    message: string,
    readonly field?: string,
  ) {
    super(message);
  }
}

/** A record that does not exist. Maps to HTTP 404. */
export class NotFoundError extends DomainError {
  constructor(entity: string, id: string) {
    super(`${entity} ${id} not found`);
  }
}

/** A valid request that the current state forbids (e.g. paying a void invoice). Maps to HTTP 409. */
export class ConflictError extends DomainError {}
