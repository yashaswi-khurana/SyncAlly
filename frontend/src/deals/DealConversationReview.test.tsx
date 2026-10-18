import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  listDealFacts,
  listDealMessages,
  listOrganizations,
  reviewDealFact,
} from "../api/client";
import type { Deal, DealFact, DealMessage, Organization } from "../api/types";
import DealConversationReview from "./DealConversationReview";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
    listOrganizations: vi.fn(),
    reviewDealFact: vi.fn(),
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
    expect(within(deliveryFact).getByText("private")).toBeInTheDocument();
    expect(within(deliveryFact).getByText(/extracted · unconfirmed/i)).toBeInTheDocument();
    expect(
      screen.getByText(/confirming one records your review; it does not approve the deal/i),
    ).toBeInTheDocument();

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

    fireEvent.change(selector, { target: { value: SELLER_ID } });
    expect(await screen.findByText("Seller private message")).toBeInTheDocument();
    expect(await screen.findByText("Seller confidential floor")).toBeInTheDocument();
    expect(screen.queryByText("Buyer private message")).not.toBeInTheDocument();
    expect(screen.queryByText("Buyer confidential price")).not.toBeInTheDocument();
    expect(mockedListDealFacts).toHaveBeenLastCalledWith(DEAL.id, SELLER_ID);
    expect(mockedListDealMessages).toHaveBeenLastCalledWith(DEAL.id, SELLER_ID);
  });
});
