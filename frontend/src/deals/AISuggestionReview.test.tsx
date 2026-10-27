import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createDealFact,
  correctDealFact,
  reviewDealFact,
  suggestDealFacts,
} from "../api/client";
import type { DealFact } from "../api/types";
import AISuggestionReview from "./AISuggestionReview";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    createDealFact: vi.fn(),
    correctDealFact: vi.fn(),
    createAgreementFromReviewedTerms: vi.fn(),
    draftDealProposal: vi.fn(),
    reviewDealFact: vi.fn(),
    suggestDealFacts: vi.fn(),
  };
});

const DEAL_ID = "deal-1";
const ORGANIZATION_ID = "org-1";

const mockedCreateDealFact = vi.mocked(createDealFact);
const mockedCorrectDealFact = vi.mocked(correctDealFact);
const mockedReviewDealFact = vi.mocked(reviewDealFact);
const mockedSuggestDealFacts = vi.mocked(suggestDealFacts);

function fact(overrides: Partial<DealFact> = {}): DealFact {
  return {
    id: "fact-1",
    deal_id: DEAL_ID,
    owner_organization_id: ORGANIZATION_ID,
    field: "quantity",
    typed_value: "500",
    currency_or_unit: "bags",
    kind: "INFORMATIONAL",
    status: "EXTRACTED",
    visibility: "PRIVATE",
    source_message_id: "message-1",
    source_span: "500 bags",
    confirmed_by: null,
    confirmed_at: null,
    version: 0,
    created_at: "2026-10-27T12:00:00Z",
    ...overrides,
  };
}

function renderReview(facts: DealFact[] = []) {
  return render(
    <AISuggestionReview
      dealId={DEAL_ID}
      organizationId={ORGANIZATION_ID}
      facts={facts}
      onTraceSource={vi.fn()}
      onFactAdded={vi.fn()}
      onFactUpdated={vi.fn()}
      onFactCorrected={vi.fn()}
    />,
  );
}

function missingStatus(field: string): HTMLElement {
  const label = screen.getByText(field, { selector: ".terms-readiness__item > span:nth-child(2)" });
  return label.closest("li") as HTMLElement;
}

function suggestionResult(facts: DealFact[], missing_fields: string[]) {
  return {
    status: "VALID" as const,
    issues: [],
    facts,
    missing_fields,
    guidance_message: "Missing trade details remain.",
  };
}

describe("AISuggestionReview readiness and manual entry", () => {
  beforeEach(() => {
    mockedCreateDealFact.mockReset();
    mockedCorrectDealFact.mockReset();
    mockedReviewDealFact.mockReset();
    mockedSuggestDealFacts.mockReset();
  });

  afterEach(() => vi.clearAllMocks());

  it("starts from persisted facts and keeps manual entry available when suggestions fail", async () => {
    renderReview([
      fact({ id: "description", field: "item_description", typed_value: "Coffee beans" }),
      fact({ id: "unit", field: "unit", typed_value: "bags" }),
    ]);
    mockedSuggestDealFacts.mockRejectedValue(new Error("AI unavailable"));

    expect(missingStatus("Item Description")).toHaveClass("terms-readiness__item--ready");
    expect(missingStatus("Unit")).toHaveClass("terms-readiness__item--ready");
    expect(missingStatus("Quantity")).toHaveClass("terms-readiness__item--missing");

    const addButton = screen.getByRole("button", { name: "+ Add Term Manually" });
    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(addButton).toBeInTheDocument();

    fireEvent.click(addButton);
    const dialog = screen.getByRole("dialog", { name: "Add a term manually" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByLabelText("Term type")).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(addButton).toHaveFocus();
  });

  it("saves a manual delivery date and updates checklist readiness", async () => {
    const created = fact({
      id: "manual-date",
      field: "delivery_date",
      typed_value: "2026-11-15",
      currency_or_unit: null,
      source_span: "2026-11-15",
    });
    mockedCreateDealFact.mockResolvedValue(created);
    renderReview([fact({ id: "item", field: "item_description" })]);

    fireEvent.click(screen.getByRole("button", { name: "+ Add Term Manually" }));
    fireEvent.change(screen.getByLabelText("Term type"), { target: { value: "delivery_date" } });
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "2026-11-15" } });
    fireEvent.change(screen.getByLabelText("Visibility"), { target: { value: "SHAREABLE" } });
    fireEvent.click(screen.getByRole("button", { name: "Add term" }));

    await waitFor(() => expect(mockedCreateDealFact).toHaveBeenCalledWith(DEAL_ID, {
      organization_id: ORGANIZATION_ID,
      field: "delivery_date",
      typed_value: "2026-11-15",
      currency_or_unit: null,
      kind: "INFORMATIONAL",
      visibility: "SHAREABLE",
    }));
    expect(missingStatus("Delivery Date")).toHaveClass("terms-readiness__item--ready");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("marks clarification-needed terms missing, while another persisted active fact keeps the field ready", async () => {
    const candidate = fact({ id: "candidate" });
    const persistedAlternative = fact({ id: "persisted-alternative", typed_value: "600" });
    mockedSuggestDealFacts.mockResolvedValue(suggestionResult([candidate], ["unit_price"]));
    mockedReviewDealFact.mockResolvedValue({
      ...candidate,
      status: "NEEDS_CLARIFICATION",
      version: 1,
    });
    const { rerender } = renderReview([candidate, persistedAlternative]);

    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    const ticket = await screen.findByRole("article", { name: "Fact suggestion: quantity" });
    fireEvent.click(within(ticket).getByRole("button", { name: "Ask for clarification" }));
    await waitFor(() => expect(mockedReviewDealFact).toHaveBeenCalledWith(DEAL_ID, candidate.id, "clarify"));
    expect(missingStatus("Quantity")).toHaveClass("terms-readiness__item--ready");

    rerender(
      <AISuggestionReview
        dealId={DEAL_ID}
        organizationId={ORGANIZATION_ID}
        facts={[candidate]}
        onTraceSource={vi.fn()}
        onFactAdded={vi.fn()}
        onFactUpdated={vi.fn()}
        onFactCorrected={vi.fn()}
      />,
    );
    expect(missingStatus("Quantity")).toHaveClass("terms-readiness__item--missing");
  });

  it("marks a field missing when concurrent rejections remove every active fact", async () => {
    const first = fact({ id: "quantity-first" });
    const second = fact({ id: "quantity-second", typed_value: "600" });
    const pendingReviews = new Map<string, (updated: DealFact) => void>();
    mockedSuggestDealFacts.mockResolvedValue(suggestionResult(
      [first, second],
      ["item_description", "unit", "unit_price", "delivery_destination", "delivery_date"],
    ));
    mockedReviewDealFact.mockImplementation(async (_dealId, factId) => new Promise((resolve) => {
      pendingReviews.set(factId, resolve);
    }));
    renderReview([first, second]);

    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    const tickets = await screen.findAllByRole("article", { name: "Fact suggestion: quantity" });
    fireEvent.click(within(tickets[0]).getByRole("button", { name: "Reject" }));
    fireEvent.click(within(tickets[1]).getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(pendingReviews.size).toBe(2));

    pendingReviews.get(first.id)?.({ ...first, status: "REJECTED", version: 1 });
    pendingReviews.get(second.id)?.({ ...second, status: "REJECTED", version: 1 });

    await waitFor(() => expect(missingStatus("Quantity")).toHaveClass("terms-readiness__item--missing"));
  });

  it("keeps a required field ready when another persisted fact survives a correction", async () => {
    const candidate = fact({ id: "suggested-quantity" });
    const persistedAlternative = fact({ id: "persisted-quantity", typed_value: "700" });
    const corrected = fact({
      id: "corrected-delivery-date",
      field: "delivery_date",
      typed_value: "2026-12-01",
      currency_or_unit: null,
      version: 0,
    });
    mockedSuggestDealFacts.mockResolvedValue(suggestionResult(
      [candidate],
      ["item_description", "unit", "unit_price", "delivery_destination", "delivery_date"],
    ));
    mockedCorrectDealFact.mockResolvedValue({
      replaced_fact: { ...candidate, status: "REJECTED", version: 1 },
      corrected_fact: corrected,
    });
    renderReview([candidate, persistedAlternative]);

    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    const ticket = await screen.findByRole("article", { name: "Fact suggestion: quantity" });
    fireEvent.change(within(ticket).getByLabelText("Fact label"), { target: { value: "delivery_date" } });
    fireEvent.click(within(ticket).getByRole("button", { name: "Save correction" }));

    await waitFor(() => expect(mockedCorrectDealFact).toHaveBeenCalledWith(DEAL_ID, candidate.id, {
      expected_version: candidate.version,
      field: "delivery_date",
      typed_value: candidate.typed_value,
      currency_or_unit: candidate.currency_or_unit,
    }));
    expect(missingStatus("Quantity")).toHaveClass("terms-readiness__item--ready");
    expect(missingStatus("Delivery Date")).toHaveClass("terms-readiness__item--ready");
  });

  it("ignores a stale suggestion response that arrives after a fact review", async () => {
    const candidate = fact({ id: "candidate" });
    let resolveStale!: (value: ReturnType<typeof suggestionResult>) => void;
    mockedSuggestDealFacts
      .mockResolvedValueOnce(suggestionResult([candidate], ["unit_price"]))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveStale = resolve; }));
    mockedReviewDealFact.mockResolvedValue({
      ...candidate,
      status: "CONFIRMED",
      confirmed_by: "user-1",
      confirmed_at: "2026-10-27T12:30:00Z",
      version: 1,
    });
    renderReview([]);

    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    const ticket = await screen.findByRole("article", { name: "Fact suggestion: quantity" });
    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    fireEvent.click(within(ticket).getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(mockedReviewDealFact).toHaveBeenCalled());

    resolveStale(suggestionResult([{ ...candidate, status: "EXTRACTED", version: 0 }], ["quantity"]));
    await waitFor(() => expect(missingStatus("Quantity")).toHaveClass("terms-readiness__item--ready"));
    expect(within(screen.getByRole("article", { name: "Fact suggestion: quantity" })).getByText("confirmed"))
      .toBeInTheDocument();
  });
});
