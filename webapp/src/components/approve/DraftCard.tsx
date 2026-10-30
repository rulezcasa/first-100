import { Check, Pencil, X } from 'lucide-react'
import { useState } from 'react'
import { copy } from '../../copy'
import { useStore } from '../../store'
import type { Draft } from '../../types'
import { Button, cx } from '../ui'

const words = (s: string) => s.trim().split(/\s+/).filter(Boolean).length

export function DraftCard({ draft }: { draft: Draft }) {
  const { setDraftStatus, editDraft } = useStore()
  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState(draft.subject)
  const [body, setBody] = useState(draft.body)
  const n = words(editing ? body : draft.body)

  const save = () => {
    editDraft(draft.id, { subject, body })
    setEditing(false)
  }

  return (
    <div className={cx('flex flex-col rounded-xl border bg-surface', draft.status === 'approved' ? 'border-good' : 'border-line')}>
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold">Version {draft.variant}</span>
          <span
            title={copy.angleHelp[draft.angle]}
            className={cx('rounded px-1.5 py-0.5 text-[10px] font-medium', draft.angle === 'signal' ? 'bg-info-soft text-info' : 'bg-warn-soft text-warn')}
          >
            {draft.angle === 'signal' ? 'Opens with news' : 'Opens with a problem'}
          </span>
        </div>
        <span className={cx('font-mono text-[11px]', n > 90 ? 'text-bad' : 'text-ink-3')} title="Under 90 words reads like a person, not a campaign">
          {n}/90 words
        </span>
      </div>

      <div className="flex-1 px-4 py-3.5">
        {editing ? (
          <>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} className="mb-2 w-full rounded-md border border-line px-2 py-1 text-sm font-medium outline-none focus:border-ink-3" />
            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={10} className="w-full resize-none rounded-md border border-line px-2 py-1.5 text-[13.5px] leading-relaxed outline-none focus:border-ink-3" />
          </>
        ) : (
          <>
            <div className="mb-2 text-sm font-medium">{draft.subject}</div>
            <p className="whitespace-pre-line text-[13.5px] leading-relaxed text-ink-2">{draft.body}</p>
          </>
        )}
      </div>

      <div className="flex items-center gap-1.5 border-t border-line px-3 py-2.5">
        {draft.status === 'approved' ? (
          <span className="flex items-center gap-1.5 px-1 text-sm font-medium text-good">
            <Check size={15} /> Approved
          </span>
        ) : editing ? (
          <>
            <Button size="sm" variant="primary" onClick={save}>
              {copy.approve.save}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </>
        ) : (
          <>
            <Button size="sm" variant="good" onClick={() => setDraftStatus(draft.id, 'approved')}>
              <Check size={13} /> {copy.approve.approve}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
              <Pencil size={13} /> {copy.approve.edit}
            </Button>
            <Button size="sm" variant="danger" className="ml-auto" onClick={() => setDraftStatus(draft.id, 'rejected')}>
              <X size={13} /> {copy.approve.reject}
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
