import { describe, expect, it } from "vitest";
import { testApp } from "./helpers";

describe("customers API", () => {
  it("creates and fetches a customer", async () => {
    const app = testApp();
    const created = await app.handle("POST", "/customers", { name: "Acme", email: "billing@acme.io" });
    expect(created.status).toBe(201);
    const id = (created.body as { id: string }).id;
    const fetched = await app.handle("GET", `/customers/${id}`);
    expect(fetched).toMatchObject({ status: 200, body: { id, name: "Acme" } });
  });

  it("returns 400 on invalid input and 404 on unknown ids", async () => {
    const app = testApp();
    expect((await app.handle("POST", "/customers", { name: "" })).status).toBe(400);
    expect((await app.handle("GET", "/customers/cus_404")).status).toBe(404);
  });
});
