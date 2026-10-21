import { afterAll, beforeAll, describe, expect, it } from "vitest"
import { createServer, type ViteDevServer } from "vite"

describe("site icon", () => {
  let server: ViteDevServer
  let origin: string

  beforeAll(async () => {
    const projectRoot = decodeURIComponent(new URL("..", import.meta.url).pathname)
      .replace(/^\/([A-Za-z]:)/, "$1")
    server = await createServer({
      configFile: false,
      root: projectRoot,
      server: { host: "127.0.0.1", port: 0 },
    })
    await server.listen()
    const address = server.httpServer?.address()
    if (!address || typeof address === "string") throw new Error("Vite test server did not expose a TCP port")
    origin = `http://127.0.0.1:${address.port}`
  })

  afterAll(async () => {
    await server.close()
  })

  it("serves the branded SVG favicon referenced by the application entry point", async () => {
    const page = await fetch(origin)
    const html = await page.text()
    const iconPath = html.match(/<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="([^"]+)"/)?.[1]

    expect(iconPath).toBe("/favicon.svg")

    const icon = await fetch(`${origin}${iconPath}`)
    expect(icon.ok).toBe(true)
    expect(icon.headers.get("content-type")).toContain("image/svg+xml")
  })
})
