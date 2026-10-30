import { X } from 'lucide-react'
import { useEffect, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { copy } from '../../copy'
import type { AgentName, EmailStatus, Tier } from '../../types'

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ')

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'good' | 'accent'
const variants: Record<Variant, string> = {
  primary: 'bg-ink text-paper hover:bg-ink/85',
  secondary: 'bg-surface text-ink border border-line-strong hover:bg-sunken',
  ghost: 'text-ink-2 hover:bg-sunken hover:text-ink',
  danger: 'text-bad hover:bg-bad-soft',
  good: 'bg-good text-white hover:bg-good/90',
  accent: 'bg-accent text-on-accent hover:bg-accent/85',
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm' | 'md' }) {
  return (
    <button
      className={cx(
        'inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors disabled:opacity-40 disabled:pointer-events-none cursor-pointer whitespace-nowrap',
        size === 'sm' ? 'h-7 px-2.5 text-xs' : 'h-9 px-3.5 text-sm',
        variants[variant],
        className,
      )}
      {...props}
    />
  )
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cx('rounded-xl border border-line bg-surface', className)}>{children}</div>
}

export function Label({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx('text-[11px] font-medium uppercase tracking-[0.08em] text-ink-3', className)}>{children}</div>
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex items-end justify-between gap-6">
      <div>
        <h1 className="font-display text-[38px] font-semibold leading-none tracking-[-0.03em]">{title}</h1>
        {subtitle && <p className="mt-3 max-w-xl text-ink-2">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

const tierStyle: Record<Tier, string> = {
  A: 'bg-good-soft text-good',
  B: 'bg-warn-soft text-warn',
  C: 'bg-sunken text-ink-3',
}

export function TierBadge({ tier, score }: { tier: Tier | null; score?: number | null }) {
  if (!tier) {
    return (
      <span title={copy.leads.notChecked} className="inline-flex items-center rounded-md bg-info-soft px-1.5 py-0.5 text-xs font-medium text-info">
        New
      </span>
    )
  }
  return (
    <span title={copy.tier[tier]} className={cx('inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs font-semibold', tierStyle[tier])}>
      {tier}
      {score != null && <span className="font-mono font-normal opacity-80">{score}</span>}
    </span>
  )
}

const emailStyle: Record<EmailStatus, string> = {
  valid: 'text-good',
  risky: 'text-warn',
  unknown: 'text-ink-3',
}

export function EmailStatusBadge({ status }: { status: EmailStatus }) {
  return (
    <span title={copy.emailStatus[status]} className={cx('inline-flex items-center gap-1 text-xs', emailStyle[status])}>
      <span className="size-1.5 rounded-full bg-current" />
      {status}
    </span>
  )
}

export function Chip({ children, className, onClick }: { children: ReactNode; className?: string; onClick?: () => void }) {
  const C = onClick ? 'button' : 'span'
  return (
    <C
      onClick={onClick}
      className={cx(
        'inline-flex items-center gap-1 rounded-full border border-line bg-surface px-2.5 py-1 text-xs text-ink-2',
        onClick && 'cursor-pointer hover:border-ink-3 hover:text-ink',
        className,
      )}
    >
      {children}
    </C>
  )
}

export function confidenceLabel(c: number) {
  return c >= 0.7 ? 'High' : c >= 0.5 ? 'Medium' : 'Low'
}

export function Confidence({ value }: { value: number }) {
  const label = confidenceLabel(value)
  const color = label === 'High' ? 'bg-good' : label === 'Medium' ? 'bg-warn' : 'bg-ink-3'
  return (
    <div className="flex items-center gap-2" title={`${Math.round(value * 100)}% confident`}>
      <div className="flex gap-0.5">
        {[0, 1, 2].map((i) => (
          <span key={i} className={cx('h-3 w-1.5 rounded-sm', i < (label === 'High' ? 3 : label === 'Medium' ? 2 : 1) ? color : 'bg-line')} />
        ))}
      </div>
      <span className="text-xs text-ink-2">{label}</span>
    </div>
  )
}

export const agentColor: Record<AgentName, string> = {
  Team: 'var(--color-agent-team)',
  Scout: 'var(--color-agent-scout)',
  Researcher: 'var(--color-agent-researcher)',
  Writer: 'var(--color-agent-writer)',
  Learner: 'var(--color-agent-learner)',
  You: 'var(--color-ink)',
}

export function AgentAvatar({ agent, size = 24 }: { agent: AgentName; size?: number }) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
      style={{ width: size, height: size, background: agentColor[agent], fontSize: size * 0.42 }}
    >
      {agent === 'You' ? 'Y' : agent[0]}
    </span>
  )
}

// Only leads the founder added or moved get a tag; agent-found is the default and needs no label.
export function SourceTag({ source }: { source: 'ai' | 'founder' }) {
  if (source === 'ai') return null
  return (
    <span title="Added or moved by you" className="rounded bg-accent-soft px-1 py-px font-mono text-[10px] font-medium uppercase text-accent-ink">
      You
    </span>
  )
}

export function Drawer({ open, onClose, children }: { open: boolean; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])
  return (
    <div className={cx('fixed inset-0 z-40', !open && 'pointer-events-none')}>
      <div onClick={onClose} className={cx('absolute inset-0 bg-ink/20 transition-opacity', open ? 'opacity-100' : 'opacity-0')} />
      <div
        className={cx(
          'scroll-thin absolute inset-y-0 right-0 w-[640px] max-w-full overflow-y-auto bg-paper shadow-2xl transition-transform duration-300',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        <button onClick={onClose} className="absolute right-4 top-4 z-10 rounded-md p-1.5 text-ink-3 hover:bg-sunken hover:text-ink">
          <X size={18} />
        </button>
        {children}
      </div>
    </div>
  )
}

export function usd(n: number) {
  return `$${n.toFixed(2)}`
}

export function pct(n: number, d: number) {
  return d ? Math.round((n / d) * 100) : 0
}
