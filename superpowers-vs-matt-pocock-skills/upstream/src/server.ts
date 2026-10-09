import { createServer } from "node:http";
import { createApp } from "./http/app";
import { openStore } from "./store/json-store";

const file = process.env.LEDGERLY_DATA ?? "data/ledgerly.json";
const app = createApp({ store: openStore({ file }) });

createServer(async (req, res) => {
  let raw = "";
  for await (const chunk of req) raw += chunk;
  let body: unknown;
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      res.writeHead(400, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { code: "bad_json", message: "body is not valid JSON" } }));
      return;
    }
  }
  const out = await app.handle(req.method ?? "GET", req.url ?? "/", body);
  res.writeHead(out.status, { "content-type": "application/json" });
  res.end(JSON.stringify(out.body));
}).listen(Number(process.env.PORT ?? 3000));
