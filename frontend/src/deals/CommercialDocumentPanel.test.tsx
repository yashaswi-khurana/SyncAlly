import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getCommercialDocumentDraft } from "../api/client";
import CommercialDocumentPanel from "./CommercialDocumentPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return { ...actual, getCommercialDocumentDraft: vi.fn() };
});

const mockedGetDraft = vi.mocked(getCommercialDocumentDraft);

describe("CommercialDocumentPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows loading and unavailable states", async () => {
    mockedGetDraft.mockReturnValue(new Promise(() => {}));
    const { rerender } = render(<CommercialDocumentPanel dealId="deal-1" />);
    expect(screen.getByRole("status")).toHaveTextContent(/checking document availability/i);

    mockedGetDraft.mockRejectedValue(new ApiError(409, "Agreement not committed"));
    rerender(<CommercialDocumentPanel dealId="deal-2" />);

    expect(await screen.findByText(/available after both parties commit/i)).toBeInTheDocument();
  });

  it("offers a download for the committed agreement draft", async () => {
    mockedGetDraft.mockResolvedValue({
      agreement_version_id: "version-1",
      agreement_version_number: 2,
      terms_hash: "hash",
      content: "SYNCALLY - COMMERCIAL TRADE SUMMARY",
    });
    const createObjectURL = vi.fn(() => "blob:trade-summary");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });

    render(<CommercialDocumentPanel dealId="deal-1" />);

    expect(await screen.findByText(/committed agreement version 2/i)).toBeInTheDocument();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    fireEvent.click(screen.getByRole("button", { name: "Download trade summary" }));
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(document.querySelector("a[download*='agreement-v2-draft.txt']")).toBeNull();
    clickSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("shows retryable errors", async () => {
    mockedGetDraft.mockRejectedValueOnce(new ApiError(503, "Service unavailable"));

    render(<CommercialDocumentPanel dealId="deal-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/trade summary is unavailable/i);
    mockedGetDraft.mockResolvedValueOnce({
      agreement_version_id: "version-1",
      agreement_version_number: 1,
      terms_hash: "hash",
      content: "draft",
    });
    fireEvent.click(screen.getByRole("button", { name: "Refresh document" }));
    expect(await screen.findByText(/committed agreement version 1/i)).toBeInTheDocument();
  });
});
