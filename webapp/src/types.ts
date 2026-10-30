// Shapes mirror the SQLite tables in PLAN.md §2 so wiring up api.ts later is a straight swap.

export type Tier = 'A' | 'B' | 'C'
export type EmailStatus = 'valid' | 'risky' | 'unknown'
export type Stage = 'found' | 'approved' | 'sent' | 'replied' | 'meeting'
export type Source = 'ai' | 'founder'
export type Angle = 'signal' | 'pain'
export type SignalType = 'funding' | 'hiring' | 'expansion' | 'new_exec' | 'product_launch' | 'other'
export type AgentName = 'Team' | 'Scout' | 'Researcher' | 'Writer' | 'Learner' | 'You'

export interface Founder {
  name: string
  past_companies: string[]
  schools: string[]
  investors: string[]
}

/** What setup captures about the product (app/models.py Product). */
export interface Product {
  product: string
  buyer_roles: string[]
  industries: string[]
  pains: string[]
}

export interface SetupMessage {
  role: 'founder' | 'scout'
  text: string
}

/** The setup draft, held only in the browser until it's finalized. */
export interface SetupDraft {
  messages: SetupMessage[]
  product: Product
  founder: Founder
  skipped: string[] // required details the founder chose to skip
}

/** What setup last finalized (GET /setup); `saved` is false before the first finalize or after starting over. */
export interface SavedSetup extends SetupDraft {
  saved: boolean
}

export interface SetupTurn {
  reply: string
  product: Product
  founder: Founder
  skipped: string[]
}

export interface Segment {
  name: string
  why: string
  confidence: number // 0–1
}

export interface Profile {
  version: number
  product: string
  buyer_roles: string[]
  industries: string[]
  pains: string[]
  segments: Segment[]
  expansion: string[]
  competitors: { name: string; note: string }[]
  change_note: string | null
  created_at: string | null // null before setup is saved
}

export interface Evidence {
  id: number
  url: string
  title: string
  quote: string
  signal_type: SignalType
  fetched_at: string
  published_at?: string | null // when the page says it happened, if known
}

export interface StorySentence {
  text: string
  refs: number[] // evidence ids
}

export interface Lead {
  id: number
  company: string
  domain: string
  industry: string
  size: string
  person_name: string | null
  title: string | null
  email: string | null
  email_status: EmailStatus | null
  tier: Tier | null // null until Researcher has checked it
  score: number | null
  score_note?: string | null // Researcher's one-line reason for the fit
  story: StorySentence[]
  evidence: Evidence[]
  warm_path: string | null
  warm_via: { kind: 'Company' | 'School' | 'Investor'; name: string } | null
  profile_version: number
  stage: Stage
  source: Source
  cost: { research: number; contact: number; writing: number }
  updated_at: string
}

export interface Draft {
  id: number
  lead_id: number
  channel: 'email' | 'linkedin'
  variant: 'A' | 'B'
  angle: Angle
  subject: string
  body: string
  followups: string[]
  status: 'pending' | 'approved' | 'rejected' | 'sent'
}

/** One message in the Band room, as the activity panel draws it (app/band/room.py). */
export interface RoomEvent {
  id: string
  kind: 'text' | 'tool_call' | 'tool_result' | 'error'
  sender: string // Band display name, e.g. 'Scout'
  from_founder: boolean
  text: string // the message; for tool_call / tool_result, the tool's name
  is_error: boolean
  created_at: string | null
}

export interface Proposal {
  title: string
  detail: string
  changes: string[]
}

export interface GraphNode {
  id: string
  label: string
  kind: 'Founder' | 'Company' | 'Person' | 'Signal' | 'School' | 'Investor'
}

export interface GraphLink {
  source: string
  target: string
  rel: string
  warm?: boolean
}

// GET /dashboard
export type DealStatus = 'potential' | 'confirmed' | 'lost'
export type Deal = {
  lead_id: number
  company: string
  person_name: string | null
  industry: string | null
  status: DealStatus
  value_usd: number
  note: string | null
  updated_at: string
}
export type Dashboard = {
  source: 'flexprice' | 'local' // where cost and revenue were read from
  sync: { connected: boolean; pending_events: number; sent_events: number; error: string | null }
  cost: {
    total_usd: number
    calls: number
    tokens: number
    per_lead_usd: number | null
    per_reply_usd: number | null
    per_client_usd: number | null
    by_agent: { agent: string; calls: number; tokens: number; cost_usd: number }[]
    daily: { day: string; cost_usd: number }[]
  }
  clients: { leads: number; contacted: number; replied: number; meetings: number; potential: number; confirmed: number; lost: number }
  revenue: { confirmed_usd: number; pipeline_usd: number; avg_deal_usd: number | null; net_usd: number; roi: number | null }
  reply_rates: { by_industry: ReplyRate[]; by_angle: ReplyRate[] }
  deals: Deal[]
}
export type ReplyRate = { key: string; sent: number; replied: number }
