import { Pencil, Plus, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { copy } from '../../copy'
import type { Founder, Product } from '../../types'
import { cx } from '../ui'

function Field({ label, flash, edited, children }: { label: string; flash: number; edited: boolean; children: ReactNode }) {
  return (
    <div
      // Re-keying on each update replays the highlight, so the founder sees what the last chat turn filled in.
      key={flash}
      className={cx('-mx-3 grid grid-cols-[130px_1fr] items-start gap-4 rounded-md border-b border-line px-3 py-3.5 last:border-0', flash > 0 && 'flash')}
    >
      <div className="flex items-center gap-1.5 pt-1 text-xs font-medium text-ink-2">
        {label}
        {edited && (
          <span title={copy.setup.editedByYou}>
            <Pencil size={10} className="text-ink-3" />
          </span>
        )}
      </div>
      <div>{children}</div>
    </div>
  )
}

const inputCls =
  'w-full rounded-md bg-transparent px-2 py-1 text-sm outline-none placeholder:text-ink-3 hover:bg-sunken focus:bg-surface focus:ring-1 focus:ring-line-strong'

function TagInput({ values, onChange }: { values: string[]; onChange: (v: string[]) => void }) {
  const [adding, setAdding] = useState('')
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {values.map((v) => (
        <span key={v} className="group inline-flex items-center gap-1 rounded-md bg-sunken py-1 pl-2 pr-1 text-[13px]">
          {v}
          <button onClick={() => onChange(values.filter((x) => x !== v))} className="rounded p-0.5 text-ink-3 opacity-0 hover:text-ink group-hover:opacity-100">
            <X size={12} />
          </button>
        </span>
      ))}
      <span className="inline-flex items-center text-ink-3">
        <Plus size={13} />
        <input
          value={adding}
          onChange={(e) => setAdding(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && adding.trim()) {
              if (!values.includes(adding.trim())) onChange([...values, adding.trim()])
              setAdding('')
            }
          }}
          placeholder="Add"
          className="w-20 bg-transparent px-1 py-1 text-[13px] outline-none placeholder:text-ink-3 focus:w-40"
        />
      </span>
    </div>
  )
}

export function ProfileForm({
  product,
  founder,
  onChange,
  flashes,
  handEdited,
  disabled,
}: {
  product: Product
  founder: Founder
  onChange: (product: Product, founder: Founder) => void
  flashes: Record<string, number>
  handEdited: string[]
  disabled: boolean
}) {
  const p = <K extends keyof Product>(k: K) => (v: Product[K]) => onChange({ ...product, [k]: v }, founder)
  const f = <K extends keyof Founder>(k: K) => (v: Founder[K]) => onChange(product, { ...founder, [k]: v })
  const field = (key: string, label: string, children: ReactNode) => (
    <Field label={label} flash={flashes[key] ?? 0} edited={handEdited.includes(key)}>
      {children}
    </Field>
  )

  return (
    <fieldset disabled={disabled} className={cx('space-y-6 transition-opacity', disabled && 'opacity-60')}>
      <div className="rounded-xl border border-line bg-surface px-5 py-2">
        {field('product.product', 'What it is',
          <textarea value={product.product} onChange={(e) => p('product')(e.target.value)} rows={2} placeholder={copy.setup.emptyField} className={`${inputCls} resize-none`} />)}
        {field('product.buyer_roles', 'Who buys it', <TagInput values={product.buyer_roles} onChange={p('buyer_roles')} />)}
        {field('product.industries', 'Industries', <TagInput values={product.industries} onChange={p('industries')} />)}
        {field('product.pains', 'Problems it fixes', <TagInput values={product.pains} onChange={p('pains')} />)}
      </div>

      <div>
        <div className="rounded-xl border border-line bg-surface px-5 py-2">
          {field('founder.name', 'Your name',
            <input value={founder.name} onChange={(e) => f('name')(e.target.value)} placeholder={copy.setup.emptyField} className={inputCls} />)}
          {field('founder.past_companies', 'Worked at', <TagInput values={founder.past_companies} onChange={f('past_companies')} />)}
          {field('founder.schools', 'Studied at', <TagInput values={founder.schools} onChange={f('schools')} />)}
          {field('founder.investors', 'Backed by', <TagInput values={founder.investors} onChange={f('investors')} />)}
        </div>
      </div>
    </fieldset>
  )
}
