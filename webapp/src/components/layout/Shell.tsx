import { CircleDollarSign, CheckSquare, Columns3, PanelRightOpen, Sparkles, Target, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { copy } from '../../copy'
import { spend } from '../../mock'
import { useStore } from '../../store'
import { cx, usd } from '../ui'
import { ActivityPanel } from './ActivityPanel'

const nav = [
  { to: '/setup', label: copy.nav.setup, icon: Sparkles },
  { to: '/who', label: copy.nav.who, icon: Target },
  { to: '/leads', label: copy.nav.leads, icon: Users },
  { to: '/approve', label: copy.nav.approve, icon: CheckSquare },
  { to: '/pipeline', label: copy.nav.pipeline, icon: Columns3 },
  { to: '/dashboard', label: copy.nav.dashboard, icon: CircleDollarSign },
]

export function Shell() {
  const [activityOpen, setActivityOpen] = useState(true)
  const { drafts, profile } = useStore()
  const pending = new Set(drafts.filter((d) => d.status === 'pending' && d.channel === 'email').map((d) => d.lead_id)).size

  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col border-r border-line px-3 py-5">
        <Link to="/setup" className="mb-8 flex items-center gap-1.5 px-2">
          <span className="font-display text-[22px] font-bold leading-none tracking-[-0.04em]">First</span>
          <span className="rounded-md bg-accent px-1.5 py-0.5 font-mono text-xs font-semibold text-on-accent">100</span>
        </Link>
        <nav className="flex flex-col gap-0.5">
          {nav.map(({ to, label, icon: Icon }, i) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cx(
                  'group flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors',
                  isActive ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--color-line)]' : 'text-ink-2 hover:bg-sunken hover:text-ink',
                )
              }
            >
              <span className="w-4 font-mono text-[10px] text-ink-3">{i + 1}</span>
              <Icon size={16} strokeWidth={1.75} />
              <span className="flex-1">{label}</span>
              {to === '/approve' && pending > 0 && (
                <span className="rounded-full bg-accent px-1.5 text-[11px] font-semibold text-on-accent">{pending}</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-3 px-2 text-xs text-ink-3">
          <div className="flex items-center justify-between">
            <span>{copy.chrome.profileVersion(profile.version)}</span>
            {profile.change_note && <span className="size-1.5 rounded-full bg-accent" title={profile.change_note} />}
          </div>
          <div title="Every search, lookup and draft is metered">{copy.chrome.spent(usd(spend.total), spend.leads)}</div>
        </div>
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col">
        {!activityOpen && (
          <button
            onClick={() => setActivityOpen(true)}
            title={copy.chrome.activityShow}
            className="absolute right-4 top-4 z-10 flex items-center gap-2 rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs text-ink-2 hover:bg-sunken"
          >
            <span className="live-dot size-1.5 rounded-full bg-good" />
            {copy.chrome.activity}
            <PanelRightOpen size={15} />
          </button>
        )}
        <main className="scroll-thin flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-10 py-10">
            <Outlet />
          </div>
        </main>
      </div>

      {activityOpen && <ActivityPanel onClose={() => setActivityOpen(false)} />}
    </div>
  )
}
