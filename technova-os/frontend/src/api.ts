// Thin typed API client. All calls go through /api (proxied to the backend).
const TOKEN_KEY = 'technova_token'

// Primary store is in-memory so auth works even where localStorage is unavailable
// (e.g. sandboxed/opaque-origin iframes like the live preview). localStorage is used
// as best-effort persistence across reloads when it's accessible.
let memToken: string | null = null
try { memToken = localStorage.getItem(TOKEN_KEY) } catch { /* storage blocked */ }

export function getToken() {
  if (memToken) return memToken
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
export function setToken(t: string) {
  memToken = t
  try { localStorage.setItem(TOKEN_KEY, t) } catch { /* storage blocked; memory is enough */ }
}
export function clearToken() {
  memToken = null
  try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function req<T = any>(method: string, path: string, body?: any, isForm = false): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
    // Also send as a custom header: some preview/reverse proxies strip `Authorization`,
    // but pass custom headers through. The backend accepts either.
    headers['X-Auth-Token'] = token
  }
  let payload: any = undefined
  if (body !== undefined) {
    if (isForm) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
      payload = new URLSearchParams(body).toString()
    } else {
      headers['Content-Type'] = 'application/json'
      payload = JSON.stringify(body)
    }
  }
  // credentials:'include' sends the auth cookie — this is the primary auth mechanism because
  // some preview/reverse proxies strip the Authorization header. The header is still sent as a
  // fallback for environments (like local dev) where cookies aren't in play.
  const res = await fetch(`/api${path}`, { method, headers, body: payload, credentials: 'include' })
  if (res.status === 204) return undefined as T
  const text = await res.text()
  const data = text ? JSON.parse(text) : undefined
  if (!res.ok) {
    const detail = data?.detail
    const msg = Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ')
      : (detail || res.statusText)
    throw new ApiError(res.status, msg)
  }
  return data as T
}

export const api = {
  get: <T = any>(p: string) => req<T>('GET', p),
  post: <T = any>(p: string, body?: any) => req<T>('POST', p, body),
  patch: <T = any>(p: string, body?: any) => req<T>('PATCH', p, body),
  form: <T = any>(p: string, body: any) => req<T>('POST', p, body, true),
}
