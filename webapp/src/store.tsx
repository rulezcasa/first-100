// App state. Leads come from the backend; the rest is local and in-memory so the design is clickable.
// Each local action is where an api.ts call goes later.
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from './api'
import * as mock from './mock'
import type { Draft, Lead, Profile, Proposal, RoomEvent, Stage } from './types'

// If Researcher never reports back (Ollama stopped, turn failed), stop showing a lead as busy after this long.
const RESEARCH_TIMEOUT_MS = 5 * 60_000

interface Store {
  profiles: Profile[]
  profile: Profile
  leads: Lead[]
  researching: number[] // lead ids Researcher has been asked to check and hasn't finished
  drafts: Draft[]
  proposal: Proposal | null
  setProfile: (p: Profile) => void // the latest profile, as loaded from the backend
  researchLead: (id: number) => void
  setDraftStatus: (id: number, status: Draft['status']) => void
  editDraft: (id: number, patch: Partial<Pick<Draft, 'subject' | 'body'>>) => void
  sendApproved: () => void
  simulateReplies: () => void
  moveLead: (id: number, stage: Stage) => void
  acceptProposal: () => void
  dismissProposal: () => void
}

const Ctx = createContext<Store | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [profiles, setProfiles] = useState<Profile[]>([mock.profileV1])
  const [leads, setLeads] = useState<Lead[]>([])
  const [researching, setResearching] = useState<number[]>([])
  // Empty until Writer saves real drafts: mock drafts point at mock lead ids, which now belong to real leads.
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [proposal, setProposal] = useState<Proposal | null>(mock.proposal)

  const profile = profiles[profiles.length - 1]

  // Load leads, then reload whenever an agent's tool finishes in the room (find_companies saves new leads).
  useEffect(() => {
    const load = () =>
      api.getLeads().then((ls) => {
        setLeads(ls)
        // A lead with a tier has been researched, so it's no longer waiting.
        setResearching((ids) => ids.filter((id) => !ls.find((l) => l.id === id)?.tier))
      }, (e) => console.error(e))
    load()
    const stream = new EventSource(api.activityStreamUrl)
    stream.onmessage = (m) => {
      const e: RoomEvent = JSON.parse(m.data)
      if (e.kind !== 'tool_result' || e.from_founder) return
      load()
    }
    return () => stream.close()
  }, [])

  useEffect(() => {
    if (!researching.length) return
    const t = setTimeout(() => setResearching([]), RESEARCH_TIMEOUT_MS)
    return () => clearTimeout(t)
  }, [researching])

  const store: Store = {
    profiles,
    profile,
    leads,
    researching,
    drafts,
    proposal,
    setProfile: (p) => setProfiles((ps) => [...ps.filter((x) => x.version < p.version), p]),
    // Asks Researcher in the room; the lead updates when research_lead finishes.
    researchLead: (id) => {
      const lead = leads.find((l) => l.id === id)
      if (!lead || researching.includes(id)) return
      setResearching((ids) => [...ids, id])
      api.sendToTeam(`@Researcher research ${lead.company} (lead ${id}).`).catch((e) => {
        console.error(e)
        setResearching((ids) => ids.filter((x) => x !== id))
      })
    },
    setDraftStatus: (id, status) => {
      const d = drafts.find((x) => x.id === id)
      setDrafts((ds) =>
        ds.map((x) => {
          if (x.id === id) return { ...x, status }
          // approving one email variant retires the other
          if (status === 'approved' && d && x.lead_id === d.lead_id && x.channel === 'email' && x.status === 'pending') return { ...x, status: 'rejected' }
          return x
        }),
      )
      if (status === 'approved' && d) setLeads((ls) => ls.map((l) => (l.id === d.lead_id && l.stage === 'found' ? { ...l, stage: 'approved', source: 'ai' } : l)))
    },
    editDraft: (id, patch) => setDrafts((ds) => ds.map((x) => (x.id === id ? { ...x, ...patch } : x))),
    sendApproved: () => {
      const ids = new Set(drafts.filter((d) => d.status === 'approved' && d.channel === 'email').map((d) => d.lead_id))
      setDrafts((ds) => ds.map((d) => (d.status === 'approved' && d.channel === 'email' ? { ...d, status: 'sent' } : d)))
      setLeads((ls) => ls.map((l) => (ids.has(l.id) ? { ...l, stage: 'sent' } : l)))
    },
    simulateReplies: () => {
      setLeads((ls) => ls.map((l) => (l.stage === 'sent' && l.industry !== 'Retail' ? { ...l, stage: 'replied' } : l)))
    },
    moveLead: (id, stage) => setLeads((ls) => ls.map((l) => (l.id === id ? { ...l, stage, source: 'founder' } : l))),
    acceptProposal: () => {
      if (!proposal) return
      setProfiles((ps) => {
        const prev = ps[ps.length - 1]
        const segments = prev.segments.filter((s) => s.name !== 'Mid-size retailers')
        return [
          ...ps,
          {
            ...prev,
            version: prev.version + 1,
            industries: prev.industries.filter((i) => i !== 'Retail'),
            segments,
            change_note: 'Focus on logistics; dropped retail; signal emails by default.',
            created_at: new Date().toISOString(),
          },
        ]
      })
      setProposal(null)
    },
    dismissProposal: () => setProposal(null),
  }

  return <Ctx.Provider value={store}>{children}</Ctx.Provider>
}

export function useStore() {
  const s = useContext(Ctx)
  if (!s) throw new Error('useStore outside StoreProvider')
  return s
}
