export interface SkillMatch {
  match_rate: number
  matched: string[]
  missing: string[]
}

export interface ScoreBreakdown {
  semantic_similarity: number
  skill_match: SkillMatch
  title_relevance: number
  experience_match: string
}

export interface MatchResponse {
  overall_score: number
  breakdown: ScoreBreakdown
  recommendations: string[]
  processing_time_ms: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserPublic {
  id: string
  email: string
  plan: string
  scan_count: number
  created_at: string
}

export interface ScanRecord {
  id: string
  endpoint: string
  overall_score: number
  job_snippet: string
  created_at: string
}

export interface PaginatedScans {
  items: ScanRecord[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface BillingStatusResponse {
  plan: string
  scan_count: number
  scan_limit: number | null
  stripe_customer_id: string | null
}

export interface CheckoutResponse {
  checkout_url: string
}

export interface PortalResponse {
  portal_url: string
}
