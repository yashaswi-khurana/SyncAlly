import React, { useState } from "react";
import {
  BUNDLED_MARKETPLACE_LISTING_DETAILS,
  MOCK_BUNDLED_LISTINGS,
} from "./bundledListings";
import { BuyerRequirementForm } from "./BuyerRequirementForm";
import { GapAnalysisInspector } from "./GapAnalysisInspector";
import { ListingComparisonView } from "./ListingComparisonView";
import { SellerInquiryModal } from "./SellerInquiryModal";
import {
  draftSellerInquiry,
  evaluateCandidateListing,
  interpretPrompt,
} from "./sourcingEngine";
import type {
  BuyerRequirements,
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
  const [title, setTitle] = useState("M8x30 Grade 316 Stainless Steel Hex Cap Bolts");
  const [category, setCategory] = useState("Industrial Fasteners");
  const [targetQuantity, setTargetQuantity] = useState("1000");
  const [unit, setUnit] = useState("boxes");
  const [targetPrice, setTargetPrice] = useState("12.00");
  const [maxPrice, setMaxPrice] = useState("14.00");
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

  const handleEvaluate = () => {
    let requirements: BuyerRequirements;

    if (inputMode === "natural") {
      if (!prompt.trim()) {
        setValidationError("Please enter sourcing requirements");
        return;
      }
      setValidationError(null);
      requirements = interpretPrompt(prompt);
      if (requirements.quantity.target_quantity) {
        setTargetQuantity(requirements.quantity.target_quantity);
      }
      if (requirements.quantity.unit) {
        setUnit(requirements.quantity.unit);
      }
    } else {
      if (
        !title.trim() ||
        !targetQuantity.trim() ||
        parseFloat(targetQuantity) <= 0 ||
        isNaN(parseFloat(targetQuantity))
      ) {
        setValidationError("Please enter requirement title and positive quantity");
        return;
      }
      setValidationError(null);
      const parsedTargetPrice = targetPrice.trim() ? targetPrice.trim() : null;
      const parsedMaxPrice = maxPrice.trim() ? maxPrice.trim() : null;

      requirements = {
        title: title.trim(),
        category: category.trim() || "Industrial Fasteners",
        description: title.trim(),
        technical_specs: {
          materials: [],
          certifications: [],
          standards: [],
        },
        pricing: {
          target_unit_price: parsedTargetPrice,
          max_unit_price: parsedMaxPrice,
          currency: "USD",
        },
        quantity: {
          target_quantity: targetQuantity.trim(),
          unit: unit.trim() || "units",
        },
        delivery: {
          destination_country_code: "DE",
          max_lead_time_days: 30,
        },
        commercial_terms: {
          preferred_incoterm: "DDP",
          acceptable_incoterms: ["DDP", "CIF", "FOB"],
          min_warranty_months: 12,
          inspection_requirement: "FACTORY_MILL_CERTIFICATE",
        },
        raw_prompt: null,
      };
    }

    const evaluated = BUNDLED_MARKETPLACE_LISTING_DETAILS.map((listing) =>
      evaluateCandidateListing(listing, requirements)
    );

    evaluated.sort((a, b) => b.composite_score - a.composite_score);

    setActiveCandidates(evaluated);
    setSelectedCandidate(evaluated[0] || null);
  };

  const handleOpenInquiry = (candidate: CandidateComparisonResult) => {
    setSelectedCandidate(candidate);
    const draft = draftSellerInquiry(candidate, targetQuantity, unit);
    setInquirySubject(draft.subject);
    setInquiryBody(draft.body);
    setIsInquiryModalOpen(true);
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
    const dealUrl = `#/deals/new?listingId=${selectedCandidate.listing_id}&sellerId=${sellerOrgId}&sellerOrganizationId=${sellerOrgId}&initiatorParty=BUYER&quantity=${targetQuantity}&unitPrice=${selectedCandidate.unit_price}`;
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
        <h1><SplitText text="Production Buyer Sourcing Agent" /></h1>
        <p className="subtitle">
          Interpret buyer requirements, evaluate realistic marketplace listings, detect commercial gaps, and draft targeted seller inquiries.
        </p>
      </header>

      {/* Dual-Mode Buyer Requirement Input Form */}
      <BuyerRequirementForm
        inputMode={inputMode}
        setInputMode={setInputMode}
        prompt={prompt}
        setPrompt={setPrompt}
        title={title}
        setTitle={setTitle}
        category={category}
        setCategory={setCategory}
        targetQuantity={targetQuantity}
        setTargetQuantity={setTargetQuantity}
        unit={unit}
        setUnit={setUnit}
        targetPrice={targetPrice}
        setTargetPrice={setTargetPrice}
        maxPrice={maxPrice}
        setMaxPrice={setMaxPrice}
        validationError={validationError}
        onEvaluate={handleEvaluate}
      />

      {/* Side-by-Side Candidate Listings and Detailed Comparison View */}
      <ListingComparisonView
        candidates={activeCandidates}
        selectedCandidate={selectedCandidate}
        onSelectCandidate={setSelectedCandidate}
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
