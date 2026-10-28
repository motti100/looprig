/** HTTP wrapper for react-research-brief. Run: npx tsx server.ts
 *
 * POST /run   {"task": "..."}                       -> {"answer": "...", "tokens": 123}
 * GET  /health
 */
import http from "node:http";
import { control, run, usedTokens } from "./agent.js";

const API_TOKEN = process.env.AGENT_API_TOKEN;
const ALLOW_RISKY = process.env.ALLOW_RISKY_TOOLS === "1";
const PORT = Number(process.env.PORT ?? 8000);

// There is no terminal to ask in, so approval prompts are off. To stay safe, tools that can act
// (write files, run code, MCP servers) are removed unless you opt in with ALLOW_RISKY_TOOLS=1.
control.setApproval("none");
const ready: Promise<void> = ALLOW_RISKY ? Promise.resolve() : control.dropRisky();

let busy: Promise<unknown> = Promise.resolve(); // the agent keeps token counters in module state, so run one request at a time

function readJson(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (c) => {
      body += c;
      if (body.length > 1_000_000) reject(new Error("body too large"));
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch (e) {
        reject(e);
      }
    });
  });
}

function send(res: http.ServerResponse, code: number, data: unknown) {
  res.writeHead(code, { "content-type": "application/json" });
  res.end(JSON.stringify(data));
}

http
  .createServer(async (req, res) => {
    try {
      await ready;
      if (req.method === "GET" && req.url === "/health") return send(res, 200, { ok: true, tools: control.tools.map((t: any) => t.name) });
      if (API_TOKEN && req.headers.authorization !== "Bearer " + API_TOKEN) return send(res, 401, { error: "missing or wrong bearer token" });
      if (req.method === "POST" && req.url === "/run") {
        const { task } = await readJson(req);
        if (!task) return send(res, 400, { error: "task is required" });
        const job = busy.then(async () => {
          control.reset();
          return { answer: await run(task), tokens: usedTokens() };
        });
        busy = job.catch(() => undefined);
        return send(res, 200, await job);
      }
      send(res, 404, { error: "not found" });
    } catch (e: any) {
      send(res, 500, { error: String(e?.message ?? e) });
    }
  })
  .listen(PORT, () => console.log("listening on :" + PORT));
