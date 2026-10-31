import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createDealFact,
  createDealMessage,
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
    createDealFact: vi.fn(),
    createDealMessage: vi.fn(),
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

const mockedCreateDealFact = vi.mocked(createDealFact);
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


describe("message composer", () => {
  const createMessage = vi.mocked(createDealMessage);
  beforeEach(() => {
    vi.resetAllMocks();
    mockedListOrganizations.mockResolvedValue([organization(BUYER_ID, "Buyer Co")]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedListDealFacts.mockResolvedValue([]);
    createMessage.mockResolvedValue(message({ id: "sent-message", body: "New terms", visibility: "SHAREABLE" }));
  });

  it("sends a trimmed shareable message, appends confirmation and observes scoped messages", async () => {
    const observe = vi.fn();
    render(<DealConversationReview deal={DEAL} onMessagesChanged={observe} revalidateIntervalMs={0} />);
    const input = await screen.findByLabelText("Message");
    expect(input).toHaveAttribute("id", `deal-message-composer-${DEAL.id}`);
    expect(screen.getByRole("radio", { name: /^Shareable/ })).toBeChecked();
    expect(screen.getByText("Sending as Buyer Co (Buyer)")).toBeInTheDocument();
    await waitFor(() => expect(observe).toHaveBeenCalledWith([]));
    fireEvent.change(input, { target: { value: "  New terms  " } });
    fireEvent.click(screen.getByRole("button", { name: "Send Message" }));
    expect(await screen.findByText("Message sent.")).toBeInTheDocument();
    expect(createMessage).toHaveBeenCalledExactlyOnceWith(DEAL.id, {
      body: "New terms", visibility: "SHAREABLE", organization_id: BUYER_ID,
      idempotency_key: expect.any(String),
    }, { signal: expect.any(AbortSignal) });
    expect(input).toHaveValue("");
    expect(document.getElementById("deal-message-sent-message")).toHaveTextContent("New terms");
    await waitFor(() => expect(observe).toHaveBeenLastCalledWith([expect.objectContaining({ id: "sent-message" })]));
  });

  it("sends private messages with lock attribution and preserves privacy for the next message", async () => {
    createMessage.mockResolvedValue(message({ id: "private-sent", body: "Internal price", visibility: "PRIVATE" }));
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    fireEvent.change(await screen.findByLabelText("Message"), { target: { value: "Internal price" } });
    fireEvent.click(screen.getByRole("radio", { name: /^Private/ }));
    fireEvent.click(screen.getByRole("button", { name: "Send Message" }));
    await screen.findByText("Message sent.");
    expect(createMessage.mock.calls[0][1].visibility).toBe("PRIVATE");
    const item = document.getElementById("deal-message-private-sent")!;
    expect(item.querySelector(".badge--private")).toHaveTextContent("\u{1F512} Private");
    expect(item).toHaveTextContent("Deal participant");
    expect(screen.getByRole("radio", { name: /^Private/ })).toBeChecked();
  });

  it.each(["ctrlKey", "metaKey"])("submits once with %s+Enter and locks the pending composer", async (modifier) => {
    let resolve!: (value: DealMessage) => void;
    createMessage.mockImplementation(() => new Promise((done) => { resolve = done; }));
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    const input = await screen.findByLabelText("Message");
    fireEvent.change(input, { target: { value: "New terms" } });
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.keyDown(input, { key: "Enter", [modifier]: true, isComposing: true });
    expect(createMessage).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Enter", [modifier]: true });
    fireEvent.keyDown(input, { key: "Enter", [modifier]: true });
    expect(createMessage).toHaveBeenCalledTimes(1);
    expect(input).toBeDisabled();
    expect(screen.getByRole("radio", { name: /^Private/ })).toBeDisabled();
    await act(async () => resolve(message({ id: "sent-message", body: "New terms" })));
    expect(input).toBeEnabled();
  });

  it("blocks whitespace and oversize messages and retains a failed private draft for retry", async () => {
    createMessage.mockRejectedValueOnce(new ApiError(503, "Service unavailable"));
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    const input = await screen.findByLabelText("Message");
    const send = screen.getByRole("button", { name: "Send Message" });
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(send);
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a message");
    fireEvent.change(input, { target: { value: "a".repeat(8001) } });
    fireEvent.click(send);
    expect(screen.getByRole("alert")).toHaveTextContent("8,000 characters");
    expect(createMessage).not.toHaveBeenCalled();
    expect(input).toHaveAttribute("maxlength", "8000");
    fireEvent.change(input, { target: { value: "Private draft" } });
    fireEvent.click(screen.getByRole("radio", { name: /^Private/ }));
    fireEvent.click(send);
    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(input).toHaveValue("Private draft");
    expect(screen.getByRole("radio", { name: /^Private/ })).toBeChecked();
    expect(send).toBeEnabled();
    fireEvent.click(send);
    await screen.findByText("Message sent.");
    expect(createMessage).toHaveBeenCalledTimes(2);
  });

  it("requires a party selection and hides confirmed private messages from the other context", async () => {
    mockedListOrganizations.mockResolvedValue([organization(BUYER_ID, "Buyer Co"), organization(SELLER_ID, "Seller Co")]);
    createMessage.mockResolvedValue(message({ id: "buyer-secret", body: "Buyer secret", visibility: "PRIVATE" }));
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    const select = await screen.findByLabelText("Viewing as");
    expect(screen.queryByLabelText("Message")).not.toBeInTheDocument();
    fireEvent.change(select, { target: { value: BUYER_ID } });
    fireEvent.change(await screen.findByLabelText("Message"), { target: { value: "Buyer secret" } });
    fireEvent.click(screen.getByRole("radio", { name: /^Private/ }));
    fireEvent.click(screen.getByRole("button", { name: "Send Message" }));
    await screen.findByText("Buyer secret");
    fireEvent.change(select, { target: { value: SELLER_ID } });
    expect(await screen.findByLabelText("Message")).toHaveValue("");
    expect(screen.queryByText("Buyer secret")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /^Shareable/ })).toBeChecked();
    expect(mockedListDealMessages).toHaveBeenLastCalledWith(DEAL.id, SELLER_ID);
  });

  it.each(["organization", "deal"])("aborts pending sends and ignores late success after changing %s", async (context) => {
    mockedListOrganizations.mockResolvedValue([organization(BUYER_ID, "Buyer Co"), organization(SELLER_ID, "Seller Co")]);
    let resolve!: (value: DealMessage) => void;
    createMessage.mockImplementation(() => new Promise((done) => { resolve = done; }));
    const observe = vi.fn();
    const { rerender } = render(<DealConversationReview deal={DEAL} onMessagesChanged={observe} revalidateIntervalMs={0} />);
    fireEvent.change(await screen.findByLabelText("Viewing as"), { target: { value: BUYER_ID } });
    fireEvent.change(await screen.findByLabelText("Message"), { target: { value: "Old private draft" } });
    fireEvent.click(screen.getByRole("radio", { name: /^Private/ }));
    fireEvent.click(screen.getByRole("button", { name: "Send Message" }));
    const signal = createMessage.mock.calls[0][2]?.signal;
    if (context === "organization") fireEvent.change(screen.getByLabelText("Viewing as"), { target: { value: SELLER_ID } });
    else rerender(<DealConversationReview deal={{ ...DEAL, id: "deal-2" }} onMessagesChanged={observe} revalidateIntervalMs={0} />);
    const input = await screen.findByLabelText("Message");
    expect(signal?.aborted).toBe(true);
    expect(input).toHaveValue("");
    fireEvent.change(input, { target: { value: "New context draft" } });
    observe.mockClear();
    await act(async () => resolve(message({ id: "late", body: "Old private draft" })));
    expect(input).toHaveValue("New context draft");
    expect(screen.queryByText("Old private draft")).not.toBeInTheDocument();
    expect(screen.queryByText("Message sent.")).not.toBeInTheDocument();
    expect(observe).not.toHaveBeenCalled();
  });

  it("does not reveal old messages while a same-party new deal loads, or late errors after unmount", async () => {
    mockedListDealMessages.mockResolvedValueOnce([message({ body: "Old deal secret" })]);
    let reject!: (reason: Error) => void;
    createMessage.mockImplementation(() => new Promise((_done, fail) => { reject = fail; }));
    const observe = vi.fn();
    const { rerender } = render(<DealConversationReview deal={DEAL} onMessagesChanged={observe} revalidateIntervalMs={0} />);
    fireEvent.change(await screen.findByLabelText("Message"), { target: { value: "Unsent" } });
    fireEvent.click(screen.getByRole("button", { name: "Send Message" }));
    mockedListDealMessages.mockImplementationOnce(() => new Promise(() => {}));
    observe.mockClear();
    rerender(<DealConversationReview deal={{ ...DEAL, id: "deal-2" }} onMessagesChanged={observe} revalidateIntervalMs={0} />);
    expect(screen.queryByText("Old deal secret")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Message")).not.toBeInTheDocument();
    await act(async () => reject(new Error("Old failure")));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await waitFor(() => expect(mockedListDealMessages).toHaveBeenLastCalledWith("deal-2", BUYER_ID));
    expect(observe).not.toHaveBeenCalled();
  });
  it.each(["send-first", "refresh-first"])("preserves confirmed sends and fetched source messages (%s)", async (order) => {
    let refresh!: (messages: DealMessage[]) => void;
    mockedListDealMessages.mockResolvedValueOnce([]).mockImplementationOnce(() => new Promise((resolve) => { refresh = resolve; }));
    mockedSuggestDealFacts.mockResolvedValue({
      status: "VALID", issues: [], missing_fields: [], guidance_message: "Review this fact.",
      facts: [fact({ id: "source-fact", field: "quantity", source_message_id: "source-message", source_span: "Source terms" })],
    });
    let send!: (value: DealMessage) => void;
    createMessage.mockImplementation(() => new Promise((resolve) => { send = resolve; }));
    const observe = vi.fn();
    render(<DealConversationReview deal={DEAL} onMessagesChanged={observe} revalidateIntervalMs={0} />);
    const input = await screen.findByLabelText("Message");
    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    await waitFor(() => expect(mockedListDealMessages).toHaveBeenCalledTimes(2));
    fireEvent.change(input, { target: { value: "Confirmed new terms" } });
    fireEvent.click(screen.getByRole("button", { name: "Send Message" }));
    const sent = message({ id: "confirmed", body: "Confirmed new terms" });
    const source = message({ id: "source-message", body: "Source terms" });
    if (order === "send-first") {
      await act(async () => send(sent));
      expect(screen.getByText("Confirmed new terms")).toBeInTheDocument();
      await act(async () => refresh([source]));
    } else {
      await act(async () => refresh([source]));
      await act(async () => send(sent));
    }
    expect(document.getElementById("deal-message-confirmed")).toHaveTextContent("Confirmed new terms");
    expect(document.getElementById("deal-message-source-message")).toHaveTextContent("Source terms");
    expect(observe).toHaveBeenLastCalledWith([source, sent]);
    expect(input).toHaveValue("");
    expect(screen.getByText("Message sent.")).toBeInTheDocument();
  });

});


describe("synchronized fact review and proposal drafts", () => {
  const quantity = fact({ field: "quantity", typed_value: "12", currency_or_unit: "boxes" });
  const draft = { schema_version: 1, description: "Shirts", quantity: "12", unit: "boxes",
    unit_price: "2.50", currency: "USD" as const, delivery_destination: "Toronto",
    delivery_date: "2026-12-01", status: "DRAFT" as const };

  beforeEach(() => {
    vi.resetAllMocks();
    mockedListOrganizations.mockResolvedValue([organization(BUYER_ID, "Buyer Co")]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedListDealFacts.mockResolvedValue([quantity]);
    mockedSuggestDealFacts.mockResolvedValue({ status: "VALID", issues: [], facts: [quantity],
      missing_fields: ["quantity"], guidance_message: "Review quantity." });
    mockedDraftDealProposal.mockResolvedValue(draft);
    mockedCreateAgreementFromReviewedTerms.mockResolvedValue({ version_number: 1 } as AgreementVersion);
  });
  afterEach(() => vi.clearAllMocks());

  async function openReview() {
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Suggest facts from this side's messages" }));
    await screen.findByRole("article", { name: "Fact suggestion: quantity" });
    fireEvent.click(screen.getByRole("button", { name: "Draft proposed terms" }));
    return screen.findByLabelText("Proposed terms draft");
  }

  it("uses the saved confirmation in both panels and submitted draft, preserving unrelated edits", async () => {
    const proposal = await openReview();
    const suggestion = screen.getByRole("article", { name: "Fact suggestion: quantity" });
    fireEvent.change(within(suggestion).getByLabelText("Suggested value"), { target: { value: "unsaved" } });
    fireEvent.change(within(proposal).getByLabelText("Unit price"), { target: { value: "8.75" } });
    fireEvent.change(within(proposal).getByLabelText("Delivery destination"), { target: { value: "Mumbai" } });
    fireEvent.change(within(proposal).getByLabelText("Payment timing"), { target: { value: "seller_invoice" } });
    mockedReviewDealFact.mockResolvedValue({ ...quantity, status: "CONFIRMED", typed_value: "24", version: 2 });
    fireEvent.click(within(screen.getByRole("article", { name: "quantity: 12" })).getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(within(suggestion).getByText("confirmed")).toBeInTheDocument());
    expect(within(suggestion).getByLabelText("Suggested value")).toHaveValue("24");
    expect(within(suggestion).getByLabelText("Suggested value")).toBeDisabled();
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("24");
    expect(within(proposal).getByLabelText("Unit price")).toHaveValue("8.75");
    expect(within(proposal).getByLabelText("Delivery destination")).toHaveValue("Mumbai");
    fireEvent.click(within(proposal).getByRole("button", { name: "Send reviewed terms for bilateral approval" }));
    await waitFor(() => expect(mockedCreateAgreementFromReviewedTerms).toHaveBeenCalledWith(DEAL.id, BUYER_ID,
      expect.objectContaining({ quantity: "24", unit_price: "8.75", delivery_destination: "Mumbai", currency: "USD", payment_trigger: "seller_invoice" })));
    expect(mockedSuggestDealFacts).toHaveBeenCalledTimes(1);
  });

  it("preserves dirty fact edits across polling and allows editing back to the original value", async () => {
    await openReview();
    const suggestion = screen.getByRole("article", { name: "Fact suggestion: quantity" });
    fireEvent.change(within(suggestion).getByLabelText("Suggested value"), { target: { value: "18" } });
    mockedListDealFacts.mockResolvedValue([{ ...quantity, typed_value: "20", version: 1 }]);
    fireEvent.focus(window);
    await screen.findByRole("article", { name: "quantity: 20" });
    expect(within(suggestion).getByLabelText("Suggested value")).toHaveValue("18");
    fireEvent.change(within(suggestion).getByLabelText("Suggested value"), { target: { value: "12" } });
    expect(within(suggestion).getByLabelText("Suggested value")).toHaveValue("12");
  });

  it("leaves suggestions and draft unchanged when confirmation fails", async () => {
    const proposal = await openReview();
    mockedReviewDealFact.mockRejectedValue(new ApiError(409, "Review conflict"));
    fireEvent.click(within(screen.getByRole("article", { name: "quantity: 12" })).getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("Review conflict")).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Fact suggestion: quantity" })).getByText("extracted")).toBeInTheDocument();
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("12");
  });

  it("applies a confirmation that finishes while the proposal request is in flight", async () => {
    let resolve!: (value: typeof draft) => void;
    mockedDraftDealProposal.mockImplementation(() => new Promise((done) => { resolve = done; }));
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Draft proposed terms" }));
    mockedReviewDealFact.mockResolvedValue({ ...quantity, status: "CONFIRMED", typed_value: "36", version: 2 });
    fireEvent.click(within(screen.getByRole("article", { name: "quantity: 12" })).getByRole("button", { name: "Confirm" }));
    await screen.findByRole("article", { name: "quantity: 36" });
    await act(async () => resolve(draft));
    expect(within(await screen.findByLabelText("Proposed terms draft")).getByLabelText("Quantity")).toHaveValue("36");
  });

  it.each(["revoked", "rejected"] as const)("invalidates a first draft when its confirmed fact is %s during the request", async (change) => {
    const shared = { ...quantity, owner_organization_id: SELLER_ID,
      visibility: "SHAREABLE" as const, status: "CONFIRMED" as const, version: 1 };
    mockedListDealFacts.mockResolvedValue([shared]);
    let resolve!: (value: typeof draft) => void;
    mockedDraftDealProposal.mockImplementation(() => new Promise((done) => { resolve = done; }));
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Draft proposed terms" }));
    expect(screen.queryByLabelText("Proposed terms draft")).not.toBeInTheDocument();
    mockedListDealFacts.mockResolvedValue(change === "revoked" ? [] : [{ ...shared, status: "REJECTED", version: 2 }]);
    fireEvent.focus(window);
    await waitFor(() => {
      if (change === "revoked") expect(screen.queryByRole("article", { name: "quantity: 12" })).not.toBeInTheDocument();
      else expect(within(screen.getByRole("article", { name: "quantity: 12" })).getByText("rejected")).toBeInTheDocument();
    });
    await act(async () => resolve(draft));
    const proposal = await screen.findByLabelText("Proposed terms draft");
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("");
    expect(within(proposal).getByRole("alert")).toHaveTextContent("request a fresh draft");
    expect(within(proposal).getByRole("button", { name: "Send reviewed terms for bilateral approval" })).toBeDisabled();
    expect(mockedCreateAgreementFromReviewedTerms).not.toHaveBeenCalled();
  });

  it("discards older polling versions and removes revoked facts and their derived draft values", async () => {
    mockedListDealFacts.mockResolvedValue([{ ...quantity, status: "CONFIRMED", typed_value: "24", version: 2 }]);
    const proposal = await openReview();
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("24");
    mockedListDealFacts.mockResolvedValue([quantity]);
    await act(async () => { fireEvent.focus(window); });
    expect(mockedListDealFacts).toHaveBeenCalledTimes(2);
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("24");
    mockedListDealFacts.mockResolvedValue([]);
    await act(async () => { fireEvent.focus(window); });
    await waitFor(() => expect(screen.queryByRole("article", { name: "Fact suggestion: quantity" })).not.toBeInTheDocument());
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("");
    expect(within(proposal).getByRole("button", { name: "Send reviewed terms for bilateral approval" })).toBeDisabled();
  });

  it("does not resurrect revoked facts when a late review response resolves", async () => {
    let resolveReview!: (val: DealFact) => void;
    let resolvePoll!: (val: DealFact[]) => void;
    mockedReviewDealFact.mockImplementation(() => new Promise((resolve) => { resolveReview = resolve; }));
    mockedListDealFacts.mockResolvedValueOnce([quantity]);
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    const factItem = await screen.findByRole("article", { name: "quantity: 12" });

    // Poll is started and pending
    mockedListDealFacts.mockImplementationOnce(() => new Promise((resolve) => { resolvePoll = resolve; }));
    fireEvent.focus(window);
    await waitFor(() => expect(mockedListDealFacts).toHaveBeenCalledTimes(2));

    // User reviews the fact while poll is in flight
    fireEvent.click(within(factItem).getByRole("button", { name: "Confirm" }));
    expect(mockedReviewDealFact).toHaveBeenCalledTimes(1);

    // Poll resolves without the fact (revoked by counterparty)
    await act(async () => {
      resolvePoll([]);
    });
    await waitFor(() => expect(screen.queryByRole("article", { name: "quantity: 12" })).not.toBeInTheDocument());

    // Late review response resolves
    await act(async () => {
      resolveReview({ ...quantity, status: "CONFIRMED", version: 2 });
    });

    // Fact must NOT reappear
    expect(screen.queryByRole("article", { name: "quantity: 12" })).not.toBeInTheDocument();
  });

  it("preserves newly saved facts when a stale polling response arrives", async () => {
    let resolvePoll!: (val: DealFact[]) => void;
    mockedListDealFacts.mockResolvedValueOnce([quantity]);
    render(<DealConversationReview deal={DEAL} revalidateIntervalMs={0} />);
    await screen.findByRole("article", { name: "quantity: 12" });

    mockedListDealFacts.mockImplementationOnce(() => new Promise((resolve) => { resolvePoll = resolve; }));
    fireEvent.focus(window);
    await waitFor(() => expect(mockedListDealFacts).toHaveBeenCalledTimes(2));

    mockedCreateDealFact.mockResolvedValue(fact({ id: "new-fact", field: "delivery_destination", typed_value: "Tokyo", status: "EXTRACTED" }));
    fireEvent.click(screen.getByRole("button", { name: "+ Add Term Manually" }));
    fireEvent.change(screen.getByLabelText("Term type"), { target: { value: "delivery_destination" } });
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "Tokyo" } });
    fireEvent.click(screen.getByRole("button", { name: "Add term" }));
    await screen.findByRole("article", { name: "delivery_destination: Tokyo" });

    await act(async () => {
      resolvePoll([quantity]);
    });

    expect(screen.getByRole("article", { name: "delivery_destination: Tokyo" })).toBeInTheDocument();
  });

  it("blocks agreement creation and clears proposal field when currency metadata contradicts proposal currency", async () => {
    mockedListDealFacts.mockResolvedValue([
      fact({ id: "eur-price", field: "unit_price", typed_value: "100", currency_or_unit: "EUR", status: "CONFIRMED" }),
    ]);
    mockedDraftDealProposal.mockResolvedValue({
      schema_version: 1,
      description: "Apples",
      quantity: "10",
      unit: "kg",
      unit_price: "2.50",
      currency: "USD",
      delivery_destination: "Port",
      delivery_date: "2026-11-01",
      status: "DRAFT",
    });
    const proposal = await openReview();
    expect(within(proposal).getByLabelText("Unit price")).toHaveValue("");
    expect(within(proposal).getByRole("button", { name: "Send reviewed terms for bilateral approval" })).toBeDisabled();
  });

  it("blocks agreement creation when confirmed unit fact contradicts confirmed quantity unit", async () => {
    mockedListDealFacts.mockResolvedValue([
      fact({ id: "qty-fact", field: "quantity", typed_value: "10", currency_or_unit: "kg", status: "CONFIRMED" }),
      fact({ id: "unit-fact", field: "unit", typed_value: "boxes", status: "CONFIRMED" }),
    ]);
    const proposal = await openReview();
    expect(within(proposal).getByLabelText("Unit")).toHaveValue("");
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("");
    expect(within(proposal).getByRole("button", { name: "Send reviewed terms for bilateral approval" })).toBeDisabled();
  });

  it("preserves fact suggestion draft edits when a background suggestion response arrives", async () => {
    await openReview();
    const suggestion = screen.getByRole("article", { name: "Fact suggestion: quantity" });

    let resolveSuggestions!: (val: Awaited<ReturnType<typeof suggestDealFacts>>) => void;
    mockedSuggestDealFacts.mockImplementation(() => new Promise((resolve) => { resolveSuggestions = resolve; }));

    fireEvent.click(screen.getByRole("button", { name: "Suggest facts from this side's messages" }));
    expect(mockedSuggestDealFacts).toHaveBeenCalledTimes(2);

    fireEvent.change(within(suggestion).getByLabelText("Suggested value"), { target: { value: "42" } });
    expect(within(suggestion).getByLabelText("Suggested value")).toHaveValue("42");

    await act(async () => {
      resolveSuggestions({
        status: "VALID",
        issues: [],
        missing_fields: [],
        guidance_message: "",
        facts: [fact({ id: quantity.id, field: "quantity", typed_value: "99", status: "EXTRACTED" })],
      });
    });

    expect(within(suggestion).getByLabelText("Suggested value")).toHaveValue("42");
  });

  it("fetches all pages of deal facts when there are more than 100 facts", async () => {
    const actualClient = await vi.importActual<typeof import("../api/client")>("../api/client");
    const originalFetch = globalThis.fetch;
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;
    try {
      const page1 = Array.from({ length: 100 }, (_, i) => ({
        id: `fact-${i}`,
        deal_id: DEAL.id,
        owner_organization_id: BUYER_ID,
        field: "item_description",
        typed_value: `Widget ${i}`,
        currency_or_unit: null,
        kind: "DISCOVERED",
        status: "EXTRACTED",
        visibility: "SHAREABLE",
        source_message_id: null,
        source_span: null,
        confirmed_by: null,
        confirmed_at: null,
        version: 1,
        created_at: "2026-10-31T00:00:00Z",
      }));
      const page2 = Array.from({ length: 5 }, (_, i) => ({
        id: `fact-10${i}`,
        deal_id: DEAL.id,
        owner_organization_id: BUYER_ID,
        field: "item_description",
        typed_value: `Widget 10${i}`,
        currency_or_unit: null,
        kind: "DISCOVERED",
        status: "CONFIRMED",
        visibility: "SHAREABLE",
        source_message_id: null,
        source_span: null,
        confirmed_by: null,
        confirmed_at: null,
        version: 1,
        created_at: "2026-10-31T00:00:00Z",
      }));

      fetchSpy
        .mockResolvedValueOnce(new Response(JSON.stringify(page1), { status: 200, headers: { "Content-Type": "application/json" } }))
        .mockResolvedValueOnce(new Response(JSON.stringify(page2), { status: 200, headers: { "Content-Type": "application/json" } }));

      const allFacts = await actualClient.listDealFacts(DEAL.id, BUYER_ID);
      expect(fetchSpy).toHaveBeenCalledTimes(2);
      expect(allFacts).toHaveLength(105);
      expect(allFacts[104].id).toBe("fact-104");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("blocks conflicting confirmed values and excludes another organization's private values", async () => {
    mockedListDealFacts.mockResolvedValue([
      { ...quantity, status: "CONFIRMED", version: 1 },
      fact({ id: "conflict", field: "quantity", typed_value: "99", status: "CONFIRMED" }),
      fact({ id: "secret", owner_organization_id: SELLER_ID, field: "unit_price", typed_value: "secret", status: "CONFIRMED" }),
    ]);
    const proposal = await openReview();
    expect(within(proposal).getByLabelText("Quantity")).toHaveValue("");
    expect(within(proposal).getByLabelText("Unit price")).toHaveValue("2.50");
    expect(within(proposal).getByRole("button", { name: "Send reviewed terms for bilateral approval" })).toBeDisabled();
  });

  it("ignores a suggestion completion from a previous visit to the same organization", async () => {
    let resolve!: (value: Awaited<ReturnType<typeof suggestDealFacts>>) => void;
    mockedSuggestDealFacts.mockImplementation(() => new Promise((done) => { resolve = done; }));
    const { rerender } = render(<DealConversationReview deal={DEAL} selectedOrganizationId={BUYER_ID} revalidateIntervalMs={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Suggest facts from this side's messages" }));
    rerender(<DealConversationReview deal={DEAL} selectedOrganizationId="" revalidateIntervalMs={0} />);
    rerender(<DealConversationReview deal={DEAL} selectedOrganizationId={BUYER_ID} revalidateIntervalMs={0} />);
    await screen.findByRole("button", { name: "Suggest facts from this side's messages" });
    await act(async () => resolve({ status: "VALID", issues: [], missing_fields: [], guidance_message: "",
      facts: [fact({ id: "late-private", typed_value: "Old secret" })] }));
    expect(screen.queryByText("Old secret")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Fact suggestions for review")).not.toBeInTheDocument();
  });
});
