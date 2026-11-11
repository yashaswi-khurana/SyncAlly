import React from "react";

export interface BuyerRequirementFormProps {
  inputMode: "natural" | "structured";
  setInputMode: (mode: "natural" | "structured") => void;
  prompt: string;
  setPrompt: (value: string) => void;
  title: string;
  setTitle: (value: string) => void;
  category: string;
  setCategory: (value: string) => void;
  targetQuantity: string;
  setTargetQuantity: (value: string) => void;
  unit: string;
  setUnit: (value: string) => void;
  targetPrice: string;
  setTargetPrice: (value: string) => void;
  maxPrice: string;
  setMaxPrice: (value: string) => void;
  destinationCountryCode: string;
  setDestinationCountryCode: (value: string) => void;
  currency: string;
  setCurrency: (value: string) => void;
  minWarrantyMonths: string;
  setMinWarrantyMonths: (value: string) => void;
  inspectionRequirement: string;
  setInspectionRequirement: (value: string) => void;
  validationError: string | null;
  isEvaluating: boolean;
  confirmationPending: boolean;
  onEvaluate: () => void;
}

export const BuyerRequirementForm: React.FC<BuyerRequirementFormProps> = ({
  inputMode,
  setInputMode,
  prompt,
  setPrompt,
  title,
  setTitle,
  category,
  setCategory,
  targetQuantity,
  setTargetQuantity,
  unit,
  setUnit,
  targetPrice,
  setTargetPrice,
  maxPrice,
  setMaxPrice,
  destinationCountryCode,
  setDestinationCountryCode,
  currency,
  setCurrency,
  minWarrantyMonths,
  setMinWarrantyMonths,
  inspectionRequirement,
  setInspectionRequirement,
  validationError,
  isEvaluating,
  confirmationPending,
  onEvaluate,
}) => {
  let actionLabel = "Interpret requirements";
  if (isEvaluating) actionLabel = "Working…";
  else if (inputMode === "structured") actionLabel = "Evaluate Marketplace Listings";
  else if (confirmationPending) actionLabel = "Confirm requirements and evaluate";

  return (
    <div className="card sourcing-requirement-card">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Input Criteria</span>
          <h2>Buyer Sourcing Requirements</h2>
        </div>
        {/* Mode Switcher */}
        <div className="input-mode-switcher">
          <button
            type="button"
            className={inputMode === "natural" ? "active" : ""}
            onClick={() => setInputMode("natural")}
          >
            Natural Language Prompt
          </button>
          <button
            type="button"
            className={inputMode === "structured" ? "active" : ""}
            onClick={() => setInputMode("structured")}
          >
            Structured Field Controls
          </button>
        </div>
      </div>

      <section className="requirement-input-panel">
        {inputMode === "natural" ? (
          <div>
            <label htmlFor="requirement-prompt">Procurement Requirement</label>
            <textarea
              id="requirement-prompt"
              rows={4}
              placeholder="e.g. Need 1000 boxes of M8 Grade 316 stainless steel bolts delivered to Berlin by Dec 8..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>
        ) : (
          <div className="structured-fields-grid">
            <div>
              <label htmlFor="field-title">Item Title</label>
              <input id="field-title" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div>
              <label htmlFor="field-category">Category</label>
              <input id="field-category" value={category} onChange={(e) => setCategory(e.target.value)} />
            </div>
            <div>
              <label htmlFor="field-quantity">Target Quantity</label>
              <input id="field-quantity" value={targetQuantity} onChange={(e) => setTargetQuantity(e.target.value)} />
            </div>
            <div>
              <label htmlFor="field-unit">Unit</label>
              <input id="field-unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
            </div>
            <div>
              <label htmlFor="field-target-price">Target Unit Price{currency ? ` (${currency})` : ""}</label>
              <input id="field-target-price" value={targetPrice} onChange={(e) => setTargetPrice(e.target.value)} />
            </div>
            <div>
              <label htmlFor="field-max-price">Maximum Unit Price{currency ? ` (${currency})` : ""}</label>
              <input id="field-max-price" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} />
            </div>
          </div>
        )}

        <fieldset className="structured-fields-grid sourcing-confirmation-fields">
          <legend>Confirm sourcing controls</legend>
          <p>
            Required values must be stated in the prompt or entered here; missing commercial terms are never defaulted.
          </p>
          <div>
            <label htmlFor="field-destination-country">Delivery Country Code</label>
            <input
              id="field-destination-country"
              maxLength={2}
              placeholder="DE"
              value={destinationCountryCode}
              onChange={(e) => setDestinationCountryCode(e.target.value.toUpperCase())}
            />
          </div>
          <div>
            <label htmlFor="field-currency">Sourcing Currency</label>
            <input
              id="field-currency"
              maxLength={3}
              placeholder="USD"
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            />
          </div>
          <div>
            <label htmlFor="field-warranty">Minimum Warranty (months)</label>
            <input
              id="field-warranty"
              inputMode="numeric"
              value={minWarrantyMonths}
              onChange={(e) => setMinWarrantyMonths(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="field-inspection">Inspection Requirement</label>
            <select
              id="field-inspection"
              value={inspectionRequirement}
              onChange={(e) => setInspectionRequirement(e.target.value)}
            >
              <option value="">Select or specify in your prompt</option>
              <option value="FACTORY_MILL_CERTIFICATE">Factory / mill certificate</option>
              <option value="PRE_SHIPMENT_THIRD_PARTY">Pre-shipment third-party</option>
              <option value="BUYER_RECEIVING_INSPECTION">Buyer receiving inspection</option>
              <option value="NONE">No inspection requirement</option>
            </select>
          </div>
        </fieldset>

        {validationError && (
          <div role="alert" className="error-banner">
            {validationError}
          </div>
        )}

        <div className="panel-actions">
          <button type="button" className="button evaluate-button" onClick={onEvaluate} disabled={isEvaluating}>
            {actionLabel}
          </button>
        </div>
      </section>
    </div>
  );
};
