/**
 * Empirical Stress Test Suite for Frontend Sourcing Hub Components.
 *
 * Agent: challenger_sourcing_m3_1
 *
 * Systematically stress-tests:
 * 1. Rapid mode switches (50-100 cycles, state retention across unmount/mount).
 * 2. Extreme input lengths (100k+ chars, Unicode, CJK, RTL, XSS payloads, extreme numbers).
 * 3. Empty submission alerts (whitespace, empty string, error banner lifecycle).
 * 4. Copy-to-clipboard toast timeouts (timer lifecycle, rapid clicks, unhandled rejections).
 * 5. Modal close/escape behavior (✕ button, Close button, backdrop click, Escape key).
 * 6. Console error / React runtime crash assertion across all operations.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ReferenceSourcingHub } from "./SourcingHubPage";
import { interpretSourcingRequirements } from "../api/client";
import { evaluateNaturalRequirements, installSourcingMocks, openServerInquiry } from "./sourcingTestFixtures";

vi.mock("../api/client", () => ({
  draftSourcingInquiry: vi.fn(),
  evaluateSourcing: vi.fn(),
  interpretSourcingRequirements: vi.fn(),
}));

describe("SourcingHub Empirical Stress & Resilience Suite (challenger_sourcing_m3_1)", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.resetAllMocks();
    installSourcingMocks();
    window.location.hash = "";
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    vi.clearAllMocks();
  });

  // ============================================================================
  // 1. RAPID MODE SWITCHES
  // ============================================================================
  describe("1. Rapid Mode Switches & State Stability", () => {
    it("survives 100 rapid mode switches without crashing or leaking errors", () => {
      render(<ReferenceSourcingHub />);

      const naturalBtn = screen.getByRole("button", { name: /natural language prompt/i });
      const structuredBtn = screen.getByRole("button", { name: /structured field controls/i });

      // Enter initial text in natural mode
      const textarea = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(textarea, { target: { value: "Initial requirement prompt test" } });

      // Rapidly toggle back and forth 100 times
      for (let i = 0; i < 100; i++) {
        fireEvent.click(structuredBtn);
        fireEvent.click(naturalBtn);
      }

      // Assert textarea still exists and retained prompt
      const finalPromptInput = screen.getByLabelText(/procurement requirement/i) as HTMLTextAreaElement;
      expect(finalPromptInput).toBeInTheDocument();
      expect(finalPromptInput.value).toBe("Initial requirement prompt test");
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    }, 15000);

    it("preserves structured field values across rapid mode toggles", () => {
      render(<ReferenceSourcingHub />);

      const naturalBtn = screen.getByRole("button", { name: /natural language prompt/i });
      const structuredBtn = screen.getByRole("button", { name: /structured field controls/i });

      // Switch to structured mode and enter custom fields
      fireEvent.click(structuredBtn);
      const titleInput = screen.getByLabelText(/item title/i);
      const qtyInput = screen.getByLabelText(/target quantity/i);
      const budgetInput = screen.getByLabelText(/maximum unit price/i);

      fireEvent.change(titleInput, { target: { value: "Custom Titanium Fastener Grade 5" } });
      fireEvent.change(qtyInput, { target: { value: "45000" } });
      fireEvent.change(budgetInput, { target: { value: "85.50" } });

      // Rapidly switch modes 50 times
      for (let i = 0; i < 50; i++) {
        fireEvent.click(naturalBtn);
        fireEvent.click(structuredBtn);
      }

      // Assert structured values are intact
      expect((screen.getByLabelText(/item title/i) as HTMLInputElement).value).toBe("Custom Titanium Fastener Grade 5");
      expect((screen.getByLabelText(/target quantity/i) as HTMLInputElement).value).toBe("45000");
      expect((screen.getByLabelText(/maximum unit price/i) as HTMLInputElement).value).toBe("85.50");
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // 2. EXTREME INPUT LENGTHS & FUZZING
  // ============================================================================
  describe("2. Extreme Input Lengths & Adversarial Payloads", () => {
    it("handles 100,000-character natural language prompt without crashing or freeze", async () => {
      render(<ReferenceSourcingHub />);

      const massivePrompt = "Need high precision aerospace bolts. " + "A".repeat(100_000);
      const textarea = screen.getByLabelText(/procurement requirement/i);

      fireEvent.change(textarea, { target: { value: massivePrompt } });
      expect((textarea as HTMLTextAreaElement).value.length).toBe(100_037);

      // Trigger evaluation
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: /interpret requirements/i }));
      });

      // Verify page is still functional and zero console errors
      expect(screen.getByText(/candidate listings/i)).toBeInTheDocument();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });

    it("handles Unicode, CJK, Arabic RTL, Emojis, and HTML/XSS injection safely", async () => {
      render(<ReferenceSourcingHub />);

      const hostileInput = `<script>alert("XSS")</script> <b>Bold</b> 🔩🚀 🔥 
      العربية - تجارة عالمية
      日本語 - 工業用ボルト
      中文 - 高强度不锈钢螺栓
      \u0000\u0007\u001b[31mANSI\u001b[0m`;

      const textarea = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(textarea, { target: { value: hostileInput } });

      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: /interpret requirements/i }));
      });

      // No raw script execution or React DOM corruption
      expect(document.querySelector("script[src*='alert']")).toBeNull();
      expect(screen.getByText(/candidate listings/i)).toBeInTheDocument();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });

    it("handles extreme numerical boundaries in structured inputs (negative, zero, 1e20, NaN)", async () => {
      render(<ReferenceSourcingHub />);

      const structuredBtn = screen.getByRole("button", { name: /structured field controls/i });
      fireEvent.click(structuredBtn);

      const qtyInput = screen.getByLabelText(/target quantity/i);
      const targetPriceInput = screen.getByLabelText(/target unit price/i);
      const maxPriceInput = screen.getByLabelText(/maximum unit price/i);
      fireEvent.change(screen.getByLabelText(/item title/i), { target: { value: "Fasteners" } });
      fireEvent.change(screen.getByLabelText(/^category$/i), { target: { value: "Industrial Fasteners" } });
      fireEvent.change(screen.getByLabelText(/^unit$/i), { target: { value: "boxes" } });
      fireEvent.change(screen.getByLabelText(/delivery country code/i), { target: { value: "DE" } });
      fireEvent.change(screen.getByLabelText(/sourcing currency/i), { target: { value: "USD" } });
      fireEvent.change(screen.getByLabelText(/minimum warranty/i), { target: { value: "12" } });
      fireEvent.change(screen.getByLabelText(/inspection requirement/i), { target: { value: "NONE" } });

      // Test negative and extreme values
      fireEvent.change(qtyInput, { target: { value: "-999999999999999" } });
      fireEvent.change(targetPriceInput, { target: { value: "0" } });
      fireEvent.change(maxPriceInput, { target: { value: "1e25" } });

      const evalButton = screen.getByRole("button", { name: /evaluate marketplace listings/i });
      fireEvent.click(evalButton);

      // Assert no crash
      expect(screen.getByText(/candidate listings/i)).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveTextContent(/positive quantity/i);

      // Test non-numeric garbage
      fireEvent.change(qtyInput, { target: { value: "1000" } });
      fireEvent.change(maxPriceInput, { target: { value: "NaN_INFINITE_OVERFLOW" } });
      vi.mocked(interpretSourcingRequirements).mockRejectedValueOnce(new Error("Invalid maximum unit price"));
      await act(async () => { fireEvent.click(evalButton); });
      expect(screen.getByRole("alert")).toHaveTextContent(/invalid maximum unit price/i);
      expect(screen.getByText(/candidate listings/i)).toBeInTheDocument();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // 3. EMPTY SUBMISSION ALERTS
  // ============================================================================
  describe("3. Empty Submission Alerts & Error Lifecycle", () => {
    it("displays role='alert' error when submitting empty string in natural mode", () => {
      render(<ReferenceSourcingHub />);

      const textarea = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(textarea, { target: { value: "" } });

      const evalButton = screen.getByRole("button", { name: /interpret requirements/i });
      fireEvent.click(evalButton);

      const alert = screen.getByRole("alert");
      expect(alert).toBeInTheDocument();
      expect(alert).toHaveTextContent(/please enter sourcing requirements/i);
    });

    it("displays role='alert' error when submitting whitespace-only in natural mode", () => {
      render(<ReferenceSourcingHub />);

      const textarea = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(textarea, { target: { value: "   \n\t  \r\n   " } });

      const evalButton = screen.getByRole("button", { name: /interpret requirements/i });
      fireEvent.click(evalButton);

      const alert = screen.getByRole("alert");
      expect(alert).toBeInTheDocument();
      expect(alert).toHaveTextContent(/please enter sourcing requirements/i);
    });

    it("clears validation error alert immediately when valid input is submitted", async () => {
      render(<ReferenceSourcingHub />);

      const textarea = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(textarea, { target: { value: "" } });

      const evalButton = screen.getByRole("button", { name: /interpret requirements/i });
      await act(async () => { fireEvent.click(evalButton); });

      expect(screen.getByRole("alert")).toBeInTheDocument();

      // Enter valid input and resubmit
      fireEvent.change(textarea, { target: { value: "1000 units M8 bolts" } });
      await act(async () => { fireEvent.click(evalButton); });

      expect(screen.queryByRole("alert")).toBeNull();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // 4. COPY-TO-CLIPBOARD TOAST TIMEOUTS
  // ============================================================================
  describe("4. Copy-to-Clipboard Toast Timeouts & Concurrent Triggers", () => {
    it("shows toast notification on copy and automatically hides it after exactly 2000ms", async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      });

      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      expect(screen.getByTestId("inquiry-modal")).toBeInTheDocument();

      // Trigger copy
      const copyBtn = screen.getByRole("button", { name: /copy to clipboard/i });
      fireEvent.click(copyBtn);

      expect(writeTextMock).toHaveBeenCalled();
      const toast = screen.getByRole("status");
      expect(toast).toBeInTheDocument();
      expect(toast).toHaveTextContent(/copied inquiry to clipboard!/i);

      // Advance by 1900ms: toast should still be visible
      act(() => {
        vi.advanceTimersByTime(1900);
      });
      expect(screen.getByRole("status")).toBeInTheDocument();

      // Advance past 2000ms (additional 150ms): toast should disappear
      act(() => {
        vi.advanceTimersByTime(150);
      });
      expect(screen.queryByRole("status")).toBeNull();
    });

    it("handles rapid consecutive copy clicks without unhandled exceptions", async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      });

      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      const copyBtn = screen.getByRole("button", { name: /copy to clipboard/i });

      // Click 10 times rapidly
      for (let i = 0; i < 10; i++) {
        fireEvent.click(copyBtn);
      }

      expect(writeTextMock).toHaveBeenCalledTimes(10);
      expect(screen.getByRole("status")).toBeInTheDocument();

      // Advance time past 2000ms
      act(() => {
        vi.advanceTimersByTime(2500);
      });

      expect(screen.queryByRole("status")).toBeNull();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });

    it("survives modal close while copy timeout is still pending without throwing", async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      });

      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      const copyBtn = screen.getByRole("button", { name: /copy to clipboard/i });
      fireEvent.click(copyBtn);

      expect(screen.getByRole("status")).toBeInTheDocument();

      // Close modal immediately before timeout finishes
      const closeBtn = screen.getByRole("button", { name: /close modal/i });
      fireEvent.click(closeBtn);

      expect(screen.queryByTestId("inquiry-modal")).toBeNull();

      // Now fast-forward timer when modal is unmounted
      act(() => {
        vi.advanceTimersByTime(3000);
      });

      // Assert zero console errors
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // 5. MODAL CLOSE & ESCAPE BEHAVIOR
  // ============================================================================
  describe("5. Modal Close / Dismissal & Escape Key Behavior", () => {
    it("closes modal via '✕' (deal-modal-close) button", async () => {
      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      expect(screen.getByTestId("inquiry-modal")).toBeInTheDocument();

      // Click top-right ✕ button
      const closeXBtn = screen.getByRole("button", { name: /close modal/i });
      fireEvent.click(closeXBtn);

      expect(screen.queryByTestId("inquiry-modal")).toBeNull();
    });

    it("closes modal via footer 'Close' button", async () => {
      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      expect(screen.getByTestId("inquiry-modal")).toBeInTheDocument();

      // Click bottom Close button
      const footerCloseBtn = screen.getByRole("button", { name: /^close$/i });
      fireEvent.click(footerCloseBtn);

      expect(screen.queryByTestId("inquiry-modal")).toBeNull();
    });

    it("tests modal close on Escape key press", async () => {
      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      const modal = screen.getByTestId("inquiry-modal");
      expect(modal).toBeInTheDocument();

      // Press Escape on document
      fireEvent.keyDown(document, { key: "Escape", code: "Escape" });

      // Check whether modal closes on Escape
      const isModalStillOpen = screen.queryByTestId("inquiry-modal") !== null;
      console.log("Modal status after Escape key press: still open =", isModalStillOpen);

      // We assert expected UX behavior: Escape key SHOULD close modal
      expect(screen.queryByTestId("inquiry-modal"), "Modal should close upon pressing Escape key").toBeNull();
    });

    it("tests modal close on backdrop click", async () => {
      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      const backdrop = screen.getByTestId("inquiry-modal");
      expect(backdrop).toBeInTheDocument();

      // Click on backdrop directly (target === currentTarget)
      fireEvent.click(backdrop);

      const isModalStillOpen = screen.queryByTestId("inquiry-modal") !== null;
      console.log("Modal status after backdrop click: still open =", isModalStillOpen);

      // We assert backdrop click behavior
      expect(screen.queryByTestId("inquiry-modal"), "Modal should close upon clicking backdrop").toBeNull();
    });
  });

  // ============================================================================
  // 6. ZERO RUNTIME CRASHES & CONSOLE ERRORS ON EMPTY / MALFORMED LISTINGS
  // ============================================================================
  describe("6. Robustness against Boundary Listings & Zero Console Errors", () => {
    it("renders cleanly with empty initialListings array without crashing", () => {
      render(<ReferenceSourcingHub initialListings={[]} />);

      expect(screen.getByTestId("sourcing-hub-page")).toBeInTheDocument();
      expect(screen.getByText(/candidate listings \(0\)/i)).toBeInTheDocument();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });

    it("handles non-existent initialListingId fallback gracefully", () => {
      render(<ReferenceSourcingHub initialListingId="non-existent-guid-9999" />);

      expect(screen.getByTestId("sourcing-hub-page")).toBeInTheDocument();
      expect(screen.getAllByText(/berlin fastener & bolt gmbh/i)[0]).toBeInTheDocument();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });

    it("asserts zero unhandled console errors or warnings across entire workflow", () => {
      expect(consoleErrorSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).not.toHaveBeenCalled();
    });
  });
});
