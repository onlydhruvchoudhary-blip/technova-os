import React, { useEffect, useState } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth, useTheme } from './store'
import { api } from './api'
import { Avatar, RoleBadge } from './ui'

const NAV = [
  { section: 'Overview' },
  { to: '/', icon: '◉', label: 'Dashboard' },
  { to: '/leaderboard', icon: '🏆', label: 'Leaderboard' },
  { to: '/profile', icon: '👤', label: 'My Portfolio' },
  { section: 'Grow' },
  { to: '/academy', icon: '📚', label: 'Academy' },
  { to: '/skills', icon: '🌳', label: 'Skill Tree' },
  { to: '/challenges', icon: '⚡', label: 'Challenges' },
  { section: 'Build & Compete' },
  { to: '/projects', icon: '🛠️', label: 'Projects' },
  { to: '/competitions', icon: '🥇', label: 'Competitions' },
  { to: '/events', icon: '📅', label: 'Events' },
  { section: 'Club' },
  { to: '/members', icon: '👥', label: 'Members' },
  { to: '/showcase', icon: '✨', label: 'Showcase' },
  { to: '/resources', icon: '📖', label: 'Resources' },
]
const ADMIN_ROLES = ['COMMITTEE', 'MENTOR', 'ADVISOR', 'CLUB_HEAD', 'SUPER_ADMIN']
const MOBILE = [
  { to: '/', icon: '◉', label: 'Home' },
  { to: '/academy', icon: '📚', label: 'Learn' },
  { to: '/challenges', icon: '⚡', label: 'Solve' },
  { to: '/leaderboard', icon: '🏆', label: 'Ranks' },
  { to: '/profile', icon: '👤', label: 'Me' },
]
const MOBILE_ADMIN = { to: '/admin', icon: '⚙️', label: 'Admin' }

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const nav = useNavigate()
  const loc = useLocation()
  const [unread, setUnread] = useState(0)
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifs, setNotifs] = useState<any[]>([])
  const [q, setQ] = useState('')
  const [results, setResults] = useState<any[]>([])
  const isAdmin = user && ADMIN_ROLES.includes(user.role)

  const loadNotifs = async () => {
    try { const d = await api.get('/notifications'); setUnread(d.unread); setNotifs(d.items) } catch {}
  }
  useEffect(() => { loadNotifs(); const t = setInterval(loadNotifs, 20000); return () => clearInterval(t) }, [])
  useEffect(() => { setNotifOpen(false); setResults([]); setQ('') }, [loc.pathname])

  useEffect(() => {
    if (q.length < 2) { setResults([]); return }
    const t = setTimeout(async () => {
      try { const d = await api.get(`/search?q=${encodeURIComponent(q)}`); setResults(d.results) } catch {}
    }, 220)
    return () => clearTimeout(t)
  }, [q])

  const openNotifs = async () => {
    setNotifOpen(o => !o)
    if (!notifOpen && unread > 0) { await api.post('/notifications/read'); setUnread(0) }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">T</div>
          <div className="brand-name">TECHNOVA<small>OPERATING SYSTEM</small></div>
        </div>
        <nav className="nav">
          {NAV.map((item, i) => item.section
            ? <div key={i} className="nav-section">{item.section}</div>
            : <NavLink key={item.to} to={item.to!} end={item.to === '/'}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                <span className="ico">{item.icon}</span>{item.label}
              </NavLink>)}
          {isAdmin && <>
            <div className="nav-section">Manage</div>
            <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="ico">⚙️</span>Admin
            </NavLink>
            <a className="nav-item" href="/command-center" target="_blank" rel="noreferrer">
              <span className="ico">📺</span>Command Center
            </a>
          </>}
        </nav>
        <div style={{ padding: 14, borderTop: '1px solid var(--border)' }}>
          <div className="row" style={{ cursor: 'pointer' }} onClick={() => nav('/profile')}>
            <Avatar seed={user!.avatar_seed} name={user!.name} size={38} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user!.name}</div>
              <RoleBadge role={user!.role} />
            </div>
          </div>
        </div>
      </aside>

      <div className="main">
        <div className="topbar">
          <div style={{ position: 'relative', flex: 1, maxWidth: 420 }}>
            <input className="input" placeholder="Search projects, courses, members…"
              value={q} onChange={e => setQ(e.target.value)} style={{ padding: '8px 12px' }} />
            {results.length > 0 && (
              <div className="card" style={{ position: 'absolute', top: 44, left: 0, right: 0, zIndex: 40, padding: 6 }}>
                {results.map((r, i) => (
                  <div key={i} className="nav-item" style={{ margin: 0 }}
                    onClick={() => { r.link.startsWith('http') ? window.open(r.link) : nav(r.link); setResults([]); setQ('') }}>
                    <span className="badge" style={{ marginRight: 6 }}>{r.type}</span>{r.title}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="spacer" />
          <button className="btn ghost sm" onClick={toggle} title="Toggle theme">{theme === 'dark' ? '☀️' : '🌙'}</button>
          <div style={{ position: 'relative' }}>
            <button className="btn ghost sm" onClick={openNotifs}>
              🔔 {unread > 0 && <span className="badge r" style={{ padding: '1px 6px' }}>{unread}</span>}
            </button>
            {notifOpen && (
              <div className="card" style={{ position: 'absolute', right: 0, top: 42, width: 340, zIndex: 40, maxHeight: 420, overflow: 'auto' }}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Notifications</h3>
                {notifs.length === 0 && <div className="faint" style={{ fontSize: 13 }}>Nothing yet.</div>}
                {notifs.map(n => (
                  <div key={n.id} onClick={() => n.link && nav(n.link)}
                    style={{ padding: '8px 4px', borderTop: '1px solid var(--border)', cursor: n.link ? 'pointer' : 'default' }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{n.title}</div>
                    <div className="faint" style={{ fontSize: 12 }}>{n.body}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button className="btn ghost sm" onClick={() => { logout(); nav('/') }}>Sign out</button>
        </div>
        <div className="content">{children}</div>
      </div>

      <nav className="mobile-nav">
        {[...MOBILE, ...(isAdmin ? [MOBILE_ADMIN] : [])].map(m => (
          <NavLink key={m.to} to={m.to} end={m.to === '/'}
            className={({ isActive }) => isActive ? 'active' : ''}>
            <span className="ico">{m.icon}</span>{m.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
