import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  listDealFacts,
  listDealMessages,
  listOrganizations,
  reviewDealFact,
  suggestDealFacts,
  draftDealProposal,
  correctDealFact,
  createAgreementFromReviewedTerms,
  updateFactVisibility,
} from "../api/client";
import type { AgreementVersion, Deal, DealFact, DealMessage, Organization } from "../api/types";
import DealConversationReview from "./DealConversationReview";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
    listOrganizations: vi.fn(),
    reviewDealFact: vi.fn(),
    suggestDealFacts: vi.fn(),
    draftDealProposal: vi.fn(),
    correctDealFact: vi.fn(),
    createAgreementFromReviewedTerms: vi.fn(),
    updateFactVisibility: vi.fn(),
  };
});

const BUYER_ID = "11111111-1111-1111-1111-111111111111";
const SELLER_ID = "22222222-2222-2222-2222-222222222222";
const DEAL: Deal = {
  id: "deal-1",
  buyer_organization_id: BUYER_ID,
  seller_organization_id: SELLER_ID,
  status: "DRAFT",
  version: 0,
};

const mockedListDealFacts = vi.mocked(listDealFacts);
const mockedListDealMessages = vi.mocked(listDealMessages);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedReviewDealFact = vi.mocked(reviewDealFact);
const mockedSuggestDealFacts = vi.mocked(suggestDealFacts);
const mockedDraftDealProposal = vi.mocked(draftDealProposal);
const mockedCorrectDealFact = vi.mocked(correctDealFact);
const mockedCreateAgreementFromReviewedTerms = vi.mocked(createAgreementFromReviewedTerms);
const mockedUpdateFactVisibility = vi.mocked(updateFactVisibility);

function organization(id: string, legalName: string): Organization {
  return { id, legal_name: legalName, country_code: "US", role: "ADMIN" };
}

function fact(overrides: Partial<DealFact> = {}): DealFact {
  return {
    id: "fact-1",
    deal_id: DEAL.id,
    owner_organization_id: BUYER_ID,
    field: "Delivery date",
    typed_value: "2026-11-01",
    currency_or_unit: null,
    kind: "HARD_LIMIT",
    status: "EXTRACTED",
    visibility: "PRIVATE",
    source_message_id: null,
    source_span: "We need delivery by November 1.",
    confirmed_by: null,
    confirmed_at: null,
    version: 0,
    created_at: "2026-10-18T09:00:00Z",
    ...overrides,
  };
}

function message(overrides: Partial<DealMessage> = {}): DealMessage {
  return {
    id: "message-1",
    conversation_id: "conversation-1",
    author_user_id: "user-12345678",
    author_agent_id: null,
    body: "We need delivery by November 1.",
    visibility: "PRIVATE",
    source_type: "USER",
    source_reference: null,
    created_at: "2026-10-18T09:00:00Z",
    ...overrides,
  };
}

describe("DealConversationReview", () => {
  beforeEach(() => {
    mockedListOrganizations.mockResolvedValue([organization(BUYER_ID, "Buyer Co")]);
    mockedListDealMessages.mockResolvedValue([message()]);
    mockedListDealFacts.mockResolvedValue([fact()]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows message visibility and fact review state, then submits all review actions", async () => {
    const facts = [
      fact(),
      fact({ id: "fact-2", field: "Minimum quantity", visibility: "SHAREABLE" }),
      fact({ id: "fact-3", field: "Preferred port", visibility: "SHAREABLE" }),
    ];
    mockedReviewDealFact.mockImplementation(async (_dealId, factId, action) => {
      const original = facts.find((item) => item.id === factId) ?? facts[0];
      return {
        ...original,
        id: factId,
        status:
          action === "confirm"
            ? "CONFIRMED"
            : action === "reject"
              ? "REJECTED"
              : "NEEDS_CLARIFICATION",
        confirmed_by: action === "confirm" ? "user-1" : null,
        confirmed_at: action === "confirm" ? "2026-10-18T10:00:00Z" : null,
        version: 1,
      };
    });
    mockedListDealFacts.mockResolvedValue(facts);

    render(<DealConversationReview deal={DEAL} />);

    expect(await screen.findByText("We need delivery by November 1.")).toBeInTheDocument();
    expect(mockedListDealMessages).toHaveBeenCalledWith(DEAL.id, BUYER_ID);
    expect(mockedListDealFacts).toHaveBeenCalledWith(DEAL.id, BUYER_ID);

    const deliveryFact = screen.getByRole("article", { name: "Delivery date: 2026-11-01" });
    expect(within(deliveryFact).getByText("🔒 Private to your org")).toBeInTheDocument();
    expect(within(deliveryFact).getByRole("button", { name: "Make Shareable" })).toBeInTheDocument();
    expect(within(deliveryFact).getByText(/extracted · unconfirmed/i)).toBeInTheDocument();
    expect(
      screen.getByText(/confirming one records your review; it does not approve the deal/i),
    ).toBeInTheDocument();

    const minQtyFact = screen.getByRole("article", { name: "Minimum quantity: 2026-11-01" });
    expect(within(minQtyFact).getByText("🌐 Shared with counterparty")).toBeInTheDocument();
    expect(within(minQtyFact).getByRole("button", { name: "Make Private" })).toBeInTheDocument();

    fireEvent.click(within(deliveryFact).getByRole("button", { name: "Confirm" }));
    expect(await within(deliveryFact).findByText("confirmed")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("article", { name: "Minimum quantity: 2026-11-01" })).getByRole("button", { name: "Reject" }));
    expect(await screen.findByText("rejected")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("article", { name: "Preferred port: 2026-11-01" })).getByRole("button", { name: "Ask for clarification" }));
    expect(await screen.findByText("needs clarification")).toBeInTheDocument();

    expect(mockedReviewDealFact).toHaveBeenNthCalledWith(1, DEAL.id, "fact-1", "confirm");
    expect(mockedReviewDealFact).toHaveBeenNthCalledWith(2, DEAL.id, "fact-2", "reject");
    expect(mockedReviewDealFact).toHaveBeenNthCalledWith(3, DEAL.id, "fact-3", "clarify");

    fireEvent.click(screen.getByRole("button", { name: /confirmed/i }));
    expect(screen.getByRole("article", { name: "Delivery date: 2026-11-01" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Minimum quantity: 2026-11-01" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /private here/i }));
    expect(screen.getByRole("article", { name: "Delivery date: 2026-11-01" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Preferred port: 2026-11-01" })).not.toBeInTheDocument();
  });

  it("requires a party choice for dual members and scopes reads so other private facts stay hidden", async () => {
    const buyerPrivate = fact({ id: "buyer-private", typed_value: "Buyer confidential price" });
    const sellerPrivate = fact({
      id: "seller-private",
      owner_organization_id: SELLER_ID,
      typed_value: "Seller confidential floor",
    });
    const sharedSellerFact = fact({
      id: "shared-seller",
      owner_organization_id: SELLER_ID,
      typed_value: "Ships from Seattle",
      visibility: "SHAREABLE",
    });
    mockedListOrganizations.mockResolvedValue([
      organization(BUYER_ID, "Buyer Co"),
      organization(SELLER_ID, "Seller Co"),
    ]);
    mockedListDealMessages.mockImplementation(async (_dealId, organizationId) =>
      organizationId === BUYER_ID
        ? [message({ body: "Buyer private message" })]
        : [message({ id: "seller-message", body: "Seller private message" })],
    );
    mockedListDealFacts.mockImplementation(async (_dealId, organizationId) =>
      organizationId === BUYER_ID
        ? [buyerPrivate, sellerPrivate, sharedSellerFact]
        : [sellerPrivate, buyerPrivate],
    );

    render(<DealConversationReview deal={DEAL} />);

    const selector = await screen.findByLabelText("Viewing as");
    expect(mockedListDealFacts).not.toHaveBeenCalled();
    fireEvent.change(selector, { target: { value: BUYER_ID } });

    expect(await screen.findByText("Buyer private message")).toBeInTheDocument();
    expect(screen.getByText("Buyer confidential price")).toBeInTheDocument();
    expect(screen.getByText("Ships from Seattle")).toBeInTheDocument();
    expect(screen.queryByText("Seller private message")).not.toBeInTheDocument();
    expect(screen.queryByText("Seller confidential floor")).not.toBeInTheDocument();
    expect(mockedListDealFacts).toHaveBeenCalledWith(DEAL.id, BUYER_ID);
    expect(
      within(screen.getByRole("article", { name: "Delivery date: Ships from Seattle" })).queryByRole(
        "button",
        { name: "Confirm" },
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("article", { name: "Delivery date: Ships from Seattle" })).queryByRole(
        "button",
        { name: /make private|make shareable/i },
      ),
    ).not.toBeInTheDocument();

    fireEvent.change(selector, { target: { value: SELLER_ID } });
    expect(await screen.findByText("Seller private message")).toBeInTheDocument();
    expect(await screen.findByText("Seller confidential floor")).toBeInTheDocument();
    expect(screen.queryByText("Buyer private message")).not.toBeInTheDocument();
    expect(screen.queryByText("Buyer confidential price")).not.toBeInTheDocument();
    expect(mockedListDealFacts).toHaveBeenLastCalledWith(DEAL.id, SELLER_ID);
    expect(mockedListDealMessages).toHaveBeenLastCalledWith(DEAL.id, SELLER_ID);
  });

  it("runs suggestions only on request, lets a person edit and review them, and keeps proposal terms as a private-safe draft", async () => {
    const onAgreementCreated = vi.fn();
    const sharedDescription = fact({
      id: "shared-description",
      field: "item_description",
      typed_value: "Organic cotton shirts",
      visibility: "SHAREABLE",
    });
    const privatePrice = fact({
      id: "private-price",
      field: "unit_price",
      typed_value: "1.00",
      currency_or_unit: "USD",
      visibility: "PRIVATE",
    });
    mockedListDealFacts.mockResolvedValue([sharedDescription, privatePrice]);
    const suggested = fact({
      id: "suggested-quantity",
      field: "quantity",
      typed_value: "12",
      currency_or_unit: "boxes",
      source_message_id: "message-1",
      source_span: "12 boxes",
    });
    mockedSuggestDealFacts.mockResolvedValue({
      status: "VALID",
      issues: [],
      facts: [suggested],
      missing_fields: ["unit_price", "delivery_destination", "delivery_date"],
      guidance_message: "Add the missing details: unit price, delivery destination, delivery date.",
    });
    mockedReviewDealFact.mockImplementation(async (_dealId, factId) => ({
      ...suggested,
      id: factId,
      status: "CONFIRMED",
      confirmed_by: "user-1",
      version: 1,
    }));
    mockedDraftDealProposal.mockResolvedValue({
      schema_version: 1,
      description: "Organic cotton shirts",
      quantity: "12",
      unit: "boxes",
      unit_price: "2.50",
      currency: "USD",
      delivery_destination: "Toronto",
      delivery_date: "2026-12-01",
      status: "DRAFT",
    });
    mockedCreateAgreementFromReviewedTerms.mockResolvedValue({
      version_number: 1,
    } as AgreementVersion);

    render(<DealConversationReview deal={DEAL} onAgreementCreated={onAgreementCreated} />);

    expect(await screen.findByText("We need delivery by November 1.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Fact suggestions for review")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Proposed terms draft")).not.toBeInTheDocument();
    expect(mockedReviewDealFact).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    const suggestion = await screen.findByRole("article", { name: "Fact suggestion: quantity" });
    expect(mockedSuggestDealFacts).toHaveBeenCalledWith(DEAL.id, BUYER_ID);
    expect(within(suggestion).getByLabelText("Fact label")).toHaveValue("quantity");
    expect(within(suggestion).getByLabelText("Suggested value")).toHaveValue("12");
    expect(within(suggestion).getByRole("blockquote")).toHaveTextContent("12 boxes");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Add the missing details: unit price, delivery destination, delivery date.",
    );

    fireEvent.change(within(suggestion).getByLabelText("Suggested value"), {
      target: { value: "24" },
    });
    expect(within(suggestion).getByLabelText("Suggested value")).toHaveValue("24");
    mockedCorrectDealFact.mockResolvedValue({
      replaced_fact: { ...suggested, status: "REJECTED", version: 1 },
      corrected_fact: { ...suggested, id: "corrected-quantity", typed_value: "24" },
    });
    fireEvent.click(within(suggestion).getByRole("button", { name: "Save correction" }));
    await vi.waitFor(() => expect(mockedCorrectDealFact).toHaveBeenCalled());
    expect(mockedCorrectDealFact).toHaveBeenCalledWith(DEAL.id, suggested.id, {
      expected_version: suggested.version,
      field: "quantity",
      typed_value: "24",
      currency_or_unit: "boxes",
    });
    fireEvent.click(screen.getByRole("button", { name: "Draft proposed terms" }));
    const proposal = await screen.findByLabelText("Proposed terms draft");
    expect(within(proposal).getByText("DRAFT - NOT AN AGREEMENT")).toBeInTheDocument();
    expect(within(proposal).getByLabelText("Item description")).toHaveValue("Organic cotton shirts");
    expect(within(proposal).getByLabelText("Unit price")).toHaveValue("2.50");
    expect(within(proposal).queryByText("1.00")).not.toBeInTheDocument();
    // The draft preview repeats the canonical condition, not a stronger paraphrase.
    expect(within(proposal).getByText("Due condition: when seller invoices")).toBeInTheDocument();
    expect(within(proposal).getByText(/does not create or approve an agreement/i)).toBeInTheDocument();
    expect(mockedDraftDealProposal).toHaveBeenCalledWith(DEAL.id, BUYER_ID);
    fireEvent.click(within(proposal).getByRole("button", { name: "Send reviewed terms for bilateral approval" }));
    await vi.waitFor(() => expect(mockedCreateAgreementFromReviewedTerms).toHaveBeenCalled());
    expect(mockedCreateAgreementFromReviewedTerms).toHaveBeenCalledWith(DEAL.id, BUYER_ID, {
      schema_version: 1,
      description: "Organic cotton shirts",
      quantity: "12",
      unit: "boxes",
      unit_price: "2.50",
      currency: "USD",
      delivery_destination: "Toronto",
      delivery_date: "2026-12-01",
      payment_trigger: "seller_invoice",
    });
    expect(onAgreementCreated).toHaveBeenCalledOnce();
    expect(await screen.findByText("Agreement version 1 is ready for both parties to review."))
      .toBeInTheDocument();
  });

  it("clears local suggestion state when switching organizations", async () => {
    mockedListOrganizations.mockResolvedValue([
      organization(BUYER_ID, "Buyer Co"),
      organization(SELLER_ID, "Seller Co"),
    ]);
    mockedListDealMessages.mockImplementation(async (_dealId, organizationId) => [
      message({ body: organizationId === BUYER_ID ? "Buyer-only note" : "Seller-only note" }),
    ]);
    mockedSuggestDealFacts.mockImplementation(async (_dealId, organizationId) => ({
      status: "VALID",
      issues: [],
      missing_fields: [],
      guidance_message: "All required trade details were found.",
      facts: [fact({
        id: `${organizationId}-candidate`,
        owner_organization_id: organizationId,
        field: "Conversation detail",
        typed_value: organizationId === BUYER_ID ? "Buyer-only note" : "Seller-only note",
        source_message_id: organizationId === BUYER_ID ? "message-1" : "seller-message",
        source_span: organizationId === BUYER_ID ? "Buyer-only note" : "Seller-only note",
      })],
    }));

    render(<DealConversationReview deal={DEAL} />);
    const selector = await screen.findByLabelText("Viewing as");
    fireEvent.change(selector, { target: { value: BUYER_ID } });
    expect(await screen.findByText("Buyer-only note")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    expect(await screen.findByLabelText("Suggested value")).toHaveValue("Buyer-only note");

    fireEvent.change(selector, { target: { value: SELLER_ID } });
    expect(await screen.findByText("Seller-only note")).toBeInTheDocument();
    expect(screen.queryByLabelText("Suggested value")).not.toBeInTheDocument();
    expect(screen.queryByText("Buyer-only note", { selector: "blockquote" })).not.toBeInTheDocument();
  });

  it("toggles fact visibility between PRIVATE and SHAREABLE immediately in UI without page reload", async () => {
    const testFact = fact({ id: "fact-toggle-1", visibility: "PRIVATE" });
    mockedListDealFacts.mockResolvedValue([testFact]);
    mockedUpdateFactVisibility.mockImplementation(async (_dealId, _factId, visibility) => ({
      ...testFact,
      visibility,
      version: testFact.version + 1,
    }));

    render(<DealConversationReview deal={DEAL} />);

    expect(await screen.findByText("Delivery date")).toBeInTheDocument();
    const factCard = screen.getByRole("article", { name: "Delivery date: 2026-11-01" });

    // Initial state: PRIVATE
    expect(within(factCard).getByText("🔒 Private to your org")).toBeInTheDocument();
    const makeShareableBtn = within(factCard).getByRole("button", { name: "Make Shareable" });
    expect(makeShareableBtn).toBeInTheDocument();

    // Toggle to SHAREABLE
    fireEvent.click(makeShareableBtn);

    expect(await within(factCard).findByText("🌐 Shared with counterparty")).toBeInTheDocument();
    expect(within(factCard).getByRole("button", { name: "Make Private" })).toBeInTheDocument();
    expect(mockedUpdateFactVisibility).toHaveBeenCalledWith(DEAL.id, "fact-toggle-1", "SHAREABLE");

    // Toggle back to PRIVATE
    const makePrivateBtn = within(factCard).getByRole("button", { name: "Make Private" });
    fireEvent.click(makePrivateBtn);

    expect(await within(factCard).findByText("🔒 Private to your org")).toBeInTheDocument();
    expect(within(factCard).getByRole("button", { name: "Make Shareable" })).toBeInTheDocument();
    expect(mockedUpdateFactVisibility).toHaveBeenCalledWith(DEAL.id, "fact-toggle-1", "PRIVATE");
  });

  it("disables fact review actions while a visibility update is pending", async () => {
    const testFact = fact({ id: "fact-visibility-race", visibility: "PRIVATE" });
    mockedListDealFacts.mockResolvedValue([testFact]);
    let resolveVisibility: (updated: DealFact) => void = () => {};
    mockedUpdateFactVisibility.mockImplementation(
      () =>
        new Promise<DealFact>((resolve) => {
          resolveVisibility = resolve;
        }),
    );

    render(<DealConversationReview deal={DEAL} />);

    const factCard = await screen.findByRole("article", { name: "Delivery date: 2026-11-01" });
    fireEvent.click(within(factCard).getByRole("button", { name: "Make Shareable" }));

    const confirmButton = within(factCard).getByRole("button", { name: "Confirm" });
    expect(within(factCard).getByRole("button", { name: "Reject" })).toBeDisabled();
    expect(within(factCard).getByRole("button", { name: "Ask for clarification" })).toBeDisabled();
    expect(confirmButton).toBeDisabled();

    fireEvent.click(confirmButton);
    expect(mockedReviewDealFact).not.toHaveBeenCalled();

    resolveVisibility({ ...testFact, visibility: "SHAREABLE", version: 1 });

    expect(await within(factCard).findByRole("button", { name: "Make Private" })).toBeInTheDocument();
    expect(within(factCard).getByRole("button", { name: "Confirm" })).toBeEnabled();
  });

  it("shows error when visibility toggle request fails", async () => {
    const testFact = fact({ id: "fact-fail-1", visibility: "PRIVATE" });
    mockedListDealFacts.mockResolvedValue([testFact]);
    mockedUpdateFactVisibility.mockRejectedValue(
      new ApiError(403, "Only an authorized member of the owner organization can modify fact visibility"),
    );

    render(<DealConversationReview deal={DEAL} />);

    expect(await screen.findByText("Delivery date")).toBeInTheDocument();
    const factCard = screen.getByRole("article", { name: "Delivery date: 2026-11-01" });
    const makeShareableBtn = within(factCard).getByRole("button", { name: "Make Shareable" });

    fireEvent.click(makeShareableBtn);

    expect(
      await screen.findByText("Only an authorized member of the owner organization can modify fact visibility"),
    ).toBeInTheDocument();
    expect(within(factCard).getByText("🔒 Private to your org")).toBeInTheDocument();
  });

  it("revalidates and removes private facts from open counterparty sessions on window focus or visibility change", async () => {
    const sharedFact = fact({
      id: "fact-shared-1",
      owner_organization_id: BUYER_ID,
      field: "Warranty period",
      typed_value: "24 months",
      visibility: "SHAREABLE",
    });

    mockedListOrganizations.mockResolvedValue([
      organization(SELLER_ID, "Seller Co"),
    ]);
    mockedListDealMessages.mockResolvedValue([
      message({ body: "Seller message" }),
    ]);
    mockedListDealFacts.mockResolvedValueOnce([sharedFact]);

    render(<DealConversationReview deal={DEAL} />);

    expect(await screen.findByText("Warranty period")).toBeInTheDocument();
    expect(screen.getByText("24 months")).toBeInTheDocument();
    expect(screen.getByText("🌐 Shared with counterparty")).toBeInTheDocument();

    mockedListDealFacts.mockResolvedValue([]);

    fireEvent(window, new Event("focus"));

    await vi.waitFor(() => {
      expect(screen.queryByText("Warranty period")).not.toBeInTheDocument();
    });
    expect(
      screen.getByText("No facts are available for this organization yet."),
    ).toBeInTheDocument();
  });

  it("periodically revalidates facts in an open session", async () => {
    const initialFact = fact({
      id: "fact-p1",
      field: "Delivery date",
      typed_value: "2026-11-01",
      visibility: "SHAREABLE",
    });
    const newFact = fact({
      id: "fact-p2",
      field: "Payment terms",
      typed_value: "Net 30",
      visibility: "SHAREABLE",
    });

    mockedListOrganizations.mockResolvedValue([
      organization(BUYER_ID, "Buyer Co"),
    ]);
    mockedListDealMessages.mockResolvedValue([message()]);
    mockedListDealFacts.mockResolvedValueOnce([initialFact]);

    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={50} />);

    expect(await screen.findByText("Delivery date")).toBeInTheDocument();

    mockedListDealFacts.mockResolvedValue([initialFact, newFact]);

    expect(await screen.findByText("Payment terms")).toBeInTheDocument();
    expect(screen.getByText("Net 30")).toBeInTheDocument();
  });

  it("silently tolerates background revalidation errors without wiping open conversation view", async () => {
    const initialFact = fact({
      id: "fact-err-test",
      field: "Payment terms",
      typed_value: "Net 60",
      visibility: "SHAREABLE",
    });

    mockedListOrganizations.mockResolvedValue([
      organization(BUYER_ID, "Buyer Co"),
    ]);
    mockedListDealMessages.mockResolvedValue([message()]);
    mockedListDealFacts.mockResolvedValueOnce([initialFact]);

    render(<DealConversationReview deal={DEAL} />);

    expect(await screen.findByText("Payment terms")).toBeInTheDocument();

    mockedListDealFacts.mockRejectedValue(new Error("Network disconnect"));

    fireEvent(window, new Event("focus"));

    expect(screen.getByText("Payment terms")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
