import { ExternalLink, FileSearch, Link2, Loader2, Mail, RotateCcw, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { copy } from '../../copy'
import { useStore } from '../../store'
import type { Lead } from '../../types'
import { Button, cx, EmailStatusBadge, Label, SourceTag, TierBadge, usd } from '../ui'
import { LeadGraph } from './LeadGraph'

const host = (url: string) => new URL(url).hostname.replace('www.', '')
const date = (d: string) => new Date(d).toLocaleDateString([], { month: 'short', day: 'numeric' })

export function LeadDrawer({ lead }: { lead: Lead }) {
  const [hl, setHl] = useState<{ id: number; tick: number } | null>(null)
  const { researching, researchLead } = useStore()
  const busy = researching.includes(lead.id)
  const num = (id: number) => lead.evidence.findIndex((e) => e.id === id) + 1

  const jump = (id: number) => {
    setHl((h) => ({ id, tick: (h?.tick ?? 0) + 1 }))
    document.getElementById(`ev-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const total = lead.cost.research + lead.cost.contact + lead.cost.writing

  return (
    <div className="px-8 pb-12 pt-8">
      <div className="flex items-center gap-2 text-xs text-ink-3">
        {[lead.industry, lead.size, lead.domain].filter(Boolean).map((x, i) => (
          <span key={i} className={cx(x === lead.domain && 'font-mono')}>
            {i > 0 && '· '}
            {x}
          </span>
        ))}
        <SourceTag source={lead.source} />
      </div>
      <div className="mt-2 flex items-center gap-3">
        <h2 className="font-display text-[34px] font-semibold leading-none tracking-[-0.03em]">{lead.company}</h2>
        <TierBadge tier={lead.tier} score={lead.score} />
      </div>
      {lead.score_note && <p className="mt-2 text-sm text-ink-2">{lead.score_note}</p>}

      {/* Why now */}
      <section className="mt-8">
        <Label className="mb-3">{copy.leads.whyNow}</Label>
        {lead.story.length ? (
          <p className="font-display text-[21px] font-medium leading-[1.45] tracking-[-0.01em] text-ink">
            {lead.story.map((s, i) => (
              <span key={i}>
                {s.text}
                {s.refs.map((r) => (
                  <button
                    key={r}
                    onClick={() => jump(r)}
                    className="mx-0.5 -translate-y-2 rounded bg-accent-soft px-1 align-baseline font-mono text-[11px] font-medium text-accent-ink hover:bg-accent hover:text-on-accent"
                  >
                    {num(r)}
                  </button>
                ))}{' '}
              </span>
            ))}
          </p>
        ) : lead.tier && lead.evidence.length ? (
          <p className="text-ink-3">Writer hasn't written the story yet. What Researcher verified is below.</p>
        ) : lead.tier ? (
          <p className="text-ink-3">Nothing recent could be verified for this company, so there's no story yet.</p>
        ) : (
          <p className="text-ink-3">Researcher hasn't checked this company yet. {copy.leads.foundBecause} is below.</p>
        )}
      </section>

      {/* Warm path */}
      {lead.warm_path && (
        <div className="mt-6 flex items-center gap-3 rounded-lg border border-accent bg-accent-soft/70 px-4 py-3">
          <Link2 size={16} className="text-accent-ink" />
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-accent-ink">{copy.leads.warmPath}</div>
            <div className="text-sm font-medium">{lead.warm_path}</div>
          </div>
        </div>
      )}

      {/* Contact */}
      <section className="mt-8">
        <Label className="mb-3">{copy.leads.contact}</Label>
        {lead.person_name ? (
          <div className="flex items-center gap-4 rounded-xl border border-line bg-surface p-4">
            <div className="flex size-10 items-center justify-center rounded-full bg-info-soft font-semibold text-info">
              {lead.person_name.split(' ').map((w) => w[0]).join('')}
            </div>
            <div className="flex-1">
              <div className="font-medium">{lead.person_name}</div>
              <div className="text-xs text-ink-2">{lead.title}</div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-1.5 font-mono text-xs">
                <Mail size={12} className="text-ink-3" />
                {lead.email}
              </div>
              {lead.email_status && <EmailStatusBadge status={lead.email_status} />}
            </div>
          </div>
        ) : !lead.tier ? (
          <div className="flex items-center justify-between gap-4 rounded-xl border border-dashed border-line p-4">
            <p className="text-sm text-ink-3">{copy.leads.researchHint}</p>
            <Button variant="primary" disabled={busy} onClick={() => researchLead(lead.id)}>
              {busy ? <Loader2 size={14} className="animate-spin" /> : <FileSearch size={14} />}
              {busy ? copy.leads.researching : copy.leads.research}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-ink-3">{copy.leads.noEmail}</p>
        )}
      </section>

      {/* Evidence */}
      {lead.evidence.length > 0 && (
        <section className="mt-8">
          <Label className="mb-3">{lead.tier ? copy.leads.sources : copy.leads.foundBecause}</Label>
          <ol className="space-y-2">
            {lead.evidence.map((e, i) => (
              <li
                key={hl?.id === e.id ? `${e.id}-${hl.tick}` : e.id}
                id={`ev-${e.id}`}
                className={cx('flex gap-3 rounded-lg border border-line bg-surface p-3.5', hl?.id === e.id && 'flash')}
              >
                <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded bg-accent-soft font-mono text-[11px] font-medium text-accent-ink">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[14.5px] leading-snug text-ink">“{e.quote}”</p>
                  <a href={e.url} target="_blank" rel="noreferrer" className="mt-1.5 flex items-center gap-1.5 text-xs text-ink-3 hover:text-ink">
                    <span className="truncate">{e.title}</span>
                    <span>·</span>
                    <span className="font-mono">{host(e.url)}</span>
                    <span>·</span>
                    <span title={e.published_at ? 'When it happened' : 'When we found it'}>{date(e.published_at ?? e.fetched_at)}</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
                <span className="h-fit rounded bg-sunken px-1.5 py-0.5 text-[10px] text-ink-2">{e.signal_type.replace('_', ' ')}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Graph */}
      <section className="mt-8">
        <Label className="mb-3">{copy.leads.graph}</Label>
        <LeadGraph lead={lead} width={574} />
      </section>

      {/* Cost */}
      <section className="mt-8 flex items-center justify-between rounded-lg bg-sunken px-4 py-3 text-xs">
        <span className="text-ink-2">{copy.leads.cost}</span>
        <span className="flex gap-4 text-ink-3">
          <span>research {usd(lead.cost.research)}</span>
          <span>contact {usd(lead.cost.contact)}</span>
          <span>writing {usd(lead.cost.writing)}</span>
          <span className="font-mono font-medium text-ink">{usd(total)}</span>
        </span>
      </section>

      <div className="mt-8 flex gap-2">
        <Button variant="primary">
          <Sparkles size={14} /> {copy.leads.findMore}
        </Button>
        <Button title="Tell the Researcher what's wrong and it will dig again">
          <RotateCcw size={14} /> {copy.leads.lookAgain}
        </Button>
      </div>
    </div>
  )
}
