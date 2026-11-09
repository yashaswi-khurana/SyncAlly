import React from "react";
import type { CandidateComparisonResult } from "./sourcingTypes";

export interface SellerInquiryModalProps {
  isOpen: boolean;
  candidate: CandidateComparisonResult | null;
  subject: string;
  setSubject: (value: string) => void;
  body: string;
  setBody: (value: string) => void;
  copiedNotification: boolean;
  onCopyToClipboard: () => void;
  onInitiateDeal: () => void;
  onClose: () => void;
}

export const SellerInquiryModal: React.FC<SellerInquiryModalProps> = ({
  isOpen,
  candidate,
  subject,
  setSubject,
  body,
  setBody,
  copiedNotification,
  onCopyToClipboard,
  onInitiateDeal,
  onClose,
}) => {
  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !candidate) return null;

  return (
    <div
      className="modal-backdrop manual-fact-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="inquiry-modal-title"
      data-testid="inquiry-modal"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-dialog manual-fact-modal" aria-labelledby="inquiry-modal-title">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Trade Outreach</span>
            <h2 id="inquiry-modal-title">Seller Inquiry: {candidate.seller_organization_name}</h2>
          </div>
          <button type="button" className="deal-modal-close" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        <div>
          <label htmlFor="inquiry-subject">Subject</label>
          <input
            id="inquiry-subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="inquiry-body">Inquiry Letter Body</label>
          <textarea
            id="inquiry-body"
            rows={8}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </div>

        {copiedNotification && (
          <div role="status" className="toast-notification">
            Copied inquiry to clipboard!
          </div>
        )}

        <div className="modal-buttons panel-actions">
          <button type="button" className="button secondary" onClick={onCopyToClipboard}>
            Copy to Clipboard
          </button>
          <button type="button" className="button primary-deal-btn" onClick={onInitiateDeal}>
            Initiate Deal Room
          </button>
          <button type="button" className="button ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
