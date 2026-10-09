import { parseNewCustomer } from "../../domain/customer";
import type { Router } from "../router";
import type { AppContext } from "../context";

export function customerRoutes(router: Router, ctx: AppContext): void {
  router.on("POST", "/customers", ({ body }) => {
    const input = parseNewCustomer(body);
    const id = `cus_${ctx.store.nextId("customer")}`;
    const customer = ctx.customers.insert({ id, ...input, createdAt: ctx.now().toISOString() });
    return { status: 201, body: customer };
  });

  router.on("GET", "/customers/:id", ({ params }) => ({ status: 200, body: ctx.customers.get(params.id) }));
}
