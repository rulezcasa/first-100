import { Activity, CloudOff, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { Button, Card, cx, Label, PageHeader, pct, usd } from '../components/ui'
import { copy } from '../copy'
import type { Dashboard as Data, ReplyRate } from '../types'

// Token costs are often fractions of a cent; usd() would round them all to $0.00.
const costUsd = (n: number | null) => (n == null ? '–' : n > 0 && n < 0.01 ? `$${n.toFixed(4)}` : usd(n))
const money = (n: number) => `$${Math.round(n).toLocaleString()}`
const compact = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}K` : String(n))

// Every chart uses one palette: ink bars, with accent marking the one bar to look at.
const bar = 'bg-ink/70'
const barHighlight = 'bg-accent'

function MeterStatus({ data }: { data: Data }) {
  const { sync, source } = data
  if (source === 'flexprice')
    return (
      <span className="flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-xs text-ink-2" title={copy.dashboard.meter.liveHelp}>
        <span className="live-dot size-1.5 rounded-full bg-good" />
        {copy.dashboard.meter.live}
        {sync.pending_events > 0 && <span className="text-ink-3">· {copy.dashboard.meter.pending(sync.pending_events)}</span>}
      </span>
    )
  return (
    <span className="flex items-center gap-2 rounded-full border border-line bg-sunken px-3 py-1.5 text-xs text-ink-3" title={sync.error ?? copy.dashboard.meter.localHelp}>
      <CloudOff size={13} />
      {sync.connected ? copy.dashboard.meter.unreachable : copy.dashboard.meter.local}
    </span>
  )
}

function Kpi({ label, value, note, tone }: { label: string; value: string; note?: string; tone?: 'good' | 'bad' }) {
  return (
    <Card className="p-5">
      <Label>{label}</Label>
      <div className={cx('mt-3 font-display text-[34px] font-semibold leading-none tracking-[-0.03em]', tone === 'good' && 'text-good', tone === 'bad' && 'text-bad')}>
        {value}
      </div>
      {note && <div className="mt-2 text-xs text-ink-3">{note}</div>}
    </Card>
  )
}

// A round step (1, 2 or 5 × 10^n) so the axis reads $0.01, $0.02… rather than $0.0137.
function niceMax(max: number) {
  if (max <= 0) return 0.01
  const step = 10 ** Math.floor(Math.log10(max / 4))
  const unit = [1, 2, 5, 10].find((m) => (m * step * 4) >= max)! * step
  return unit * 4
}

function SpendTrend({ daily }: { daily: Data['cost']['daily'] }) {
  // The last 14 days ending today, with empty days filled in so gaps show as gaps.
  const byDay = new Map(daily.map((d) => [d.day, d.cost_usd]))
  const days = Array.from({ length: 14 }, (_, i) => {
    const d = new Date()
    d.setUTCDate(d.getUTCDate() - (13 - i))
    const key = d.toISOString().slice(0, 10)
    return { key, label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' }), cost: byDay.get(key) ?? 0 }
  })
  const top = niceMax(Math.max(...days.map((d) => d.cost)))
  const ticks = [4, 3, 2, 1, 0].map((i) => (top / 4) * i)
  const total = days.reduce((n, d) => n + d.cost, 0)
  const [hover, setHover] = useState<number | null>(null)
  const shown = hover == null ? null : days[hover]

  return (
    <div>
      <div className="mb-4 flex items-baseline gap-6 text-xs text-ink-3">
        <span>
          <span className="font-mono text-base font-medium text-ink">{costUsd(total)}</span> in 14 days
        </span>
        <span>
          <span className="font-mono text-base font-medium text-ink">{costUsd(total / 14)}</span> a day on average
        </span>
        <span className="ml-auto h-5 font-mono text-ink-2">{shown && `${shown.label}: ${costUsd(shown.cost)}`}</span>
      </div>
      <div className="grid grid-cols-[52px_1fr] gap-2">
        <div className="relative h-40">
          {ticks.map((t, i) => (
            <span key={i} className="absolute right-0 -translate-y-1/2 font-mono text-[10px] text-ink-3" style={{ top: `${(i / 4) * 100}%` }}>
              {costUsd(t)}
            </span>
          ))}
        </div>
        <div className="relative h-40">
          {ticks.map((_, i) => (
            <div key={i} className={cx('absolute inset-x-0 border-t', i === 4 ? 'border-line-strong' : 'border-dashed border-line')} style={{ top: `${(i / 4) * 100}%` }} />
          ))}
          <div className="absolute inset-0 flex items-end gap-1.5" onMouseLeave={() => setHover(null)}>
            {days.map((d, i) => (
              <div key={d.key} className="flex h-full flex-1 items-end" onMouseEnter={() => setHover(i)}>
                <div
                  className={cx(
                    'w-full rounded-t-sm transition-colors',
                    i === days.length - 1 ? barHighlight : hover === i ? 'bg-ink' : bar,
                  )}
                  style={{ height: `${(d.cost / top) * 100}%`, minHeight: d.cost ? 2 : 0 }}
                />
              </div>
            ))}
          </div>
        </div>
        <div />
        <div className="flex gap-1.5">
          {days.map((d, i) => (
            <span key={d.key} className="flex-1 whitespace-nowrap text-center font-mono text-[10px] text-ink-3">
              {i === days.length - 1 ? 'Today' : i % 3 === 0 ? d.label : ''}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function ReplyRates({ title, rows, help }: { title: string; rows: ReplyRate[]; help?: Record<string, string> }) {
  const rates = rows.map((r) => pct(r.replied, r.sent))
  const best = Math.max(...rates)
  return (
    <Card className="p-5">
      <Label className="mb-4">{title}</Label>
      {rows.length === 0 ? (
        <p className="text-sm text-ink-3">{copy.dashboard.noReplies}</p>
      ) : (
        <div className="space-y-2.5">
          {rows.map((r, i) => {
            const rate = rates[i]
            const top = rows.length > 1 && rate === best
            return (
              <div key={r.key} className="grid grid-cols-[110px_1fr_88px] items-center gap-3">
                <span className="text-sm capitalize" title={help?.[r.key]}>
                  {r.key}
                </span>
                <div className="h-5 overflow-hidden rounded bg-sunken">
                  <div className={cx('h-full rounded', top ? barHighlight : bar)} style={{ width: `${Math.max(rate, 2)}%` }} />
                </div>
                <span className="text-right font-mono text-xs" title={`${r.replied} of ${r.sent} replied`}>
                  <span className={cx('text-sm', top ? 'font-semibold text-ink' : 'font-medium text-ink-2')}>{rate}%</span>
                  <span className="text-ink-3"> · {r.replied}/{r.sent}</span>
                </span>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}

export function Dashboard() {
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    return api
      .getDashboard()
      .then((d) => {
        setData(d)
        setError(null)
      }, (e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  if (error) return <p className="text-bad">{error}</p>
  if (!data) return <p className="text-ink-3">Loading…</p>

  const { cost, clients, revenue } = data
  const steps = [
    ['Leads', clients.leads],
    ['Contacted', clients.contacted],
    ['Replied', clients.replied],
    ['Meetings', clients.meetings],
    ['Potential', clients.potential],
    ['Confirmed', clients.confirmed],
  ] as const
  const maxAgent = Math.max(...cost.by_agent.map((a) => a.cost_usd), 0)
  const unit = [
    ['Per lead', cost.per_lead_usd],
    ['Per reply', cost.per_reply_usd],
    ['Per client', cost.per_client_usd],
  ] as const


  return (
    <>
      <PageHeader
        title={copy.dashboard.title}
        subtitle={copy.dashboard.subtitle}
        actions={
          <>
            <MeterStatus data={data} />
            <Button size="sm" variant="ghost" title="Refresh" onClick={load} disabled={loading}>
              <RefreshCw size={14} className={cx(loading && 'animate-spin')} />
            </Button>
          </>
        }
      />

      <div className="mb-4 grid grid-cols-4 gap-4">
        <Kpi label={copy.dashboard.cost} value={costUsd(cost.total_usd)} note={`${compact(cost.tokens)} tokens · ${cost.calls} AI calls`} />
        <Kpi label={copy.dashboard.clients} value={String(clients.confirmed)} note={`${clients.potential} potential · ${pct(clients.confirmed, clients.contacted)}% of contacted`} />
        <Kpi label={copy.dashboard.revenue} value={money(revenue.confirmed_usd)} note={`${money(revenue.pipeline_usd)} still in talks`} />
        <Kpi
          label={copy.dashboard.return}
          value={revenue.roi == null ? '–' : `${compact(Math.round(revenue.roi))}×`}
          note={`${money(revenue.net_usd)} after AI cost`}
          tone={revenue.net_usd >= 0 ? 'good' : 'bad'}
        />
      </div>

      <div className="mb-4 grid grid-cols-[2fr_1fr] gap-4">
        <Card className="p-5">
          <div className="mb-4 flex items-baseline justify-between">
            <Label>{copy.dashboard.trend}</Label>
            <span className="flex items-center gap-1.5 text-[11px] text-ink-3">
              <Activity size={12} /> {data.source === 'flexprice' ? copy.dashboard.meter.from : copy.dashboard.meter.fromLocal}
            </span>
          </div>
          {cost.daily.length ? <SpendTrend daily={cost.daily} /> : <p className="py-12 text-center text-sm text-ink-3">No AI calls recorded yet.</p>}
        </Card>
        <Card className="p-5">
          <Label className="mb-4">{copy.dashboard.unit}</Label>
          <div className="space-y-3">
            {unit.map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between border-b border-line pb-3 last:border-0 last:pb-0">
                <span className="text-sm text-ink-2">{k}</span>
                <span className="font-mono text-lg font-medium">{costUsd(v)}</span>
              </div>
            ))}
            <div className="flex items-baseline justify-between pt-1">
              <span className="text-sm text-ink-2">Avg deal</span>
              <span className="font-mono text-lg font-medium text-good">{revenue.avg_deal_usd == null ? '–' : money(revenue.avg_deal_usd)}</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="mb-4 grid grid-cols-[2fr_1fr] gap-4">
        <Card className="p-5">
          <Label className="mb-4">{copy.dashboard.funnel}</Label>
          <div className="space-y-2">
            {steps.map(([label, n], i) => (
              <div key={label} className="grid grid-cols-[84px_1fr_88px] items-center gap-3">
                <span className="text-xs text-ink-2">{label}</span>
                <div className="h-5 overflow-hidden rounded bg-sunken">
                  <div
                    className={cx('h-full rounded', i === steps.length - 1 ? barHighlight : bar)}
                    style={{ width: `${clients.leads ? Math.max((n / clients.leads) * 100, n ? 2 : 0) : 0}%` }}
                  />
                </div>
                <span className="text-right font-mono text-xs">
                  <span className="text-sm font-medium">{n}</span>
                  {i > 0 && <span className="text-ink-3"> · {pct(n, steps[i - 1][1])}%</span>}
                </span>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-5">
          <Label className="mb-4">{copy.dashboard.byAgent}</Label>
          {cost.by_agent.length === 0 ? (
            <p className="text-sm text-ink-3">No AI calls recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {cost.by_agent.map((a) => (
                <div key={a.agent}>
                  <div className="mb-1 flex items-baseline justify-between text-sm">
                    <span className="capitalize">{a.agent}</span>
                    <span className="font-mono text-xs">{costUsd(a.cost_usd)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded bg-sunken">
                    <div className={cx('h-full rounded', a.cost_usd === maxAgent ? barHighlight : bar)} style={{ width: `${maxAgent ? (a.cost_usd / maxAgent) * 100 : 0}%` }} />
                  </div>
                  <div className="mt-0.5 text-[11px] text-ink-3">
                    {a.calls} calls · {compact(a.tokens)} tokens
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <ReplyRates title={copy.dashboard.byIndustry} rows={data.reply_rates.by_industry} />
        <ReplyRates title={copy.dashboard.byAngle} rows={data.reply_rates.by_angle} help={copy.angleHelp} />
      </div>
    </>
  )
}
