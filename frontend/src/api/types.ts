export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Organization {
  id: string;
  legal_name: string;
  country_code: string;
  role: string;
}

export interface Deal {
  id: string;
  buyer_organization_id: string;
  seller_organization_id: string;
  status: string;
  version: number;
}

export type ViewerRole = "BUYER" | "SELLER" | "BOTH";

export interface DealSummary extends Deal {
  viewer_role: ViewerRole;
}

export interface CreateDealInput {
  buyer_organization_id: string;
  seller_organization_id: string;
}

export interface CreateOrganizationInput {
  legal_name: string;
  country_code: string;
}

export interface OrganizationMember {
  user_id: string;
  email: string;
  role: string;
}
