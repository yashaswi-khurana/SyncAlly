import React, { useEffect, useRef, useState } from "react";
import { MOCK_BUNDLED_LISTINGS } from "./bundledListings";
import { BuyerRequirementForm } from "./BuyerRequirementForm";
import { GapAnalysisInspector } from "./GapAnalysisInspector";
import { ListingComparisonView } from "./ListingComparisonView";
import { SellerInquiryModal } from "./SellerInquiryModal";
import {
  draftSourcingInquiry,
  evaluateSourcing,
  interpretSourcingRequirements,
} from "../api/client";
import type {
  BuyerRequirements as ApiBuyerRequirements,
  ComparisonResult,
  InterpretSourcingResponse,
  InterpretSourcingRequest,
} from "../api/types";
import type {
  CandidateComparisonResult,
  CommercialGap,
  SourcingHubProps,
} from "./sourcingTypes";
import SplitText from "../ui/SplitText";
import "./sourcing.css";

export const SourcingHubPage: React.FC<SourcingHubProps> = ({
  onDealInitiated,
  initialListings = MOCK_BUNDLED_LISTINGS,
  initialListingId,
}) => {
  const [prompt, setPrompt] = useState("");
  const [inputMode, setInputMode] = useState<"natural" | "structured">("natural");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [targetQuantity, setTargetQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [destinationCountryCode, setDestinationCountryCode] = useState("");
  const [currency, setCurrency] = useState("");
  const [minWarrantyMonths, setMinWarrantyMonths] = useState("");
  const [inspectionRequirement, setInspectionRequirement] = useState("");
  const [selectedSector, setSelectedSector] = useState("All");

  const [activeCandidates, setActiveCandidates] = useState<CandidateComparisonResult[]>(initialListings);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateComparisonResult | null>(() => {
    if (initialListingId) {
      const match = initialListings.find((c) => c.listing_id === initialListingId);
      if (match) return match;
    }
    return initialListings[0] || null;
  });
  const [inspectedGap, setInspectedGap] = useState<CommercialGap | null>(null);
  const [isInquiryModalOpen, setIsInquiryModalOpen] = useState(false);
  const [inquirySubject, setInquirySubject] = useState("");
  const [inquiryBody, setInquiryBody] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [copiedNotification, setCopiedNotification] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [currentRequirements, setCurrentRequirements] = useState<ApiBuyerRequirements | null>(null);
  const [interpretationSource, setInterpretationSource] = useState<string | null>(null);
  const [pendingRequirements, setPendingRequirements] = useState<ApiBuyerRequirements | null>(null);
  const [pendingSignature, setPendingSignature] = useState<string | null>(null);
  const mounted = useRef(true);
  const requirementsGeneration = useRef(0);
  const evaluationGeneration = useRef(0);
  const selectionGeneration = useRef(0);
  const inquiryGeneration = useRef(0);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      requirementsGeneration.current += 1;
      evaluationGeneration.current += 1;
      selectionGeneration.current += 1;
      inquiryGeneration.current += 1;
    };
  }, []);

  const invalidateRequirements = () => {
    requirementsGeneration.current += 1;
    evaluationGeneration.current += 1;
    inquiryGeneration.current += 1;
    setIsEvaluating(false);
    setCurrentRequirements(null);
    setPendingRequirements(null);
    setPendingSignature(null);
    setInterpretationSource(null);
    setValidationError(null);
    setIsInquiryModalOpen(false);
  };

  const updateRequirement = <T,>(
    setter: React.Dispatch<React.SetStateAction<T>>,
    value: React.SetStateAction<T>,
  ) => {
    invalidateRequirements();
    setter(value);
  };

  const createOverrides = () => {
    if (inputMode === "structured") {
      if (!title.trim() || !category.trim() || !targetQuantity.trim() || !unit.trim()) {
        throw new Error("Enter an item title, category, positive quantity, and unit.");
      }
      if (!destinationCountryCode.trim() || !currency.trim() || !minWarrantyMonths.trim() || !inspectionRequirement) {
        throw new Error("Confirm the delivery country, currency, warranty, and inspection requirement.");
      }
      const quantity = Number(targetQuantity);
      const warranty = Number(minWarrantyMonths);
      if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isInteger(warranty) || warranty < 0) {
        throw new Error("Enter a positive quantity and a non-negative whole-number warranty in months.");
      }
      return {
        title: title.trim(),
        category: category.trim(),
        description: title.trim(),
        technical_specs: { materials: [], certifications: [], standards: [] },
        pricing: {
          target_unit_price: targetPrice.trim() || null,
          max_unit_price: maxPrice.trim() || null,
          currency: currency.trim().toUpperCase(),
        },
        quantity: { target_quantity: targetQuantity.trim(), unit: unit.trim() },
        delivery: { destination_country_code: destinationCountryCode.trim().toUpperCase() },
        commercial_terms: {
          acceptable_incoterms: [],
          min_warranty_months: warranty,
          inspection_requirement: inspectionRequirement,
        },
        raw_prompt: null,
      };
    }

    const overrides: Record<string, unknown> = {};
    if (targetQuantity.trim() || unit.trim()) {
      overrides.quantity = {
        ...(targetQuantity.trim() ? { target_quantity: targetQuantity.trim() } : {}),
        ...(unit.trim() ? { unit: unit.trim() } : {}),
      };
    }
    if (targetPrice.trim() || maxPrice.trim() || currency.trim()) {
      overrides.pricing = {
        ...(targetPrice.trim() ? { target_unit_price: targetPrice.trim() } : {}),
        ...(maxPrice.trim() ? { max_unit_price: maxPrice.trim() } : {}),
        ...(currency.trim() ? { currency: currency.trim().toUpperCase() } : {}),
      };
    }
    if (destinationCountryCode.trim()) {
      overrides.delivery = { destination_country_code: destinationCountryCode.trim().toUpperCase() };
    }
    if (minWarrantyMonths.trim() || inspectionRequirement) {
      overrides.commercial_terms = {
        ...(minWarrantyMonths.trim() ? { min_warranty_months: Number(minWarrantyMonths) } : {}),
        ...(inspectionRequirement ? { inspection_requirement: inspectionRequirement } : {}),
      };
    }
    return overrides;
  };

  const mapComparison = (result: ComparisonResult): CandidateComparisonResult => {
    const catalogueListing = initialListings.find((item) => item.listing_id === result.listing_id);
    return {
      listing_id: result.listing_id,
      seller_organization_id: result.seller_organization_id,
      organization_id: result.seller_organization_id,
      seller_organization_name: result.seller_organization_name,
      country_code: result.country_code,
      listing_title: result.listing_title,
      category: result.category || catalogueListing?.category || "Catalogue demo",
      unit_price: result.unit_price,
      currency: result.currency,
      available_quantity: result.available_quantity,
      moq: result.moq ?? "Not specified",
      lead_time_days: result.lead_time_days,
      match_tier:
        result.match_tier ||
        (result.tier.replace("Tier ", "") as CandidateComparisonResult["match_tier"]),
      composite_score: result.composite_score,
      completeness_tier:
        result.completeness_tier || catalogueListing?.completeness_tier || "UNKNOWN",
      attribute_matrix: (result.attribute_matrix || result.attribute_comparisons || []).map((row) => {
        const detailed = "display_name" in row;
        return {
          attribute: row.attribute || (detailed ? row.display_name : "Requirement"),
          buyer_requirement: row.buyer_requirement || (detailed ? row.buyer_value : ""),
          candidate_value: row.candidate_value || (detailed ? row.seller_value : "") || "Not specified",
          variance: row.variance,
          status: row.status === "ACCEPTABLE_VARIANCE" ? "ACCEPTABLE" : row.status,
        };
      }),
      gaps: result.gaps || result.detected_gaps || [],
    };
  };

  const handleSelectCandidate = (candidate: CandidateComparisonResult) => {
    evaluationGeneration.current += 1;
    selectionGeneration.current += 1;
    inquiryGeneration.current += 1;
    setIsEvaluating(false);
    setIsInquiryModalOpen(false);
    setSelectedCandidate(candidate);
  };

  const handleEvaluate = async () => {
    if (isEvaluating) return;
    const requestId = ++evaluationGeneration.current;
    const requirementsId = requirementsGeneration.current;
    const selectionId = selectionGeneration.current;
    const isCurrent = () =>
      mounted.current &&
      evaluationGeneration.current === requestId &&
      requirementsGeneration.current === requirementsId &&
      selectionGeneration.current === selectionId;
    setValidationError(null);
    setIsEvaluating(true);
    try {
      const overrides = createOverrides();
      if (inputMode === "natural" && !prompt.trim()) {
        throw new Error("Please enter sourcing requirements.");
      }
      const signature = `${inputMode}|${prompt.trim()}|${JSON.stringify(overrides)}`;
      const mustConfirm = inputMode === "natural" &&
        (!pendingRequirements || pendingSignature !== signature);
      if (mustConfirm) {
        setPendingRequirements(null);
        setPendingSignature(null);
      }
      const interpretation = mustConfirm || inputMode === "structured"
        ? await interpretSourcingRequirements({
            ...(inputMode === "natural" ? { prompt: prompt.trim() } : {}),
            structured_overrides: overrides,
          } as InterpretSourcingRequest) as InterpretSourcingResponse & {
            ai_provider?: string;
            ai_model?: string | null;
            fallback_reason?: string | null;
          }
        : { requirements: pendingRequirements as ApiBuyerRequirements };
      if (!isCurrent()) return;
      if (mustConfirm) {
        const aiStatus = interpretation as InterpretSourcingResponse & {
          ai_provider?: string;
          ai_model?: string | null;
          fallback_reason?: string | null;
        };
        setPendingRequirements(interpretation.requirements);
        setPendingSignature(signature);
        setInterpretationSource(
          `AI interpreted by ${aiStatus.ai_provider || "configured provider"}${aiStatus.ai_model ? ` · ${aiStatus.ai_model}` : ""}${aiStatus.fallback_reason ? ` · fallback: ${aiStatus.fallback_reason}` : ""}`,
        );
        return;
      }
      const report = await evaluateSourcing({ requirements: interpretation.requirements });
      if (!isCurrent()) return;
      const candidates = report.comparisons.map(mapComparison);
      selectionGeneration.current += 1;
      inquiryGeneration.current += 1;
      setCurrentRequirements(interpretation.requirements);
      if (inputMode === "structured") setInterpretationSource("Structured user controls");
      setPendingRequirements(null);
      setPendingSignature(null);
      setActiveCandidates(candidates);
      setSelectedCandidate(candidates[0] || null);
    } catch (error) {
      if (isCurrent()) {
        setValidationError(error instanceof Error ? error.message : "Sourcing evaluation failed. Please retry.");
      }
    } finally {
      if (mounted.current && evaluationGeneration.current === requestId) {
        setIsEvaluating(false);
      }
    }
  };

  const handleOpenInquiry = async (candidate: CandidateComparisonResult) => {
    if (!currentRequirements) {
      setValidationError("Interpret and evaluate requirements before drafting an inquiry.");
      return;
    }
    evaluationGeneration.current += 1;
    selectionGeneration.current += 1;
    const selectedId = selectionGeneration.current;
    const requirementsId = requirementsGeneration.current;
    const requestId = ++inquiryGeneration.current;
    setIsEvaluating(false);
    setSelectedCandidate(candidate);
    setValidationError(null);
    setIsInquiryModalOpen(false);
    try {
      const draft = await draftSourcingInquiry({
        requirements: currentRequirements,
        listing_id: candidate.listing_id,
      });
      if (
        !mounted.current ||
        inquiryGeneration.current !== requestId ||
        requirementsGeneration.current !== requirementsId ||
        selectionGeneration.current !== selectedId
      ) return;
      setInquirySubject(draft.subject);
      setInquiryBody(draft.body);
      setIsInquiryModalOpen(true);
    } catch (error) {
      if (
        mounted.current &&
        inquiryGeneration.current === requestId &&
        requirementsGeneration.current === requirementsId &&
        selectionGeneration.current === selectedId
      ) {
        setValidationError(error instanceof Error ? error.message : "Could not draft the seller inquiry.");
      }
    }
  };

  const handleCopyToClipboard = () => {
    void navigator.clipboard?.writeText(inquiryBody);
    setCopiedNotification(true);
    setTimeout(() => setCopiedNotification(false), 2000);
  };

  const handleInitiateDeal = () => {
    if (!selectedCandidate) return;
    const sellerOrgId =
      selectedCandidate.seller_organization_id ||
      selectedCandidate.organization_id ||
      "";
    const dealQuantity = currentRequirements?.quantity.target_quantity ?? targetQuantity;
    const dealUrl = `#/deals/new?listingId=${selectedCandidate.listing_id}&sellerId=${sellerOrgId}&sellerOrganizationId=${sellerOrgId}&initiatorParty=BUYER&quantity=${dealQuantity}&unitPrice=${selectedCandidate.unit_price}`;
    window.location.hash = dealUrl;
    if (onDealInitiated) onDealInitiated(dealUrl);
    setIsInquiryModalOpen(false);
  };

  return (
    <div className="sourcing-hub-container" data-testid="sourcing-hub-page">
      <header className="sourcing-hub-header">
        <nav aria-label="Breadcrumb" className="breadcrumbs">
          <span>Marketplace</span> &gt; <span>Sourcing Hub</span>
        </nav>
        <h1><SplitText text="Buyer Sourcing Agent" /></h1>
        <p className="subtitle">
          AI interprets buyer requirements; deterministic backend scoring and inquiry templates use a bundled demo catalogue.
        </p>
      </header>

      <div role="note" className="sourcing-demo-notice">
        <strong>Demo catalogue:</strong> bundled sample suppliers and listing data are not verified marketplace offers.
        Candidate ranking and gap arithmetic are deterministic, not AI-generated.
        {interpretationSource && <span> Requirement source: {interpretationSource}.</span>}
      </div>

      {/* Dual-Mode Buyer Requirement Input Form */}
      <BuyerRequirementForm
        inputMode={inputMode}
        setInputMode={(value) => updateRequirement(setInputMode, value)}
        prompt={prompt}
        setPrompt={(value) => updateRequirement(setPrompt, value)}
        title={title}
        setTitle={(value) => updateRequirement(setTitle, value)}
        category={category}
        setCategory={(value) => updateRequirement(setCategory, value)}
        targetQuantity={targetQuantity}
        setTargetQuantity={(value) => updateRequirement(setTargetQuantity, value)}
        unit={unit}
        setUnit={(value) => updateRequirement(setUnit, value)}
        targetPrice={targetPrice}
        setTargetPrice={(value) => updateRequirement(setTargetPrice, value)}
        maxPrice={maxPrice}
        setMaxPrice={(value) => updateRequirement(setMaxPrice, value)}
        destinationCountryCode={destinationCountryCode}
        setDestinationCountryCode={(value) => updateRequirement(setDestinationCountryCode, value)}
        currency={currency}
        setCurrency={(value) => updateRequirement(setCurrency, value)}
        minWarrantyMonths={minWarrantyMonths}
        setMinWarrantyMonths={(value) => updateRequirement(setMinWarrantyMonths, value)}
        inspectionRequirement={inspectionRequirement}
        setInspectionRequirement={(value) => updateRequirement(setInspectionRequirement, value)}
        validationError={validationError}
        onEvaluate={handleEvaluate}
        isEvaluating={isEvaluating}
        confirmationPending={Boolean(pendingRequirements && inputMode === "natural")}
      />

      {pendingRequirements && inputMode === "natural" && (
        <div className="sourcing-confirmation-summary" role="status">
          <strong>Review the interpreted requirements before ranking:</strong>
          <span>{pendingRequirements.title} · {pendingRequirements.category}</span>
          <span>
            {pendingRequirements.quantity.target_quantity} {pendingRequirements.quantity.unit} to{" "}
            {pendingRequirements.delivery.destination_country_code}
          </span>
          <span>
            Currency: {pendingRequirements.pricing.currency}; warranty:{" "}
            {pendingRequirements.commercial_terms.min_warranty_months} months; inspection:{" "}
            {pendingRequirements.commercial_terms.inspection_requirement}
          </span>
        </div>
      )}

      {/* Side-by-Side Candidate Listings and Detailed Comparison View */}
      <ListingComparisonView
        candidates={activeCandidates}
        selectedCandidate={selectedCandidate}
        onSelectCandidate={handleSelectCandidate}
        onOpenInquiry={handleOpenInquiry}
        selectedSector={selectedSector}
        onSectorChange={setSelectedSector}
      >
        {selectedCandidate && (
          <GapAnalysisInspector
            gaps={selectedCandidate.gaps}
            inspectedGap={inspectedGap}
            onInspectGap={setInspectedGap}
          />
        )}
      </ListingComparisonView>

      {/* Seller Inquiry Modal */}
      <SellerInquiryModal
        isOpen={isInquiryModalOpen}
        candidate={selectedCandidate}
        subject={inquirySubject}
        setSubject={setInquirySubject}
        body={inquiryBody}
        setBody={setInquiryBody}
        copiedNotification={copiedNotification}
        onCopyToClipboard={handleCopyToClipboard}
        onInitiateDeal={handleInitiateDeal}
        onClose={() => setIsInquiryModalOpen(false)}
      />
    </div>
  );
};

export const ReferenceSourcingHub = SourcingHubPage;
export default SourcingHubPage;
