// Calls to the FastAPI backend. Setup, Who should buy this, leads and the activity panel are wired up; other pages still read mock.ts.
import type { Lead, Profile, RoomEvent, SavedSetup, SetupDraft, SetupTurn } from './types'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(`Can't reach the backend at ${API_URL}. Is uvicorn running?`)
  }
  if (!res.ok) {
    const detail = await res.json().then((j) => j.detail, () => null)
    throw new ApiError(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  // Saves nothing: the draft lives in the browser until it's finalized.
  sendSetupMessage: (text: string, draft: SetupDraft, handEdited: string[]) =>
    call<SetupTurn>('POST', '/setup/chat', { text, ...draft, hand_edited: handEdited }),
  finalizeSetup: (draft: SetupDraft) => call<{ finalized: boolean }>('POST', '/setup/finalize', draft),
  getSetup: () => call<SavedSetup>('GET', '/setup'),
  // Deletes everything setup saved.
  startOver: () => call<{ cleared: boolean }>('DELETE', '/setup'),
  getProfile: () => call<Profile>('GET', '/who'),
  // Scout works out who should buy it from the saved setup; `again` asks for a different answer.
  generateWho: (again = false) => call<Profile>('POST', '/who/generate', { again }),
  addExpansion: (name: string) => call<Profile>('POST', '/who/add', { name }),
  // Every lead Scout has saved, newest first.
  getLeads: () => call<Lead[]>('GET', '/leads'),
  // The Band room: recent messages, posting as the founder, and new messages as server-sent events.
  getActivity: () => call<RoomEvent[]>('GET', '/activity'),
  sendToTeam: (text: string) => call<{ sent: boolean }>('POST', '/activity', { text }),
  activityStreamUrl: `${API_URL}/activity/stream`,
}
