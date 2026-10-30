import { ArrowUp, PanelRightClose, Wrench } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api } from '../../api'
import { copy } from '../../copy'
import type { AgentName, RoomEvent } from '../../types'
import { AgentAvatar, agentColor, cx } from '../ui'

const AGENTS: AgentName[] = ['Team', 'Scout', 'Researcher', 'Writer', 'Learner']
const WORKING_FOR_MS = 5 * 60_000 // an agent that took a turn and went quiet (band_no_reply) stops showing as working

const time = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '')
const asAgent = (e: RoomEvent): AgentName => (e.from_founder ? 'You' : AGENTS.find((a) => a === e.sender) ?? 'Team')
const mentions = (e: RoomEvent, agent: AgentName) => e.kind === 'text' && e.text.toLowerCase().includes(`@${agent.toLowerCase()}`)

/** Renders "@Scout" and "lead 3" as highlighted tokens. */
function Message({ text }: { text: string }) {
  const parts: ReactNode[] = []
  text.split(/(@\w+|\(lead \d+\)|lead \d+)/g).forEach((p, i) => {
    if (p.startsWith('@')) {
      const a = p.slice(1) as AgentName
      parts.push(
        <span key={i} className="font-medium" style={{ color: agentColor[a] ?? 'inherit' }}>
          {p}
        </span>,
      )
    } else if (/lead \d+/.test(p)) {
      parts.push(
        <span key={i} className="font-mono text-[11px] text-ink-3">
          {p}
        </span>,
      )
    } else parts.push(p)
  })
  return <>{parts}</>
}

/** The Band room: history on (re)connect, then new messages live over server-sent events. */
function useRoom() {
  const [events, setEvents] = useState<RoomEvent[]>([])
  const [status, setStatus] = useState<'connecting' | 'live' | 'offline'>('connecting')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const add = (incoming: RoomEvent[]) =>
      setEvents((prev) => {
        const seen = new Set(prev.map((e) => e.id))
        const merged = [...prev, ...incoming.filter((e) => !seen.has(e.id))]
        return merged.sort((a, b) => (a.created_at ?? '').localeCompare(b.created_at ?? ''))
      })
    const stream = new EventSource(api.activityStreamUrl)
    // On every (re)connect, load recent history too, so nothing said while offline is missed.
    stream.onopen = () => {
      setStatus('live')
      api.getActivity().then((h) => {
        setError(null)
        add(h)
      }, (e) => setError((e as Error).message))
    }
    stream.onerror = () => setStatus('offline') // EventSource reconnects on its own
    stream.onmessage = (m) => add([JSON.parse(m.data)])
    return () => stream.close()
  }, [])

  return { events, status, error, setError }
}

function Event({ e }: { e: RoomEvent }) {
  const agent = asAgent(e)
  if (e.kind === 'tool_call' || e.kind === 'tool_result') {
    if (e.kind === 'tool_result' && !e.is_error) return null
    return (
      <div className={cx('flex items-center gap-1.5 pl-[34px] text-[11px]', e.is_error ? 'text-bad' : 'text-ink-3')}>
        <Wrench size={11} />
        <span style={{ color: e.is_error ? undefined : agentColor[agent] }}>{e.sender}</span>
        <span className="font-mono">{e.kind === 'tool_result' ? copy.chrome.activityToolFailed(e.text) : e.text}</span>
      </div>
    )
  }
  return (
    <div className="flex gap-2.5">
      <AgentAvatar agent={agent} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold" style={{ color: agentColor[agent] }}>
            {e.from_founder ? 'You' : e.sender}
          </span>
          <span className="text-[11px] text-ink-3">{time(e.created_at)}</span>
        </div>
        <p className={cx('mt-0.5 whitespace-pre-wrap text-[13px] leading-snug', e.kind === 'error' ? 'text-bad' : 'text-ink-2')}>
          <Message text={e.text} />
        </p>
      </div>
    </div>
  )
}

export function ActivityPanel({ onClose }: { onClose: () => void }) {
  const { events, status, error, setError } = useRoom()
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  // The @mention being typed at the cursor ("" right after "@"), or null when there isn't one.
  const [query, setQuery] = useState<string | null>(null)
  const [active, setActive] = useState(0)
  const options = query === null ? [] : AGENTS.filter((a) => a.toLowerCase().startsWith(query.toLowerCase()))

  const trackMention = (el: HTMLTextAreaElement) => {
    const m = el.value.slice(0, el.selectionStart).match(/(?:^|\s)@(\w*)$/)
    setQuery(m ? m[1] : null)
    setActive(0)
  }

  const pick = (agent: AgentName) => {
    const el = input.current
    if (!el || query === null) return
    const caret = el.selectionStart
    const start = caret - query.length - 1 // the "@"
    const next = `${draft.slice(0, start)}@${agent} ${draft.slice(caret)}`
    const after = start + agent.length + 2
    setDraft(next)
    setQuery(null)
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(after, after)
    })
  }

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  // An agent is working when it was mentioned, or started using tools, after it last said anything.
  const now = Date.now()
  const working = AGENTS.filter((a) => {
    let lastSaid = -1
    let lastAsked = -1
    events.forEach((e, i) => {
      if (e.sender === a && !e.from_founder && (e.kind === 'text' || e.kind === 'error')) lastSaid = i
      else if ((e.sender === a && e.kind === 'tool_call') || (e.sender !== a && mentions(e, a))) lastAsked = i
    })
    const asked = events[lastAsked]
    return lastAsked > lastSaid && asked?.created_at && now - new Date(asked.created_at).getTime() < WORKING_FOR_MS
  })

  const send = async () => {
    const text = draft.trim()
    if (!text || sending) return
    setSending(true)
    setError(null)
    setDraft('')
    try {
      await api.sendToTeam(text) // the message comes back over the stream, like everyone else's
    } catch (e) {
      setError((e as Error).message)
      setDraft(text) // nothing typed is lost
    } finally {
      setSending(false)
    }
  }

  const statusStyle = { live: 'text-good', offline: 'text-ink-3', connecting: 'text-ink-3' }[status]
  const statusText = { live: copy.chrome.activityLive, offline: copy.chrome.activityOffline, connecting: copy.chrome.activityConnecting }[status]

  return (
    <aside className="flex w-[340px] shrink-0 flex-col border-l border-line bg-surface">
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-line px-4">
        <div className="text-sm font-medium">{copy.chrome.activity}</div>
        <div className="flex items-center gap-3">
          <div className={cx('flex items-center gap-1.5 text-xs', statusStyle)}>
            <span className={cx('size-1.5 rounded-full bg-current', status === 'live' && 'live-dot')} />
            {statusText}
          </div>
          <button onClick={onClose} title={copy.chrome.activityHide} className="rounded-md p-1 text-ink-3 hover:bg-sunken hover:text-ink">
            <PanelRightClose size={16} />
          </button>
        </div>
      </div>

      <div className="scroll-thin flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {events.length === 0 && status === 'live' && !error && <p className="text-xs text-ink-3">{copy.chrome.activityEmpty}</p>}
        {events.map((e) => (
          <Event key={e.id} e={e} />
        ))}
        {working.map((a) => (
          <div key={a} className="flex items-center gap-2 pl-[34px] text-xs text-ink-3">
            <span className="flex gap-0.5">
              <span className="live-dot size-1 rounded-full bg-ink-3" />
              <span className="live-dot size-1 rounded-full bg-ink-3 [animation-delay:200ms]" />
              <span className="live-dot size-1 rounded-full bg-ink-3 [animation-delay:400ms]" />
            </span>
            {copy.chrome.activityWorking(a)}
          </div>
        ))}
        <div ref={end} />
      </div>

      {error && <div className="mx-3 mb-2 rounded-md bg-bad-soft px-3 py-2 text-xs text-bad">{error}</div>}
      <div className="relative border-t border-line p-3">
        {options.length > 0 && (
          <ul className="absolute inset-x-3 bottom-full mb-1 overflow-hidden rounded-lg border border-line bg-surface py-1 shadow-lg">
            {options.map((a, i) => (
              <li key={a}>
                <button
                  onMouseDown={(e) => e.preventDefault()} // keep focus in the textarea
                  onClick={() => pick(a)}
                  onMouseEnter={() => setActive(i)}
                  className={cx('flex w-full items-center gap-2.5 px-2.5 py-1.5 text-left', i === active && 'bg-sunken')}
                >
                  <AgentAvatar agent={a} size={22} />
                  <span className="text-[13px] font-medium" style={{ color: agentColor[a] }}>
                    {a}
                  </span>
                  <span className="truncate text-[11px] text-ink-3">{copy.chrome.agentRoles[a]}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex items-end gap-2 rounded-lg border border-line bg-paper p-2 focus-within:border-ink-3">
          <textarea
            ref={input}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              trackMention(e.target)
            }}
            onSelect={(e) => trackMention(e.currentTarget)}
            onBlur={() => setQuery(null)}
            onKeyDown={(e) => {
              if (options.length > 0) {
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                  e.preventDefault()
                  setActive((i) => (i + (e.key === 'ArrowDown' ? 1 : options.length - 1)) % options.length)
                  return
                }
                if (e.key === 'Enter' || e.key === 'Tab') {
                  e.preventDefault()
                  pick(options[active])
                  return
                }
                if (e.key === 'Escape') {
                  e.preventDefault()
                  setQuery(null)
                  return
                }
              }
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            rows={2}
            placeholder={copy.chrome.activityPlaceholder}
            className="flex-1 resize-none bg-transparent text-[13px] outline-none placeholder:text-ink-3"
          />
          <button onClick={send} disabled={!draft.trim() || sending} className="rounded-md bg-ink p-1.5 text-paper disabled:opacity-30">
            <ArrowUp size={14} />
          </button>
        </div>
      </div>
    </aside>
  )
}
