import { FileSearch, Link2, Loader2, Plus } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { LeadDrawer } from '../components/leads/LeadDrawer'
import { Button, cx, Drawer, EmailStatusBadge, PageHeader, SourceTag, TierBadge } from '../components/ui'
import { copy } from '../copy'
import { useStore } from '../store'
import type { Tier } from '../types'

const filters: ('All' | Tier)[] = ['All', 'A', 'B', 'C']

export function Leads() {
  const { leads, researching, researchLead } = useStore()
  const [tier, setTier] = useState<'All' | Tier>('All')
  const [params, setParams] = useSearchParams()
  const open = leads.find((l) => l.id === Number(params.get('lead')))
  const setOpenId = (id: number | null) => setParams(id ? { lead: String(id) } : {})

  // Scored leads by score; unchecked ones (newest first, as the backend sends them) after.
  const rows = leads.filter((l) => tier === 'All' || l.tier === tier).sort((a, b) => (b.score ?? -1) - (a.score ?? -1))

  return (
    <>
      <PageHeader
        title={copy.leads.title}
        subtitle={copy.leads.subtitle}
        actions={
          <>
            <Button>
              <Plus size={14} /> {copy.leads.addLead}
            </Button>
          </>
        }
      />

      <div className="mb-4 flex items-center gap-1">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setTier(f)}
            className={cx(
              'rounded-md px-3 py-1.5 text-xs font-medium',
              tier === f ? 'bg-ink text-paper' : 'text-ink-2 hover:bg-sunken',
            )}
          >
            {f === 'All' ? `All ${leads.length}` : `Tier ${f} · ${leads.filter((l) => l.tier === f).length}`}
          </button>
        ))}
      </div>

      {leads.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line bg-surface px-6 py-14 text-center">
          <div className="font-medium">{copy.leads.empty}</div>
          <p className="mx-auto mt-1 max-w-sm text-sm text-ink-3">{copy.leads.emptyHint}</p>
        </div>
      ) : (
      <div className="overflow-hidden rounded-xl border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-wider text-ink-3">
              <th className="px-5 py-3 font-medium">Company</th>
              <th className="px-3 py-3 font-medium">Person</th>
              <th className="px-3 py-3 font-medium">Fit</th>
              <th className="px-3 py-3 font-medium">Why now</th>
              <th className="px-5 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <tr
                key={l.id}
                onClick={() => setOpenId(l.id)}
                className={cx('cursor-pointer border-b border-line last:border-0 hover:bg-paper', l.tier === 'C' && 'opacity-55')}
              >
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2 font-medium">
                    {l.company} <SourceTag source={l.source} />
                  </div>
                  <div className="text-xs text-ink-3">{[l.industry, l.size].filter(Boolean).join(' · ')}</div>
                </td>
                <td className="px-3 py-3.5">
                  {l.person_name ? (
                    <>
                      <div>{l.person_name}</div>
                      <div className="flex items-center gap-2 text-xs text-ink-3">
                        {l.title} {l.email_status && <EmailStatusBadge status={l.email_status} />}
                      </div>
                    </>
                  ) : l.tier ? (
                    <span className="text-xs text-ink-3">No contact found</span>
                  ) : (
                    <Button
                      size="sm"
                      title={copy.leads.researchHint}
                      disabled={researching.includes(l.id)}
                      onClick={(e) => {
                        e.stopPropagation() // don't open the drawer
                        researchLead(l.id)
                      }}
                    >
                      {researching.includes(l.id) ? <Loader2 size={12} className="animate-spin" /> : <FileSearch size={12} />}
                      {researching.includes(l.id) ? copy.leads.researching : copy.leads.research}
                    </Button>
                  )}
                </td>
                <td className="px-3 py-3.5">
                  <TierBadge tier={l.tier} score={l.score} />
                </td>
                <td className="max-w-[300px] px-3 py-3.5 text-[13px] text-ink-2">
                  <span className="line-clamp-2">{l.story[0]?.text ?? l.evidence[0]?.quote ?? 'Nothing recent found'}</span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  {l.warm_path && (
                    <span title={l.warm_path} className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent-ink">
                      <Link2 size={11} /> {l.warm_via?.name}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}

      <Drawer open={!!open} onClose={() => setOpenId(null)}>
        {open && <LeadDrawer key={open.id} lead={open} />}
      </Drawer>
    </>
  )
}
