import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getDealFulfillment, recordDealFulfillment } from "../api/client";
import type { FulfillmentSnapshot } from "../api/types";
import FulfillmentPanel from "./FulfillmentPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getDealFulfillment: vi.fn(),
    recordDealFulfillment: vi.fn(),
  };
});

const mockedGetFulfillment = vi.mocked(getDealFulfillment);
const mockedRecordFulfillment = vi.mocked(recordDealFulfillment);

const SNAPSHOT: FulfillmentSnapshot = {
  deal_id: "deal-1",
  state: "EMPTY",
  agreement_version_id: "agreement-1",
  agreement_version_number: 1,
  terms_hash: "a".repeat(64),
  obligation_id: "obligation-1",
  planned_quantity: "2",
  unit: "boxes",
  destination: "Toronto",
  target_date: "2026-12-01",
  shipped_quantity: "0",
  observed_quantity: "0",
  confirmed_quantity: "0",
  fulfillment_version: 0,
  payment_complete: false,
  deal_completed: false,
  events: [],
};

const props = {
  dealId: "deal-1",
  buyerOrganizationId: "buyer-1",
  sellerOrganizationId: "seller-1",
  selectedOrganizationId: "seller-1",
};

describe("FulfillmentPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("records a seller shipment against the current agreement and refreshes totals", async () => {
    vi.stubGlobal("crypto", { randomUUID: () => "idempotency-1" });
    mockedGetFulfillment
      .mockResolvedValueOnce(SNAPSHOT)
      .mockResolvedValue({ ...SNAPSHOT, state: "READY", shipped_quantity: "1", fulfillment_version: 1 });

    const onChanged = vi.fn();
    render(<FulfillmentPanel {...props} onChanged={onChanged} />);
    await screen.findByText("Planned");
    fireEvent.change(screen.getByLabelText("Quantity (boxes)"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Record shipped" }));

    await waitFor(() => expect(mockedRecordFulfillment).toHaveBeenCalledWith("deal-1", {
      agreement_version_id: "agreement-1",
      terms_hash: "a".repeat(64),
      obligation_id: "obligation-1",
      organization_id: "seller-1",
      event_type: "SHIPPED",
      quantity: "1",
      expected_version: 0,
      idempotency_key: "idempotency-1",
    }));
    expect(onChanged).toHaveBeenCalledOnce();
    expect(await screen.findByText("1 boxes")).toBeTruthy();
  });

  it("shows access revocation when the capability check rejects a write", async () => {
    vi.stubGlobal("crypto", { randomUUID: () => "idempotency-2" });
    mockedGetFulfillment.mockResolvedValue(SNAPSHOT);
    mockedRecordFulfillment.mockRejectedValue(new ApiError(403, "Fulfillment capability required"));

    render(<FulfillmentPanel {...props} />);
    await screen.findByText("Planned");
    fireEvent.change(screen.getByLabelText("Quantity (boxes)"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Record shipped" }));

    expect(await screen.findByText(/membership or fulfillment permission is unavailable/i)).toBeTruthy();
  });

  it("lets the buyer choose observation or confirmation", async () => {
    mockedGetFulfillment.mockResolvedValue(SNAPSHOT);
    render(<FulfillmentPanel {...props} selectedOrganizationId="buyer-1" />);

    expect(await screen.findByLabelText("Delivery fact")).toBeTruthy();
    expect(screen.queryByRole("option", { name: /shipped/i })).toBeNull();
  });
});
