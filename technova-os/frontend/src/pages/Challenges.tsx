import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Spinner, DiffBadge, Empty } from '../ui'

export default function Challenges() {
  const [challenges, setChallenges] = useState<any[]>([])
  const [tab, setTab] = useState<'all' | 'weekly'>('all')
  useEffect(() => {
    const ac = new AbortController()
    api.get('/challenges', ac.signal).then(setChallenges).catch(() => {})
    return () => ac.abort()
  }, [])
  if (!challenges) return <Spinner />

  const weekly = challenges.filter(c => c.is_weekly)
  const regular = challenges.filter(c => !c.is_weekly)
  const shown = tab === 'weekly' ? weekly : regular

  return (
    <div>
      <div className="page-head"><h1>Challenges</h1>
        <p>Solve problems, get instantly judged against hidden tests, earn points and grow skills.</p></div>
      <div className="row" style={{ marginBottom: 16 }}>
        <button className={`btn sm ${tab === 'all' ? 'primary' : 'ghost'}`} onClick={() => setTab('all')}>Practice ({regular.length})</button>
        <button className={`btn sm ${tab === 'weekly' ? 'primary' : 'ghost'}`} onClick={() => setTab('weekly')}>⚡ Weekly ({weekly.length})</button>
      </div>
      {shown.length === 0 ? <Empty icon="⚡" title="No challenges here yet" /> : (
        <div className="grid g2">
          {shown.map(c => (
            <Link to={`/challenges/${c.slug}`} key={c.id} className="card" style={{ display: 'block' }}>
              <div className="row between" style={{ marginBottom: 8 }}>
                <div className="row">
                  {c.is_weekly && <span className="badge w">{c.weekly_kind || 'Weekly'}</span>}
                  <DiffBadge d={c.difficulty} />
                </div>
                {c.solved ? <span className="badge g">✓ Solved</span> : <span className="badge p">+{c.points}</span>}
              </div>
              <h3 style={{ margin: '0 0 6px' }}>{c.title}</h3>
              <span className="faint" style={{ fontSize: 12 }}>👥 {c.solvers} member{c.solvers === 1 ? '' : 's'} solved</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
