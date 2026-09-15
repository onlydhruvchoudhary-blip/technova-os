import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from './api'

interface Command { id: string; label: string; icon: string; hint?: string; run: () => void }
interface SearchResult { type: string; title: string; link: string }

const ROUTES: Array<{ to: string; icon: string; label: string; group: string }> = [
  { to: '/', icon: '◉', label: 'Dashboard', group: 'Go to' },
  { to: '/leaderboard', icon: '🏆', label: 'Leaderboard', group: 'Go to' },
  { to: '/profile', icon: '👤', label: 'My Portfolio', group: 'Go to' },
  { to: '/academy', icon: '📚', label: 'Academy', group: 'Go to' },
  { to: '/skills', icon: '🌳', label: 'Skill Tree', group: 'Go to' },
  { to: '/challenges', icon: '⚡', label: 'Challenges', group: 'Go to' },
  { to: '/grading', icon: '🎓', label: 'Code Review', group: 'Go to' },
  { to: '/projects', icon: '🛠️', label: 'Projects', group: 'Go to' },
  { to: '/competitions', icon: '🥇', label: 'Competitions', group: 'Go to' },
  { to: '/events', icon: '📅', label: 'Events', group: 'Go to' },
  { to: '/members', icon: '👥', label: 'Members', group: 'Go to' },
  { to: '/governance', icon: '🗳️', label: 'Governance', group: 'Go to' },
  { to: '/store', icon: '🎁', label: 'Rewards Store', group: 'Go to' },
  { to: '/showcase', icon: '✨', label: 'Showcase', group: 'Go to' },
  { to: '/activity', icon: '📡', label: 'Live Activity', group: 'Go to' },
  { to: '/resources', icon: '📖', label: 'Resources', group: 'Go to' },
]

export default function CommandPalette({ open, onClose, isAdmin, onToggleTheme }: {
  open: boolean; onClose: () => void; isAdmin: boolean; onToggleTheme: () => void
}) {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const [remote, setRemote] = useState<SearchResult[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { if (open) { setQ(''); setActive(0); setRemote([]); setTimeout(() => inputRef.current?.focus(), 20) } }, [open])

  // live server search (projects/courses/members/…)
  useEffect(() => {
    if (!open || q.trim().length < 2) { setRemote([]); return }
    const t = setTimeout(() => {
      api.get<{ results: SearchResult[] }>(`/search?q=${encodeURIComponent(q)}`)
        .then(d => setRemote(d.results || [])).catch(() => setRemote([]))
    }, 200)
    return () => clearTimeout(t)
  }, [q, open])

  const go = (to: string) => { onClose(); if (to.startsWith('http')) window.open(to); else nav(to) }

  const actions: Command[] = useMemo(() => {
    const base: Command[] = [
      { id: 'a-theme', label: 'Toggle light / dark theme', icon: '🌓', hint: 'Action', run: () => { onToggleTheme() } },
      { id: 'a-new-project', label: 'New project', icon: '➕', hint: 'Action', run: () => go('/projects') },
      { id: 'a-submit-code', label: 'Submit code for review', icon: '🎓', hint: 'Action', run: () => go('/grading') },
      { id: 'a-store', label: 'Open Rewards Store', icon: '🎁', hint: 'Action', run: () => go('/store') },
    ]
    if (isAdmin) {
      base.push({ id: 'a-admin', label: 'Open Admin console', icon: '⚙️', hint: 'Admin', run: () => go('/admin') })
      base.push({ id: 'a-cc', label: 'Open Command Center (projector)', icon: '📺', hint: 'Admin', run: () => go('/command-center') })
    }
    return base
  }, [isAdmin])

  // Build a flat, filtered, grouped list
  const items = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const routeCmds: Command[] = ROUTES
      .filter(r => !needle || r.label.toLowerCase().includes(needle))
      .map(r => ({ id: `r-${r.to}`, label: r.label, icon: r.icon, hint: 'Go to', run: () => go(r.to) }))
    const actionCmds = actions.filter(a => !needle || a.label.toLowerCase().includes(needle))
    const remoteCmds: Command[] = remote.map((r, i) => ({
      id: `s-${i}`, label: r.title, icon: '🔎', hint: r.type, run: () => go(r.link),
    }))
    return [...actionCmds, ...routeCmds, ...remoteCmds]
  }, [q, actions, remote])

  useEffect(() => { setActive(0) }, [q, remote])

  if (!open) return null

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(i => Math.min(i + 1, items.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(i => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); items[active]?.run() }
    else if (e.key === 'Escape') { e.preventDefault(); onClose() }
  }

  return (
    <div className="cmdk-backdrop" onClick={onClose}>
      <div className="cmdk glass-card" onClick={e => e.stopPropagation()}>
        <input ref={inputRef} className="cmdk-input" placeholder="Type a command or search… (↑↓ to move, ↵ to run, Esc to close)"
          value={q} onChange={e => setQ(e.target.value)} onKeyDown={onKey} />
        <div className="cmdk-list">
          {items.length === 0 && <div className="cmdk-empty">No matches for “{q}”.</div>}
          {items.map((c, i) => (
            <div key={c.id} className={`cmdk-item${i === active ? ' active' : ''}`}
              onMouseEnter={() => setActive(i)} onClick={() => c.run()}>
              <span className="cmdk-ico">{c.icon}</span>
              <span className="cmdk-label">{c.label}</span>
              {c.hint && <span className="cmdk-hint">{c.hint}</span>}
            </div>
          ))}
        </div>
        <div className="cmdk-foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> select</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}
