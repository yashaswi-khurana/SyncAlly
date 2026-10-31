import { describe, expect, it } from "vitest";

import {
  dealPath,
  invitePath,
  organizationsPath,
  parseRoute,
} from "./router";

describe("router", () => {
  it("parses deals route for empty or root hash", () => {
    expect(parseRoute("")).toEqual({ name: "deals" });
    expect(parseRoute("#")).toEqual({ name: "deals" });
    expect(parseRoute("#/deals")).toEqual({ name: "deals" });
  });

  it("parses create deal route", () => {
    expect(parseRoute("#/deals/new")).toEqual({ name: "create" });
  });

  it("parses deal detail route with deal ID", () => {
    expect(parseRoute("#/deals/deal-123")).toEqual({
      name: "deal",
      dealId: "deal-123",
    });
  });

  it("parses organizations settings route", () => {
    expect(parseRoute("#/settings/organizations")).toEqual({
      name: "organizations",
      inviteToken: undefined,
      dealId: undefined,
    });
  });

  it("parses invite route with token query parameter into organizations route", () => {
    const route = parseRoute("#/invite?token=test-token-value");
    expect(route).toEqual({
      name: "organizations",
      inviteToken: "test-token-value",
      dealId: undefined,
    });
  });

  it("parses invite route with token and dealId query parameters", () => {
    const route = parseRoute("#/invite?token=test-token-value&dealId=deal-abc");
    expect(route).toEqual({
      name: "organizations",
      inviteToken: "test-token-value",
      dealId: "deal-abc",
    });
  });

  it("generates correct invite path", () => {
    expect(invitePath("signed-token")).toBe("#/invite?token=signed-token");
    expect(invitePath("signed-token", "deal-xyz")).toBe(
      "#/invite?token=signed-token&dealId=deal-xyz",
    );
  });

  it("generates correct paths for navigation helpers", () => {
    expect(dealPath("deal-1")).toBe("#/deals/deal-1");
    expect(organizationsPath()).toBe("#/settings/organizations");
  });
});

