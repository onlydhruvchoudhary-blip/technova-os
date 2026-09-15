import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../store'
import { Spinner, Bar, StateBadge, DiffBadge } from '../ui'
import ActivityFeed from '../ActivityFeed'

export default function Dashboard() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<any>(null)
  const [courses, setCourses] = useState<any[]>([])
  const [challenges, setChallenges] = useState<any[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [board, setBoard] = useState<any>(null)

  useEffect(() => {
    Promise.all([
      api.get('/me/profile'), api.get('/academy/courses'), api.get('/challenges?weekly=true'),
      api.get('/events'), api.get('/announcements'), api.get('/leaderboard'),
    ]).then(([p, c, ch, e, a, b]) => {
      setProfile(p); setCourses(c); setChallenges(ch)
      setEvents(e.filter((x: any) => new Date(x.starts_at) >= new Date()).slice(0, 3))
      setAnnouncements(a); setBoard(b)
    })
  }, [])

  if (!profile || !board) return <Spinner />
  const inProgress = courses.filter(c => c.completed > 0 && c.progress < 100).slice(0, 3)
  const suggested = courses.filter(c => c.completed === 0).slice(0, 3)

  return (
    <div>
      <div className="page-head">
        <h1>Welcome back, {user!.name.split(' ')[0]} 👋</h1>
        <p>Here's what's happening across TECHNOVA today.</p>
      </div>

      <div className="grid g4" style={{ marginBottom: 18 }}>
        <div className="card stat"><span className="ico">⭐</span><span className="n">{profile.points}</span><span className="l">Points</span></div>
        <div className="card stat"><span className="ico">🏆</span><span className="n">#{profile.rank ?? '—'}</span><span className="l">Club Rank</span></div>
        <div className="card stat"><span className="ico">⚡</span><span className="n">{profile.stats.challenges_solved}</span><span className="l">Challenges Solved</span></div>
        <div className="card stat"><span className="ico">🌳</span><span className="n">{profile.stats.skills}</span><span className="l">Skills Growing</span></div>
      </div>

      <div className="grid g3">
        <div style={{ gridColumn: 'span 2' }} className="grid">
          <div className="card">
            <div className="card-h"><h3>Continue learning</h3><Link className="btn ghost sm" to="/academy">All courses →</Link></div>
            {inProgress.length === 0 && suggested.length === 0 && <div className="faint">No courses yet.</div>}
            {(inProgress.length ? inProgress : suggested).map(c => (
              <Link to={`/academy/${c.slug}`} key={c.id} style={{ display: 'block', marginBottom: 12 }}>
                <div className="row between" style={{ marginBottom: 5 }}>
                  <strong style={{ fontSize: 14 }}>{c.title}</strong>
                  <span className="faint" style={{ fontSize: 12 }}>{c.completed}/{c.lessons} · {c.progress}%</span>
                </div>
                <Bar value={c.progress} />
              </Link>
            ))}
          </div>

          <div className="card">
            <div className="card-h"><h3>⚡ Challenge of the Week</h3><Link className="btn ghost sm" to="/challenges">All →</Link></div>
            {challenges.length === 0 && <div className="faint">No weekly challenge right now.</div>}
            {challenges.map(ch => (
              <Link to={`/challenges/${ch.slug}`} key={ch.id} className="row between"
                style={{ padding: '10px 0', borderTop: '1px solid var(--border)' }}>
                <div><div style={{ fontWeight: 600 }}>{ch.title}</div>
                  <span className="faint" style={{ fontSize: 12 }}>{ch.weekly_kind} · {ch.solvers} solved</span></div>
                <div className="row"><DiffBadge d={ch.difficulty} /><span className="badge p">+{ch.points}</span>
                  {ch.solved && <span className="badge g">✓</span>}</div>
              </Link>
            ))}
          </div>
        </div>

        <div className="grid">
          <div className="card">
            <div className="card-h"><h3>🏆 Top members</h3><Link className="btn ghost sm" to="/leaderboard">Full →</Link></div>
            {board.board.slice(0, 5).map((r: any) => (
              <div key={r.user_id} className="row between" style={{ padding: '7px 0' }}>
                <div className="row"><span className="mono faint" style={{ width: 22 }}>#{r.rank}</span><span style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</span></div>
                <span className="badge p">{r.points}</span>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="card-h"><h3>📅 Upcoming</h3><Link className="btn ghost sm" to="/events">All →</Link></div>
            {events.length === 0 && <div className="faint">No upcoming events.</div>}
            {events.map(e => (
              <div key={e.id} style={{ padding: '8px 0', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{e.title}</div>
                <div className="faint" style={{ fontSize: 12 }}>{e.kind} · {new Date(e.starts_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} · {e.location}</div>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="card-h"><h3>📢 Announcements</h3></div>
            {announcements.slice(0, 3).map(a => (
              <div key={a.id} style={{ padding: '8px 0', borderTop: '1px solid var(--border)' }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{a.pinned && '📌 '}{a.title}</div>
                <div className="faint" style={{ fontSize: 12 }}>{a.body}</div>
              </div>
            ))}
          </div>

          <ActivityFeed compact limit={6} />
        </div>
      </div>
    </div>
  )
}
