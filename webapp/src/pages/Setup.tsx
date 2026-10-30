import { Check, RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { ChatPane } from '../components/setup/ChatPane'
import { ProfileForm } from '../components/setup/ProfileForm'
import { Button, PageHeader } from '../components/ui'
import { copy } from '../copy'
import type { Founder, Product, SetupDraft } from '../types'

// Mirrors REQUIRED in app/api/routes.py, which checks it again on finalize.
const REQUIRED = [
  'product.product',
  'product.buyer_roles',
  'product.industries',
  'product.pains',
  'founder.background',
  'founder.name',
]

const EMPTY_PRODUCT: Product = { product: '', buyer_roles: [], industries: [], pains: [] }
const EMPTY_FOUNDER: Founder = { name: '', past_companies: [], schools: [], investors: [] }

function stillNeeded({ product, founder, skipped }: SetupDraft): string[] {
  const filled: Record<string, boolean> = {}
  Object.entries(product).forEach(([k, v]) => (filled[`product.${k}`] = v.length > 0))
  Object.entries(founder).forEach(([k, v]) => (filled[`founder.${k}`] = v.length > 0))
  filled['founder.background'] = founder.past_companies.length + founder.schools.length + founder.investors.length > 0
  return REQUIRED.filter((k) => !filled[k] && !skipped.includes(k))
}

/** Field keys ('product.pains', 'founder.name') whose value differs between two drafts. */
function changedFields(a: Pick<SetupDraft, 'product' | 'founder'>, b: Pick<SetupDraft, 'product' | 'founder'>): string[] {
  const diff = (prefix: string, x: object, y: object) =>
    Object.keys(y)
      .filter((k) => JSON.stringify((x as Record<string, unknown>)[k]) !== JSON.stringify((y as Record<string, unknown>)[k]))
      .map((k) => `${prefix}.${k}`)
  return [...diff('product', a.product, b.product), ...diff('founder', a.founder, b.founder)]
}

const snapshot = (d: SetupDraft) => JSON.stringify(d)

// Before anything is saved, or after starting over.
const freshDraft = (): SetupDraft => ({
  messages: [{ role: 'scout', text: copy.setup.greeting }],
  product: EMPTY_PRODUCT,
  founder: EMPTY_FOUNDER,
  skipped: [],
})

export function Setup() {
  const [draft, setDraft] = useState<SetupDraft>(freshDraft)
  const [savedSnapshot, setSavedSnapshot] = useState<string | null>(null) // the draft as last finalized
  const [loading, setLoading] = useState(true)
  const [handEdited, setHandEdited] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [thinking, setThinking] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [flashes, setFlashes] = useState<Record<string, number>>({})

  const isSaved = savedSnapshot !== null && snapshot(draft) === savedSnapshot
  const dirty = !isSaved && draft.messages.length > 1 // something typed that isn't finalized

  // The draft only lives in this tab, so warn before a refresh or close throws it away.
  useEffect(() => {
    if (!dirty) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  // Open on what was last finalized; only Start over clears it.
  useEffect(() => {
    api
      .getSetup()
      .then(({ saved, messages, product, founder, skipped }) => {
        if (!saved) return
        const loaded: SetupDraft = { messages: messages.length ? messages : freshDraft().messages, product, founder, skipped }
        setDraft(loaded)
        setSavedSnapshot(snapshot(loaded))
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  const missing = stillNeeded(draft)
  const label = (k: string) => copy.setup.detailLabels[k] ?? k
  const missingText = missing.map(label).join(', ')

  const send = async (text: string) => {
    setError(null)
    setThinking(true)
    const before = draft
    // Show the founder's message right away; Scout's reply is added when it arrives.
    setDraft({ ...draft, messages: [...draft.messages, { role: 'founder', text }] })
    try {
      const turn = await api.sendSetupMessage(text, before, handEdited)
      setDraft({
        messages: [...before.messages, { role: 'founder', text }, { role: 'scout', text: turn.reply }],
        product: turn.product,
        founder: turn.founder,
        skipped: turn.skipped,
      })
      setFlashes((f) => ({ ...f, ...Object.fromEntries(changedFields(before, turn).map((k) => [k, (f[k] ?? 0) + 1])) }))
      return true
    } catch (e) {
      setDraft(before)
      setError((e as Error).message)
      return false
    } finally {
      setThinking(false)
    }
  }

  const edit = (product: Product, founder: Founder) => {
    const changed = changedFields(draft, { product, founder })
    setHandEdited((h) => [...new Set([...h, ...changed])])
    setDraft({ ...draft, product, founder })
  }

  const finalize = async () => {
    setError(null)
    setFinalizing(true)
    try {
      await api.finalizeSetup(draft)
      setSavedSnapshot(snapshot(draft))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setFinalizing(false)
    }
  }

  const reset = async () => {
    if (!confirm(copy.setup.resetConfirm)) return
    try {
      await api.startOver()
    } catch (e) {
      setError((e as Error).message)
      return
    }
    setDraft(freshDraft())
    setSavedSnapshot(null)
    setHandEdited([])
    setFlashes({})
    setError(null)
  }

  const saveButton = isSaved ? (
    <Button disabled>
      <Check size={14} /> {copy.setup.saved}
    </Button>
  ) : (
    <Button
      variant="accent"
      onClick={finalize}
      disabled={missing.length > 0 || loading || thinking || finalizing}
      title={missing.length ? copy.setup.finalizeNeeds(missingText) : undefined}
    >
      <Check size={14} /> {finalizing ? copy.setup.finalizing : savedSnapshot ? copy.setup.saveChanges : copy.setup.finalize}
    </Button>
  )

  return (
    <>
      <PageHeader
        title={copy.setup.title}
        subtitle={copy.setup.subtitle}
        actions={
          <>
            <Button variant="ghost" onClick={reset} disabled={loading || thinking || finalizing}>
              <RotateCcw size={14} /> {copy.setup.reset}
            </Button>
            {saveButton}
          </>
        }
      />
      <div className="grid grid-cols-[minmax(0,5fr)_minmax(0,6fr)] gap-8">
        <div className="sticky top-0 h-[calc(100vh-14rem)] min-h-[480px]">
          <ChatPane messages={draft.messages} thinking={thinking} error={error} onSend={send} disabled={loading} />
        </div>
        <div>
          <ProfileForm
            product={draft.product}
            founder={draft.founder}
            onChange={edit}
            flashes={flashes}
            handEdited={handEdited}
            disabled={loading || thinking || finalizing}
          />
        </div>
      </div>
    </>
  )
}
