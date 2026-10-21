// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App.vue"

const hasSession = vi.hoisted(() => vi.fn())

vi.mock("./api", () => ({
  api: {
    hasSession,
    me: vi.fn().mockResolvedValue({
      user_id: "admin",
      username: "admin",
      display_name: "系统管理员",
      role: "admin",
    }),
    schema: vi.fn().mockResolvedValue([]),
    memories: vi.fn().mockResolvedValue([]),
    clearSession: vi.fn(),
  },
}))

describe("desktop history sidebar", () => {
  beforeEach(() => {
    hasSession.mockReturnValue(true)
    vi.stubGlobal("crypto", { randomUUID: () => "conversation-1" })
  })

  it("collapses and expands from its accessible toggle", async () => {
    const wrapper = mount(App)
    await flushPromises()

    const layout = wrapper.get(".app-layout")
    const toggle = wrapper.get('button[aria-label="收起左侧栏"]')

    expect(layout.classes()).not.toContain("left-collapsed")
    expect(toggle.attributes("aria-expanded")).toBe("true")

    await toggle.trigger("click")

    expect(layout.classes()).toContain("left-collapsed")
    expect(wrapper.get('button[aria-label="展开左侧栏"]').attributes("aria-expanded")).toBe("false")

    await wrapper.get('button[aria-label="展开左侧栏"]').trigger("click")

    expect(layout.classes()).not.toContain("left-collapsed")
    expect(wrapper.get('button[aria-label="收起左侧栏"]').attributes("aria-expanded")).toBe("true")
  })
})

describe("product identity", () => {
  it("shows the DataPilot identity on the logged-out entry point", async () => {
    hasSession.mockReturnValue(false)
    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.get(".login-brand").text()).toBe("DDataPilot")
    expect(wrapper.get(".login-card header").text()).toContain("登录 DataPilot Studio")
  })
})
