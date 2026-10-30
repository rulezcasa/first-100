import { Check, ChevronDown, Copy, Link2, Linkedin, Send } from 'lucide-react'
import { useState } from 'react'
import { DraftCard } from '../components/approve/DraftCard'
import { Button, Label, PageHeader, TierBadge } from '../components/ui'
import { copy } from '../copy'
import { useStore } from '../store'
import type { Draft, Lead } from '../types'

function LinkedInNote({ draft }: { draft: Draft }) {
  const { setDraftStatus } = useStore()
  const [copied, setCopied] = useState(false)
  return (
    <div className="flex items-start gap-3 rounded-lg border border-line bg-paper px-4 py-3">
      <Linkedin size={15} className="mt-0.5 shrink-0 text-info" />
      <p className="flex-1 text-[13px] text-ink-2">{draft.body}</p>
      <div className="flex shrink-0 gap-1">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            navigator.clipboard?.writeText(draft.body)
            setCopied(true)
          }}
        >
          {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? copy.approve.copied : copy.approve.copy}
        </Button>
        {draft.status === 'sent' ? (
          <span className="px-2 py-1 text-xs text-good">Sent</span>
        ) : (
          <Button size="sm" onClick={() => setDraftStatus(draft.id, 'sent')}>
            {copy.approve.markSent}
          </Button>
        )}
      </div>
    </div>
  )
}

function LeadQueueItem({ lead, drafts }: { lead: Lead; drafts: Draft[] }) {
  const [showFollowups, setShowFollowups] = useState(false)
  const emails = drafts.filter((d) => d.channel === 'email' && d.status !== 'rejected' && d.status !== 'sent')
  const note = drafts.find((d) => d.channel === 'linkedin')
  if (!emails.length) return null

  return (
    <section className="border-t border-line pt-6">
      <div className="mb-4 flex items-center gap-3">
        <h2 className="text-lg font-semibold">{lead.person_name}</h2>
        <span className="text-sm text-ink-2">
          {lead.title}, {lead.company}
        </span>
        <TierBadge tier={lead.tier} score={lead.score} />
        {lead.warm_path && (
          <span className="flex items-center gap-1 text-xs text-accent-ink">
            <Link2 size={12} /> {lead.warm_path}
          </span>
        )}
      </div>
      <p className="mb-4 max-w-3xl border-l-2 border-accent pl-3 text-[14.5px] leading-snug text-ink-2">
        {lead.story.map((s) => s.text).join(' ')}
      </p>

      <div className={emails.length > 1 ? 'grid grid-cols-2 gap-4' : 'max-w-xl'}>
        {emails.map((d) => (
          <DraftCard key={d.id} draft={d} />
        ))}
      </div>

      <button onClick={() => setShowFollowups((s) => !s)} className="mt-3 flex items-center gap-1 text-xs text-ink-3 hover:text-ink">
        <ChevronDown size={13} className={showFollowups ? 'rotate-180' : ''} /> {copy.approve.followups}
      </button>
      {showFollowups && (
        <ol className="mt-2 space-y-1.5 pl-4 text-[13px] text-ink-2">
          {emails[0].followups.map((f, i) => (
            <li key={i}>
              <span className="mr-2 font-mono text-[11px] text-ink-3">Day {(i + 1) * 3}</span>
              {f}
            </li>
          ))}
        </ol>
      )}

      {note && (
        <div className="mt-4">
          <Label className="mb-2">{copy.approve.linkedin}</Label>
          <LinkedInNote draft={note} />
        </div>
      )}
    </section>
  )
}

export function Approve() {
  const { leads, drafts, sendApproved } = useStore()
  const byLead = leads
    .map((l) => ({ lead: l, drafts: drafts.filter((d) => d.lead_id === l.id) }))
    .filter((x) => x.drafts.some((d) => d.channel === 'email' && (d.status === 'pending' || d.status === 'approved')))
    // pending first, then approved-but-unsent
    .sort((a, b) => Number(b.drafts.some((d) => d.status === 'pending')) - Number(a.drafts.some((d) => d.status === 'pending')))
  const approved = drafts.filter((d) => d.status === 'approved' && d.channel === 'email').length

  return (
    <>
      <PageHeader
        title={copy.approve.title}
        subtitle={copy.approve.subtitle}
        actions={
          <Button variant="primary" disabled={!approved} onClick={sendApproved}>
            <Send size={14} /> {copy.approve.sendApproved(approved)}
          </Button>
        }
      />
      {byLead.length ? (
        <div className="space-y-10">
          {byLead.map(({ lead, drafts }) => (
            <LeadQueueItem key={lead.id} lead={lead} drafts={drafts} />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-line-strong py-16 text-center text-ink-3">{copy.approve.empty}</div>
      )}
    </>
  )
}
