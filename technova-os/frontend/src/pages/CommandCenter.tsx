import { useEffect, useState } from 'react'
import { api } from '../api'
import { Spinner } from '../ui'

export default function CommandCenter() {
  const [d, setD] = useState<any>(null)
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const load = () => api.get('/command-center').then(setD).catch(() => {})
    load(); const t = setInterval(load, 30000)
    const c = setInterval(() => setNow(new Date()), 1000)
    return () => { clearInterval(t); clearInterval(c) }
  }, [])
  if (!d) return <Spinner />

  return (
    <div className="cc">
      <div className="row between" style={{ marginBottom: 24 }}>
        <div className="row" style={{ gap: 14 }}>
          <div className="brand-logo" style={{ width: 52, height: 52, fontSize: 24 }}>T</div>
          <div><h1 style={{ margin: 0 }}>TECHNOVA</h1><div className="faint" style={{ letterSpacing: 4, fontSize: 12 }}>COMMAND CENTER</div></div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: 34, fontWeight: 800 }}>{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
          <div className="faint">{now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</div>
        </div>
      </div>

      <div className="grid g4" style={{ marginBottom: 20 }}>
        {[['Members', d.stats.members, '👥'], ['Projects', d.stats.projects, '🛠️'], ['Events', d.stats.events, '📅'], ['Challenges', d.stats.challenges, '⚡']].map(([l, n, i]: any) =>
          <div className="card stat" key={l}><span className="ico" style={{ fontSize: 28 }}>{i}</span><span className="n" style={{ fontSize: 40 }}>{n}</span><span className="l">{l}</span></div>)}
      </div>

      <div className="cc-grid">
        <div className="grid">
          <div className="card"><h2 style={{ marginTop: 0 }}>🏆 Leaderboard</h2>
            {d.board.map((r: any) => (
              <div key={r.user_id} className="row between" style={{ padding: '10px 0', borderTop: '1px solid var(--border)', fontSize: 17 }}>
                <span className="row"><span className="mono" style={{ width: 40, fontWeight: 800, color: r.rank <= 3 ? 'var(--primary)' : 'var(--text-dim)' }}>
                  {r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : `#${r.rank}`}</span>
                  <strong>{r.name}</strong></span>
                <span className="badge p" style={{ fontSize: 15 }}>{r.points}</span>
              </div>
            ))}
          </div>
          <div className="card"><h2 style={{ marginTop: 0 }}>🚀 Active projects</h2>
            <div className="row wrap" style={{ gap: 10 }}>
              {d.active_projects.map((p: any) => (
                <span key={p.slug} className="badge a" style={{ fontSize: 14, padding: '6px 12px' }}>{p.title} · {p.state}</span>))}
              {d.active_projects.length === 0 && <span className="faint">No active projects.</span>}
            </div>
          </div>
        </div>

        <div className="grid">
          <div className="card"><h2 style={{ marginTop: 0 }}>📅 Upcoming events</h2>
            {d.upcoming_events.length === 0 && <span className="faint">Nothing scheduled.</span>}
            {d.upcoming_events.map((e: any, i: number) => (
              <div key={i} style={{ padding: '10px 0', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontWeight: 700, fontSize: 17 }}>{e.title}</div>
                <div className="faint">{e.kind} · {new Date(e.starts_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} · {e.location}</div>
              </div>
            ))}
          </div>
          <div className="card"><h2 style={{ marginTop: 0 }}>⚡ Weekly challenges</h2>
            {d.weekly_challenges.map((c: any) => <div key={c.slug} style={{ padding: '8px 0' }}><strong>{c.title}</strong> <span className="badge w">{c.kind}</span></div>)}
            {d.weekly_challenges.length === 0 && <span className="faint">None active.</span>}
          </div>
          <div className="card"><h2 style={{ marginTop: 0 }}>📢 Announcements</h2>
            {d.announcements.map((a: any, i: number) => <div key={i} style={{ padding: '8px 0', borderTop: i ? '1px solid var(--border)' : 'none' }}>
              <strong>{a.title}</strong><div className="faint" style={{ fontSize: 14 }}>{a.body}</div></div>)}
          </div>
        </div>
      </div>
    </div>
  )
}
