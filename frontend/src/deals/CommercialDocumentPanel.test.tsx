import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getTradePack } from "../api/client";
import type { AgreementVersion } from "../api/types";
import CommercialDocumentPanel from "./CommercialDocumentPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return { ...actual, getTradePack: vi.fn() };
});

const agreement = { id: "version-1", deal_id: "deal-1", version_number: 2,
  terms_hash: "a".repeat(64), status: "COMMITTED" } as AgreementVersion;
const props = { dealId: "deal-1", organizationId: "buyer", agreement, contextKey: "snapshot-1" };
const createObjectURL = vi.fn(() => "blob:trade-pack");
const revokeObjectURL = vi.fn();

describe("CommercialDocumentPanel", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", class extends URL {
      static createObjectURL = createObjectURL;
      static revokeObjectURL = revokeObjectURL;
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it.each(["zip", "html"] as const)("downloads %s for the exact snapshot without injecting HTML", async (format) => {
    vi.mocked(getTradePack).mockResolvedValue(new Blob(['<script>alert(1)</script>'], { type: "text/html" }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe(`syncally-deal-deal-1-agreement-v2-trade-pack.${format}`);
    });
    render(<CommercialDocumentPanel {...props} />);
    fireEvent.change(screen.getByLabelText("Document format"), { target: { value: format } });
    fireEvent.click(screen.getByRole("button", { name: "Download trade pack" }));
    await waitFor(() => expect(click).toHaveBeenCalledOnce());
    expect(getTradePack).toHaveBeenCalledWith("deal-1", agreement, "buyer", format, expect.any(AbortSignal));
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("a[download]")).toBeNull();
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith("blob:trade-pack"));
  });

  it.each(["party", "deal", "version", "hash", "reload", "unmount"])("aborts and discards stale downloads after %s changes", async (change) => {
    let resolve!: (value: Blob) => void;
    vi.mocked(getTradePack).mockReturnValue(new Promise((done) => { resolve = done; }));
    const view = render(<CommercialDocumentPanel {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Download trade pack" }));
    const signal = vi.mocked(getTradePack).mock.calls[0][4]!;
    if (change === "unmount") view.unmount();
    else view.rerender(<CommercialDocumentPanel {...props}
      dealId={change === "deal" ? "deal-2" : props.dealId}
      organizationId={change === "party" ? "seller" : "buyer"}
      contextKey={change === "reload" ? "snapshot-2" : props.contextKey}
      agreement={{ ...agreement, id: change === "version" ? "version-2" : agreement.id,
        terms_hash: change === "hash" ? "b".repeat(64) : agreement.terms_hash }} />);
    expect(signal.aborted).toBe(true);
    await act(async () => { resolve(new Blob(["late"])); });
    expect(createObjectURL).not.toHaveBeenCalled();
  });

  it("preserves errors and permits retry without changing version", async () => {
    vi.mocked(getTradePack).mockRejectedValueOnce(new ApiError(409, "Unapproved version"));
    render(<CommercialDocumentPanel {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Download trade pack" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unapproved version");
    vi.mocked(getTradePack).mockRejectedValueOnce(new ApiError(413, "Too large"));
    fireEvent.click(screen.getByRole("button", { name: "Download trade pack" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Too large"));
  });
});
