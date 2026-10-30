import { ArrowRight, Plus, RotateCcw } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { AgentAvatar, Button, Card, Chip, Confidence, Label, PageHeader } from '../components/ui'
import { copy } from '../copy'
import { useStore } from '../store'
import type { Profile } from '../types'

export function Who() {
  const { setProfile } = useStore()
  const nav = useNavigate()
  const [profile, setLocal] = useState<Profile | null>(null)
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false) // StrictMode runs effects twice; generate only once
  const last = useRef<() => Promise<Profile>>(api.getProfile) // what Try again repeats

  const show = (p: Profile) => {
    setLocal(p)
    setProfile(p)
  }

  const run = async (fn: () => Promise<Profile>) => {
    last.current = fn
    setError(null)
    setThinking(true)
    try {
      show(await fn())
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setThinking(false)
    }
  }

  // Load the saved profile; if setup is saved but Scout hasn't worked out the groups yet, do it now.
  useEffect(() => {
    if (started.current) return
    started.current = true
    run(async () => {
      const p = await api.getProfile()
      if (!p.product || p.segments.length) return p
      setLocal(p)
      return api.generateWho()
    })
  }, [])


  const ready = profile && profile.segments.length > 0
  const header = (
    <PageHeader
      title={copy.who.title}
      subtitle={copy.who.subtitle}
      actions={
        <>
          <Button variant="ghost" onClick={() => run(() => api.generateWho(true))} disabled={!profile?.product || thinking}>
            <RotateCcw size={14} /> {copy.who.redo}
          </Button>
        </>
      }
    />
  )

  if (profile && !profile.product) {
    return (
      <>
        {header}
        <Card className="flex items-center justify-between gap-6 p-7">
          <div>
            <h2 className="text-[17px] font-semibold">{copy.who.notSetUp}</h2>
            <p className="mt-1 text-sm text-ink-2">{copy.who.notSetUpHint}</p>
          </div>
          <Button variant="primary" onClick={() => nav('/setup')}>
            {copy.who.goToSetup} <ArrowRight size={15} />
          </Button>
        </Card>
      </>
    )
  }

  const status = (thinking || error) && (
    <div className="mb-6">
      {thinking && (
        <div className="flex items-center gap-2.5">
          <AgentAvatar agent="Scout" size={26} />
          <div className="flex gap-1 rounded-2xl rounded-bl-sm bg-sunken px-3.5 py-3.5">
            <span className="live-dot size-1.5 rounded-full bg-ink-3" />
            <span className="live-dot size-1.5 rounded-full bg-ink-3 [animation-delay:200ms]" />
            <span className="live-dot size-1.5 rounded-full bg-ink-3 [animation-delay:400ms]" />
          </div>
          <span className="text-xs text-ink-3">{copy.who.thinking}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center justify-between gap-4 rounded-md bg-bad-soft px-4 py-2.5 text-sm text-bad">
          {error}
          <Button size="sm" variant="danger" onClick={() => run(last.current)}>
            <RotateCcw size={12} /> {copy.who.retry}
          </Button>
        </div>
      )}
    </div>
  )

  if (!ready) {
    return (
      <>
        {header}
        {status}
      </>
    )
  }

  const [top, ...rest] = [...profile.segments].sort((a, b) => b.confidence - a.confidence)

  return (
    <>
      {header}
      {status}

      {profile.change_note && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-accent bg-accent-soft/60 px-4 py-2.5 text-sm">
          <span className="font-mono text-xs font-medium text-accent-ink">v{profile.version}</span>
          <span className="text-ink-2">{profile.change_note}</span>
        </div>
      )}

      <div className={thinking ? 'pointer-events-none opacity-50 transition-opacity' : 'transition-opacity'}>
        <div className="grid grid-cols-2 gap-4">
          <Card className="col-span-2 grid grid-cols-[1fr_auto] gap-8 p-7">
            <div>
              <Label>{copy.who.bestBet}</Label>
              <h2 className="mt-2 font-display text-[30px] font-semibold leading-tight tracking-[-0.03em]">{top.name}</h2>
              <p className="mt-2 max-w-xl text-ink-2">{top.why}</p>
            </div>
            <div className="flex flex-col items-end justify-between">
              <Confidence value={top.confidence} />
              <div className="text-right text-xs text-ink-3">{profile.buyer_roles.slice(0, 2).join(', ')}</div>
            </div>
          </Card>
          {rest.map((s) => (
            <Card key={s.name} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <h3 className="text-[15px] font-semibold">{s.name}</h3>
                <Confidence value={s.confidence} />
              </div>
              <p className="mt-2 text-[13.5px] text-ink-2">{s.why}</p>
            </Card>
          ))}
        </div>

        <div className="mt-10 grid grid-cols-[1fr_1fr] gap-10">
          <section>
            <Label>{copy.who.tryAlso}</Label>
            <p className="mb-3 mt-1 text-xs text-ink-3">{copy.who.tryAlsoHint}</p>
            <div className="flex flex-wrap gap-2">
              {profile.expansion.map((e) => (
                <Chip key={e} onClick={() => run(() => api.addExpansion(e))}>
                  <Plus size={12} /> {e}
                </Chip>
              ))}
            </div>
          </section>
          <section>
            <Label className="mb-3">{copy.who.competitors}</Label>
            {profile.competitors.length ? (
              <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
                {profile.competitors.map((c) => (
                  <li key={c.name} className="flex items-baseline justify-between gap-4 px-4 py-3">
                    <span className="text-sm font-medium">{c.name}</span>
                    <span className="text-right text-xs text-ink-3">{c.note}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-xl border border-dashed border-line px-4 py-3 text-xs text-ink-3">{copy.who.competitorsLater}</p>
            )}
          </section>
        </div>
      </div>
    </>
  )
}
