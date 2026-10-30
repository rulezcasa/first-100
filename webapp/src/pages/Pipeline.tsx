import { Dices, Link2 } from 'lucide-react'
import { useState } from 'react'
import { Button, cx, PageHeader, SourceTag, TierBadge } from '../components/ui'
import { copy } from '../copy'
import { useStore } from '../store'
import type { Stage } from '../types'

const stages: Stage[] = ['found', 'approved', 'sent', 'replied', 'meeting']

export function Pipeline() {
  const { leads, simulateReplies, moveLead } = useStore()
  const [dragging, setDragging] = useState<number | null>(null)
  const [over, setOver] = useState<Stage | null>(null)

  return (
    <>
      <PageHeader
        title={copy.pipeline.title}
        subtitle={copy.pipeline.subtitle}
        actions={
          <Button onClick={simulateReplies} title="Demo only: rolls a reply outcome for every sent lead">
            <Dices size={14} /> {copy.pipeline.simulate}
          </Button>
        }
      />
      <div className="grid grid-cols-5 gap-3">
        {stages.map((s) => {
          const col = leads.filter((l) => l.stage === s && l.tier !== 'C')
          return (
            <div
              key={s}
              onDragOver={(e) => {
                e.preventDefault()
                setOver(s)
              }}
              onDragLeave={() => setOver(null)}
              onDrop={() => {
                if (dragging !== null) moveLead(dragging, s)
                setDragging(null)
                setOver(null)
              }}
              className={cx('min-h-[420px] rounded-xl bg-sunken/70 p-2 transition-colors', over === s && 'bg-accent-soft/60')}
            >
              <div className="flex items-center justify-between px-2 pb-3 pt-1">
                <span className="text-xs font-semibold">{copy.pipeline.stages[s]}</span>
                <span className="font-mono text-[11px] text-ink-3">{col.length}</span>
              </div>
              <div className="space-y-2">
                {col.map((l) => (
                  <div
                    key={l.id}
                    draggable
                    onDragStart={() => setDragging(l.id)}
                    className="cursor-grab rounded-lg border border-line bg-surface p-3 shadow-[0_1px_0_var(--color-line)] active:cursor-grabbing"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-[13px] font-medium leading-tight">{l.company}</span>
                      <SourceTag source={l.source} />
                    </div>
                    <div className="mt-0.5 truncate text-xs text-ink-3">{l.person_name}</div>
                    <div className="mt-2.5 flex items-center justify-between">
                      <TierBadge tier={l.tier} score={l.score} />
                      {l.warm_path && <Link2 size={12} className="text-accent-ink" />}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}
