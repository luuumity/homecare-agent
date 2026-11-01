import { api } from './api'

type AuthState = 'unknown' | 'in' | 'out'

let state: AuthState = 'unknown'

export function markIn() {
  state = 'in'
}

export function markOut() {
  state = 'out'
}

export async function ensureAuth(): Promise<boolean> {
  if (state === 'unknown') {
    try {
      await api.auth.me()
      state = 'in'
    } catch {
      state = 'out'
    }
  }
  return state === 'in'
}
