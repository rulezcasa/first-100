// Design-time data for pages not yet wired to the backend (setup is live; see api.ts).
import type { Draft, Evidence, GraphLink, GraphNode, Lead, Profile, Proposal, RateRow } from './types'

export const profileV1: Profile = {
  version: 1,
  product: 'Shelfwise: live inventory tracking for mid-size warehouses, without the spreadsheet',
  buyer_roles: ['COO', 'VP Operations', 'Head of Fulfillment', 'Warehouse Director'],
  industries: ['Logistics', '3PL', 'E-commerce fulfillment', 'Retail'],
  pains: ['Stock counts drift from reality', 'Mis-picks and late orders', 'New sites take months to get right'],
  segments: [
    { name: 'Regional logistics companies', why: 'Run several sites, feel count drift the most, and buy ops tools without a long IT process.', confidence: 0.86 },
    { name: '3PL warehouses', why: 'Accuracy is what their customers pay for; one bad count can lose a contract.', confidence: 0.74 },
    { name: 'E-commerce brands with their own fulfillment', why: 'Growing fast and outgrowing spreadsheets, but often still small.', confidence: 0.58 },
    { name: 'Mid-size retailers', why: 'Real pain, but usually tied to a larger system already.', confidence: 0.41 },
  ],
  expansion: ['Cold-chain food distributors', 'Auto parts distributors'],
  competitors: [
    { name: 'Fishbowl', note: 'Popular with small warehouses; often outgrown at 3+ sites' },
    { name: 'NetSuite WMS', note: 'Bundled with the ERP; heavy to set up' },
    { name: 'Spreadsheets', note: 'The real competitor for most of these teams' },
  ],
  change_note: null,
  created_at: '2026-10-30T09:12:00Z',
}

let eid = 0
const ev = (url: string, title: string, quote: string, signal_type: Evidence['signal_type'], fetched_at: string): Evidence => ({
  id: ++eid,
  url,
  title,
  quote,
  signal_type,
  fetched_at,
})

const acme = [
  ev('https://example.com/news/acme-freight-dallas', 'Acme Freight opens second Dallas warehouse', 'Acme Freight has opened a 180,000 sq ft facility in south Dallas, its second in the metro area.', 'expansion', '2026-10-28'),
  ev('https://example.com/jobs/acme-freight', 'Careers at Acme Freight', 'We are hiring two Inventory Managers for our new Dallas site.', 'hiring', '2026-10-28'),
  ev('https://example.com/people/jane-doe', 'Jane Doe – COO, Acme Freight', 'Before Acme, Jane led fulfillment operations at Stripe.', 'other', '2026-10-28'),
]
const northpine = [
  ev('https://example.com/news/northpine-series-b', 'Northpine 3PL raises $24M Series B', 'Northpine 3PL raised $24 million to expand capacity across the Pacific Northwest.', 'funding', '2026-10-27'),
  ev('https://example.com/blog/northpine-accuracy', 'Why we obsess over pick accuracy', 'Our customers judge us on one number: did the right item ship.', 'other', '2026-10-27'),
]
const cartwheel = [
  ev('https://example.com/news/cartwheel-fulfillment', 'Cartwheel Goods brings fulfillment in-house', 'Cartwheel is moving fulfillment in-house after two years with an outside partner.', 'expansion', '2026-10-26'),
  ev('https://example.com/jobs/cartwheel-ops', 'Head of Inventory, Cartwheel Goods', 'You will own stock accuracy across our first owned warehouse.', 'hiring', '2026-10-26'),
]
const ridgeline = [
  ev('https://example.com/news/ridgeline-new-coo', 'Ridgeline names new COO', 'Ridgeline Distribution appointed Tom Becker as Director of Warehouse Operations in September.', 'new_exec', '2026-10-25'),
]
const harbor = [
  ev('https://example.com/news/harbor-hale-stores', 'Harbor & Hale adds 12 stores', 'The retailer plans 12 new stores in 2027, served from a single distribution center.', 'expansion', '2026-10-22'),
]
const loop = [
  ev('https://example.com/news/loop-parcel-seed', 'Loop Parcel raises seed round', 'Loop Parcel raised $6M to add two same-day hubs.', 'funding', '2026-10-18'),
  ev('https://example.com/jobs/loop-parcel', 'Ops Lead, Loop Parcel', 'Help us keep inventory accurate as we open new hubs.', 'hiring', '2026-10-18'),
]
const fernway = [
  ev('https://example.com/news/fernway-launch', 'Fernway launches outdoor rental line', 'Fernway Outfitters launched rentals, adding 3,000 SKUs to track.', 'product_launch', '2026-10-21'),
]
const meridian = [
  ev('https://example.com/news/meridian-cold-chain', 'Meridian Cold Chain opens Reno facility', 'Meridian opened a temperature-controlled site in Reno.', 'expansion', '2026-10-12'),
  ev('https://example.com/jobs/meridian', 'Inventory Control Manager, Meridian', 'Own cycle counts across three cold storage sites.', 'hiring', '2026-10-12'),
]

const cost = (research: number, contact: number, writing: number) => ({ research, contact, writing })

export const leads: Lead[] = [
  {
    id: 1, company: 'Acme Freight', domain: 'acmefreight.com', industry: 'Logistics', size: '220 people',
    person_name: 'Jane Doe', title: 'COO', email: 'jane@acmefreight.com', email_status: 'valid',
    tier: 'A', score: 87,
    story: [
      { text: 'They opened a second warehouse in Dallas this week', refs: [acme[0].id] },
      { text: 'and are hiring two inventory managers to run it.', refs: [acme[1].id] },
      { text: 'Their COO, Jane Doe, ran fulfillment at Stripe, so she has seen this problem at scale.', refs: [acme[2].id] },
    ],
    evidence: acme, warm_path: 'You both worked at Stripe', warm_via: { kind: 'Company', name: 'Stripe' },
    profile_version: 1, stage: 'found', source: 'ai', cost: cost(0.06, 0.04, 0.03), updated_at: '2026-10-30T09:41:00Z',
  },
  {
    id: 2, company: 'Northpine 3PL', domain: 'northpine.co', industry: '3PL', size: '140 people',
    person_name: 'Marcus Lee', title: 'VP Operations', email: 'marcus@northpine.co', email_status: 'valid',
    tier: 'A', score: 82,
    story: [
      { text: 'Northpine just raised $24M to add capacity across the Pacific Northwest.', refs: [northpine[0].id] },
      { text: 'They say publicly that pick accuracy is the number their customers judge them on.', refs: [northpine[1].id] },
    ],
    evidence: northpine, warm_path: 'You both went to Stanford', warm_via: { kind: 'School', name: 'Stanford University' },
    profile_version: 1, stage: 'found', source: 'ai', cost: cost(0.05, 0.04, 0.03), updated_at: '2026-10-30T09:40:00Z',
  },
  {
    id: 3, company: 'Cartwheel Goods', domain: 'cartwheelgoods.com', industry: 'E-commerce', size: '90 people',
    person_name: 'Dana Ortiz', title: 'Head of Fulfillment', email: 'dana@cartwheelgoods.com', email_status: 'risky',
    tier: 'B', score: 71,
    story: [
      { text: 'Cartwheel is bringing fulfillment in-house after two years with an outside partner', refs: [cartwheel[0].id] },
      { text: 'and is hiring someone to own stock accuracy in their first warehouse.', refs: [cartwheel[1].id] },
    ],
    evidence: cartwheel, warm_path: 'You are both backed by Y Combinator', warm_via: { kind: 'Investor', name: 'Y Combinator' },
    profile_version: 1, stage: 'found', source: 'ai', cost: cost(0.05, 0.04, 0.02), updated_at: '2026-10-30T09:38:00Z',
  },
  {
    id: 4, company: 'Ridgeline Distribution', domain: 'ridgelinedist.com', industry: 'Logistics', size: '310 people',
    person_name: 'Tom Becker', title: 'Director of Warehouse Ops', email: 'tbecker@ridgelinedist.com', email_status: 'valid',
    tier: 'B', score: 68,
    story: [{ text: 'Tom Becker took over warehouse operations in September; new leaders tend to review their tools early.', refs: [ridgeline[0].id] }],
    evidence: ridgeline, warm_path: null, warm_via: null,
    profile_version: 1, stage: 'approved', source: 'ai', cost: cost(0.04, 0.04, 0.03), updated_at: '2026-10-30T09:20:00Z',
  },
  {
    id: 5, company: 'Harbor & Hale', domain: 'harborandhale.com', industry: 'Retail', size: '400 people',
    person_name: 'Sofia Marin', title: 'VP Supply Chain', email: 'sofia.marin@harborandhale.com', email_status: 'unknown',
    tier: 'B', score: 64,
    story: [{ text: 'They plan 12 new stores next year, all served from one distribution center.', refs: [harbor[0].id] }],
    evidence: harbor, warm_path: null, warm_via: null,
    profile_version: 1, stage: 'sent', source: 'ai', cost: cost(0.05, 0.04, 0.03), updated_at: '2026-10-29T16:02:00Z',
  },
  {
    id: 6, company: 'Loop Parcel', domain: 'loopparcel.com', industry: 'Logistics', size: '75 people',
    person_name: 'Ken Ito', title: 'COO', email: 'ken@loopparcel.com', email_status: 'valid',
    tier: 'A', score: 79,
    story: [
      { text: 'Loop Parcel raised $6M to add two same-day hubs', refs: [loop[0].id] },
      { text: 'and is hiring an ops lead to keep inventory accurate as they open.', refs: [loop[1].id] },
    ],
    evidence: loop, warm_path: null, warm_via: null,
    profile_version: 1, stage: 'replied', source: 'ai', cost: cost(0.05, 0.03, 0.03), updated_at: '2026-10-29T14:10:00Z',
  },
  {
    id: 7, company: 'Fernway Outfitters', domain: 'fernway.com', industry: 'Retail', size: '260 people',
    person_name: 'Ava Brooks', title: 'Operations Manager', email: 'ava@fernway.com', email_status: 'valid',
    tier: 'B', score: 61,
    story: [{ text: 'Their new rental line adds about 3,000 items to track.', refs: [fernway[0].id] }],
    evidence: fernway, warm_path: null, warm_via: null,
    profile_version: 1, stage: 'sent', source: 'ai', cost: cost(0.04, 0.04, 0.03), updated_at: '2026-10-29T15:55:00Z',
  },
  {
    id: 8, company: 'Meridian Cold Chain', domain: 'meridiancold.com', industry: 'Logistics', size: '180 people',
    person_name: 'Leah Park', title: 'VP Operations', email: 'leah@meridiancold.com', email_status: 'valid',
    tier: 'A', score: 84,
    story: [
      { text: 'Meridian opened a temperature-controlled site in Reno', refs: [meridian[0].id] },
      { text: 'and is hiring someone to run cycle counts across all three sites.', refs: [meridian[1].id] },
    ],
    evidence: meridian, warm_path: 'You both worked at Flexport', warm_via: { kind: 'Company', name: 'Flexport' },
    profile_version: 1, stage: 'meeting', source: 'founder', cost: cost(0.05, 0.04, 0.03), updated_at: '2026-10-28T11:00:00Z',
  },
  {
    id: 9, company: 'Boxly Logistics', domain: 'boxly.io', industry: 'Logistics', size: '40 people',
    person_name: null, title: null, email: null, email_status: null,
    tier: 'C', score: 31,
    story: [],
    evidence: [], warm_path: null, warm_via: null,
    profile_version: 1, stage: 'found', source: 'ai', cost: cost(0.03, 0, 0), updated_at: '2026-10-30T09:39:00Z',
  },
]

let did = 0
const email = (lead_id: number, variant: 'A' | 'B', angle: Draft['angle'], subject: string, body: string, status: Draft['status'] = 'pending'): Draft => ({
  id: ++did, lead_id, channel: 'email', variant, angle, subject, body, status,
  followups: [
    'Quick nudge on this. Happy to show you a 10-minute version if easier.',
    'Last note from me. If timing is off, I will leave it here.',
  ],
})
const linkedin = (lead_id: number, body: string): Draft => ({
  id: ++did, lead_id, channel: 'linkedin', variant: 'A', angle: 'signal', subject: '', body, status: 'pending', followups: [],
})

export const drafts: Draft[] = [
  email(1, 'A', 'signal', 'Your second Dallas site',
    "Hi Jane,\n\nSaw Acme just opened the second Dallas warehouse. Congrats. When I ran fulfillment ops at Stripe, a new site was always when our counts drifted most.\n\nI built Shelfwise to keep stock counts live across sites without the spreadsheet. Would it be useful to see how it handles a new site going live?\n\nPriya"),
  email(1, 'B', 'pain', 'Counts across two sites',
    "Hi Jane,\n\nMost ops teams I talk to find out their counts are wrong when an order ships late. With two Dallas sites that gets harder to catch.\n\nI'm a former Stripe ops lead, now building Shelfwise to keep inventory live across warehouses. Open to a short look?\n\nPriya"),
  linkedin(1, 'Hi Jane, fellow ex-Stripe ops person here. Saw the new Dallas site, congrats. Building something for exactly that moment and would love to compare notes.'),
  email(2, 'A', 'signal', 'Congrats on the Series B',
    "Hi Marcus,\n\nCongrats on the $24M. Your post on pick accuracy stuck with me: it's the one number customers judge a 3PL on.\n\nShelfwise keeps stock counts live so accuracy holds as you add capacity. Worth 15 minutes before the new space fills up?\n\nPriya (Stanford '15)"),
  email(2, 'B', 'pain', 'Pick accuracy while you grow',
    "Hi Marcus,\n\nAdding capacity usually means accuracy dips for a quarter while counts catch up. That's the gap Shelfwise closes.\n\nI ran warehouse ops at Stripe before starting this. Would a quick walkthrough be useful?\n\nPriya"),
  linkedin(2, 'Hi Marcus, fellow Stanford alum. Loved your pick accuracy post. Building inventory tooling for 3PLs and would value your take.'),
  email(3, 'A', 'signal', 'Bringing fulfillment in-house',
    "Hi Dana,\n\nSaw Cartwheel is bringing fulfillment in-house. Exciting, and a lot to get right in the first warehouse.\n\nShelfwise gives you live stock counts from day one, no spreadsheet. We're YC too. Want me to send a 3-minute video?\n\nPriya"),
  email(3, 'B', 'pain', 'Your first warehouse',
    "Hi Dana,\n\nThe first owned warehouse is where stock counts usually go wrong, because nobody has set up the habits yet.\n\nI built Shelfwise for that. Happy to share what we've seen work. Open to it?\n\nPriya"),
  linkedin(3, 'Hi Dana, fellow YC founder here. Congrats on bringing fulfillment in-house. Building tools for exactly that and happy to share notes.'),
  email(4, 'A', 'signal', 'New role, new tools?',
    "Hi Tom,\n\nCongrats on taking over warehouse ops at Ridgeline. New leaders often look hard at how counts are done.\n\nShelfwise keeps inventory live across sites. Worth a look while you're getting set up?\n\nPriya", 'approved'),
]


export const funnel = { found: 37, approved: 30, sent: 30, replied: 9, meeting: 3 }

export const byIndustry: RateRow[] = [
  { key: 'Logistics', sent: 11, replied: 5, meetings: 2, cost: 0.11 },
  { key: '3PL', sent: 6, replied: 2, meetings: 1, cost: 0.12 },
  { key: 'E-commerce', sent: 5, replied: 1, meetings: 0, cost: 0.13 },
  { key: 'Retail', sent: 8, replied: 1, meetings: 0, cost: 0.14 },
]

export const byAngle: RateRow[] = [
  { key: 'signal', sent: 17, replied: 7, meetings: 3, cost: 0.12 },
  { key: 'pain', sent: 13, replied: 2, meetings: 0, cost: 0.13 },
]

export const spend = { total: 4.82, leads: 37 }

export const proposal: Proposal = {
  title: 'Focus on logistics, and lead with what just happened',
  detail: 'Logistics companies replied 45% of the time versus 13% for retail, and signal emails replied 41% versus 15% for pain emails.',
  changes: ['Move "Regional logistics companies" to the top', 'Drop "Mid-size retailers"', 'Use signal emails by default'],
}

export function leadSubgraph(lead: Lead): { nodes: GraphNode[]; links: GraphLink[] } {
  const co = `co:${lead.id}`
  const nodes: GraphNode[] = [{ id: co, label: lead.company, kind: 'Company' }]
  const links: GraphLink[] = []
  if (lead.person_name) {
    nodes.push({ id: 'person', label: lead.person_name, kind: 'Person' })
    links.push({ source: 'person', target: co, rel: 'WORKS_AT' })
  }
  lead.evidence
    .filter((e) => e.signal_type !== 'other')
    .forEach((e) => {
      nodes.push({ id: `sig:${e.id}`, label: e.signal_type.replace('_', ' '), kind: 'Signal' })
      links.push({ source: co, target: `sig:${e.id}`, rel: 'HAS_SIGNAL' })
    })
  if (lead.warm_via) {
    const v = lead.warm_via
    nodes.push({ id: 'founder', label: 'You', kind: 'Founder' }, { id: 'via', label: v.name, kind: v.kind })
    const rel = v.kind === 'Company' ? 'PREVIOUSLY_WORKED_AT' : v.kind === 'School' ? 'STUDIED_AT' : 'BACKED_BY'
    links.push({ source: 'founder', target: 'via', rel, warm: true })
    links.push({ source: v.kind === 'Investor' ? co : 'person', target: 'via', rel, warm: true })
  }
  return { nodes, links }
}
