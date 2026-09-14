import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, setToken, clearToken, getToken } from './api'

export interface User { id: number; email: string; name: string; role: string; bio: string; avatar_seed: string }

interface AuthCtx {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}
const Ctx = createContext<AuthCtx>(null as any)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    // Try regardless of a stored token — auth may be held in an httpOnly cookie
    // (the preview proxy strips the Authorization header, so the cookie is authoritative).
    try { setUser(await api.get<User>('/auth/me')) }
    catch { clearToken(); setUser(null) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const login = async (email: string, password: string) => {
    const r = await api.form<{ access_token: string }>('/auth/login', { username: email, password })
    setToken(r.access_token); await refresh()
  }
  const register = async (email: string, name: string, password: string) => {
    const r = await api.post<{ access_token: string }>('/auth/register', { email, name, password })
    setToken(r.access_token); await refresh()
  }
  const logout = () => { api.post('/auth/logout').catch(() => {}); clearToken(); setUser(null) }

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>
}

// ---- theme
const ThemeCtx = createContext<{ theme: string; toggle: () => void }>({ theme: 'dark', toggle: () => {} })
export const useTheme = () => useContext(ThemeCtx)
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState(localStorage.getItem('technova_theme') || 'dark')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('technova_theme', theme)
  }, [theme])
  return <ThemeCtx.Provider value={{ theme, toggle: () => setTheme(t => t === 'dark' ? 'light' : 'dark') }}>{children}</ThemeCtx.Provider>
}

// ---- toasts
type Toast = { id: number; kind: string; msg: string }
const ToastCtx = createContext<{ push: (msg: string, kind?: string) => void }>({ push: () => {} })
export const useToast = () => useContext(ToastCtx)
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = (msg: string, kind = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, kind, msg }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3800)
  }
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="toast-wrap">
        {toasts.map(t => <div key={t.id} className={`toast ${t.kind}`}>{t.msg}</div>)}
      </div>
    </ToastCtx.Provider>
  )
}
