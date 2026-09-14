// Shared UI primitives.
import React from 'react'

export function Avatar({ seed, name, size = 36 }: { seed: string; name?: string; size?: number }) {
  const initials = (name || seed).split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
  const hue = [...seed].reduce((a, c) => a + c.charCodeAt(0), 0) % 360
  return (
    <div className="avatar" style={{
      width: size, height: size, fontSize: size * 0.38,
      background: `linear-gradient(135deg, hsl(${hue},70%,55%), hsl(${(hue + 60) % 360},70%,50%))`,
    }}>{initials}</div>
  )
}

export function Spinner() {
  return <div className="loading"><div className="spinner" /></div>
}

export function Empty({ icon = '📭', title, sub }: { icon?: string; title: string; sub?: string }) {
  return (
    <div className="empty">
      <div className="e-ico">{icon}</div>
      <div style={{ fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>{title}</div>
      {sub && <div style={{ fontSize: 13 }}>{sub}</div>}
    </div>
  )
}

export function Bar({ value, max = 100 }: { value: number; max?: number }) {
  return <div className="bar"><i style={{ width: `${Math.min(100, (value / max) * 100)}%` }} /></div>
}

export function Pips({ level, total = 4 }: { level: number; total?: number }) {
  return <div className="pips">{Array.from({ length: total }).map((_, i) =>
    <span key={i} className={`pip ${i < level ? 'on' : ''}`} />)}</div>
}

const ROLE_STYLE: Record<string, string> = {
  SUPER_ADMIN: 'r', CLUB_HEAD: 'p', ADVISOR: 'a', MENTOR: 'w', COMMITTEE: 'g', MEMBER: '', GUEST: '',
}
export function RoleBadge({ role }: { role: string }) {
  return <span className={`badge ${ROLE_STYLE[role] || ''}`}>{role.replace('_', ' ')}</span>
}

const STATE_STYLE: Record<string, string> = {
  IDEA: '', PROPOSED: 'a', TEAM_FORMING: 'w', PLANNING: 'w', DEVELOPMENT: 'p',
  TESTING: 'w', DEMO: 'a', COMPLETED: 'g', SHOWCASE: 'g',
}
export function StateBadge({ state }: { state: string }) {
  return <span className={`badge ${STATE_STYLE[state] || ''}`}>{state.replace('_', ' ')}</span>
}

const DIFF: Record<string, string> = { Easy: 'g', Medium: 'w', Hard: 'r' }
export function DiffBadge({ d }: { d: string }) {
  return <span className={`badge ${DIFF[d] || ''}`}>{d}</span>
}

export function Modal({ title, children, onClose, wide }: { title: string; children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', zIndex: 200,
      display: 'grid', placeItems: 'center', padding: 16,
    }}>
      <div onClick={e => e.stopPropagation()} className="card" style={{ width: '100%', maxWidth: wide ? 760 : 480, maxHeight: '88vh', overflow: 'auto' }}>
        <div className="card-h"><h3>{title}</h3><button className="btn ghost sm" onClick={onClose}>✕</button></div>
        {children}
      </div>
    </div>
  )
}
