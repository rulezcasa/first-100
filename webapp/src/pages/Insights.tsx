import { ArrowRight, Check, Lightbulb } from 'lucide-react'
import { Button, Card, cx, Label, PageHeader, pct, usd } from '../components/ui'
import { copy } from '../copy'
import { byAngle, byIndustry, funnel, spend } from '../mock'
import { useStore } from '../store'
import type { RateRow } from '../types'

function RateTable({ title, rows, labels }: { title: string; rows: RateRow[]; labels?: Record<string, string> }) {
  const rates = rows.map((r) => pct(r.replied, r.sent))
  const best = Math.max(...rates)
  const worst = Math.min(...rates)
  return (
    <Card className="p-5">
      <Label className="mb-4">{title}</Label>
      <div className="space-y-3">
        {rows.map((r, i) => {
          const rate = rates[i]
          const tone = rate === best ? 'good' : rate === worst ? 'bad' : 'mid'
          return (
            <div key={r.key} className="grid grid-cols-[110px_1fr_48px] items-center gap-3">
              <span className="text-sm capitalize" title={labels?.[r.key]}>
                {r.key}
              </span>
              <div className="relative h-6 overflow-hidden rounded bg-sunken">
                <div
                  className={cx('h-full rounded', tone === 'good' ? 'bg-good' : tone === 'bad' ? 'bg-bad/70' : 'bg-ink-3/50')}
                  style={{ width: `${Math.max(rate, 3)}%` }}
                />
                <span className="absolute inset-y-0 right-2 flex items-center font-mono text-[11px] text-ink-3">
                  {r.replied}/{r.sent} · {usd(r.cost)}/lead
                </span>
              </div>
              <span className={cx('text-right font-mono text-sm font-medium', tone === 'good' ? 'text-good' : tone === 'bad' ? 'text-bad' : 'text-ink-2')}>
                {rate}%
              </span>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

export function Insights() {
  const { proposal, acceptProposal, dismissProposal, profiles } = useStore()
  const steps = [
    ['Found', funnel.found],
    ['Approved', funnel.approved],
    ['Sent', funnel.sent],
    ['Replied', funnel.replied],
    ['Meeting', funnel.meeting],
  ] as const

  const stats = [
    ['Spent so far', usd(spend.total)],
    ['Per lead', usd(spend.total / spend.leads)],
    ['Per reply', usd(spend.total / funnel.replied)],
    ['Per meeting', usd(spend.total / funnel.meeting)],
  ]

  return (
    <>
      <PageHeader title={copy.insights.title} subtitle={copy.insights.subtitle} />

      {proposal && (
        <div className="mb-8 rounded-xl bg-ink p-7 text-paper">
          <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.08em] text-paper/60">
            <Lightbulb size={13} /> {copy.insights.proposal}
          </div>
          <h2 className="mt-3 font-display text-[28px] font-semibold leading-tight tracking-[-0.03em]">{proposal.title}</h2>
          <p className="mt-2 max-w-2xl text-sm text-paper/70">{proposal.detail}</p>
          <ul className="mt-4 space-y-1.5">
            {proposal.changes.map((c) => (
              <li key={c} className="flex items-center gap-2 text-sm">
                <ArrowRight size={13} className="text-accent" /> {c}
              </li>
            ))}
          </ul>
          <div className="mt-6 flex gap-2">
            <Button variant="accent" onClick={acceptProposal}>
              <Check size={14} /> {copy.insights.accept}
            </Button>
            <Button variant="ghost" className="!text-paper/70 hover:!bg-paper/10 hover:!text-paper" onClick={dismissProposal}>
              {copy.insights.dismiss}
            </Button>
          </div>
        </div>
      )}

      <div className="mb-8 grid grid-cols-4 gap-4">
        {stats.map(([k, v]) => (
          <div key={k}>
            <div className="text-xs text-ink-3">{k}</div>
            <div className="mt-1 font-display text-[32px] font-semibold leading-none tracking-[-0.03em]">{v}</div>
          </div>
        ))}
      </div>

      <Card className="mb-4 p-5">
        <Label className="mb-4">{copy.insights.funnel}</Label>
        <div className="grid grid-cols-5 gap-1">
          {steps.map(([label, n], i) => (
            <div key={label}>
              <div className="flex h-24 items-end">
                <div className={cx('w-full rounded-t', i === steps.length - 1 ? 'bg-accent' : 'bg-ink/80')} style={{ height: `${(n / funnel.found) * 100}%` }} />
              </div>
              <div className="mt-2 flex items-baseline justify-between pr-2">
                <span className="text-xs text-ink-2">{label}</span>
                <span className="font-mono text-sm font-medium">{n}</span>
              </div>
              {i > 0 && <div className="text-[11px] text-ink-3">{pct(n, steps[i - 1][1])}% of previous</div>}
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <RateTable title={copy.insights.byIndustry} rows={byIndustry} />
        <RateTable title={copy.insights.byAngle} rows={byAngle} labels={copy.insights.angleHelp} />
      </div>

      <section className="mt-10">
        <Label className="mb-3">{copy.insights.history}</Label>
        <ol className="space-y-2">
          {[...profiles].reverse().map((p) => (
            <li key={p.version} className="flex items-center gap-4 rounded-lg border border-line bg-surface px-4 py-3 text-sm">
              <span className="font-mono text-xs font-medium">v{p.version}</span>
              <span className="flex-1 text-ink-2">{p.change_note ?? 'First version, from your setup'}</span>
              {p.created_at && (
                <span className="text-xs text-ink-3">{new Date(p.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>
              )}
            </li>
          ))}
        </ol>
      </section>
    </>
  )
}
