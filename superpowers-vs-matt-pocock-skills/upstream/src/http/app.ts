import { openStore, type Store } from "../store/json-store";
import { createContext } from "./context";
import { errorResponse } from "./errors";
import { customerRoutes } from "./handlers/customers";
import { invoiceRoutes } from "./handlers/invoices";
import { reportRoutes } from "./handlers/reports";
import { type Response, Router } from "./router";

export type App = {
  handle(method: string, url: string, body?: unknown): Promise<Response>;
};

export function createApp(opts: { store?: Store; now?: () => Date } = {}): App {
  const ctx = createContext(opts.store ?? openStore(), opts.now);
  const router = new Router();
  customerRoutes(router, ctx);
  invoiceRoutes(router, ctx);
  reportRoutes(router, ctx);

  return {
    async handle(method, url, body) {
      const parsed = new URL(url, "http://local");
      const match = router.match(method, parsed.pathname);
      if (!match) return { status: 404, body: { error: { code: "not_found", message: `no route ${method} ${parsed.pathname}` } } };
      try {
        return await match.handler({
          method: method as "GET",
          path: parsed.pathname,
          params: match.params,
          query: parsed.searchParams,
          body,
        });
      } catch (err) {
        return errorResponse(err);
      }
    },
  };
}
