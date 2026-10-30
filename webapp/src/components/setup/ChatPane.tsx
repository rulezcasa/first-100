import { ArrowUp } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { copy } from '../../copy'
import type { SetupMessage } from '../../types'
import { AgentAvatar, cx } from '../ui'

export function ChatPane({
  messages,
  thinking,
  error,
  onSend,
  disabled = false,
}: {
  messages: SetupMessage[]
  thinking: boolean
  error: string | null
  onSend: (text: string) => Promise<boolean>
  disabled?: boolean
}) {
  const [text, setText] = useState('')
  const scroller = useRef<HTMLDivElement>(null)

  // Scroll only the chat box; scrollIntoView would also scroll the page.
  useEffect(() => {
    const el = scroller.current
    el?.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages.length, thinking])

  const send = async () => {
    const t = text.trim()
    if (!t || thinking || disabled) return
    setText('')
    // Put the text back if the turn failed, so nothing typed is lost.
    if (!(await onSend(t))) setText(t)
  }

  return (
    <div className="flex h-full flex-col rounded-xl border border-line bg-surface">
      <div ref={scroller} className="scroll-thin flex-1 space-y-4 overflow-y-auto p-5">
        {messages.map((m, i) => (
          <div key={i} className={cx('flex gap-2.5', m.role === 'founder' && 'flex-row-reverse')}>
            {m.role === 'scout' && <AgentAvatar agent="Scout" size={26} />}
            <div
              className={cx(
                'max-w-[85%] whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed',
                m.role === 'founder' ? 'rounded-br-sm bg-ink text-paper' : 'rounded-bl-sm bg-sunken text-ink',
              )}
            >
              {m.text}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="flex items-center gap-2.5">
            <AgentAvatar agent="Scout" size={26} />
            <div className="flex gap-1 rounded-2xl rounded-bl-sm bg-sunken px-3.5 py-3.5">
              <span className="live-dot size-1.5 rounded-full bg-ink-3" />
              <span className="live-dot size-1.5 rounded-full bg-ink-3 [animation-delay:200ms]" />
              <span className="live-dot size-1.5 rounded-full bg-ink-3 [animation-delay:400ms]" />
            </div>
            <span className="text-xs text-ink-3">{copy.setup.thinking}</span>
          </div>
        )}
      </div>
      {error && <div className="mx-3 mb-2 rounded-md bg-bad-soft px-3 py-2 text-xs text-bad">{error}</div>}
      <div className="border-t border-line p-3">
        <div className="flex items-end gap-2 rounded-lg border border-line bg-paper p-2 focus-within:border-ink-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            rows={3}
            placeholder={disabled ? copy.setup.loading : copy.setup.chatPlaceholder}
            disabled={disabled}
            className="flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-ink-3"
          />
          <button onClick={send} disabled={!text.trim() || thinking || disabled} className="rounded-md bg-ink p-2 text-paper disabled:opacity-30">
            <ArrowUp size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
