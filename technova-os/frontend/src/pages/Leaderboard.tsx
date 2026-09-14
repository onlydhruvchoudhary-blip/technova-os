import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Spinner, Avatar, RoleBadge } from '../ui'

const CAT_COLORS: Record<string, string> = {
  learning: '#5b8cff', challenge: '#22d3ee', attendance: '#34d399',
  project: '#7c5cff', social: '#fbbf24', competition: '#f87171',
}

export default function Leaderboard() {
  const [data, setData] = useState<any>(null)
  useEffect(() => { api.get('/leaderboard').then(setData) }, [])
  if (!data) return <Spinner />
  const breakdown = data.me.breakdown || {}
  const totalMine = Object.values(breakdown).reduce((a: number, b: any) => a + b, 0) as number

  return (
    <div>
      <div className="page-head"><h1>Club Leaderboard</h1>
        <p>Points reward real contribution — learning, solving, building, helping, attending. Not spam.</p></div>

      <div className="grid g3" style={{ marginBottom: 18 }}>
        <div className="card stat"><span className="ico">🏆</span><span className="n">#{data.me.rank ?? '—'}</span><span className="l">Your Rank</span></div>
        <div className="card stat"><span className="ico">⭐</span><span className="n">{data.me.points}</span><span className="l">Your Points</span></div>
        <div className="card">
          <div className="l" style={{ marginBottom: 8 }}>How you earned them</div>
          {totalMine === 0 ? <div className="faint" style={{ fontSize: 13 }}>Start learning and solving to earn points!</div> : (
            <>
              <div style={{ display: 'flex', height: 12, borderRadius: 6, overflow: 'hidden', marginBottom: 8 }}>
                {Object.entries(breakdown).map(([cat, pts]: any) => pts > 0 &&
                  <div key={cat} title={`${cat}: ${pts}`} style={{ width: `${(pts / totalMine) * 100}%`, background: CAT_COLORS[cat] || '#888' }} />)}
              </div>
              <div className="row wrap" style={{ gap: 8, fontSize: 11 }}>
                {Object.entries(breakdown).map(([cat, pts]: any) => pts > 0 &&
                  <span key={cat} className="row" style={{ gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: 2, background: CAT_COLORS[cat] || '#888', display: 'inline-block' }} />{cat} {pts}</span>)}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table>
          <thead><tr><th style={{ width: 60 }}>Rank</th><th>Member</th><th className="hide-mobile">Role</th><th style={{ textAlign: 'right' }}>Points</th></tr></thead>
          <tbody>
            {data.board.map((r: any) => (
              <tr key={r.user_id}>
                <td><span className="mono" style={{ fontWeight: 700, color: r.rank <= 3 ? 'var(--primary)' : 'var(--text-dim)' }}>
                  {r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : `#${r.rank}`}</span></td>
                <td><Link to={`/members/${r.user_id}`} className="row"><Avatar seed={r.avatar_seed} name={r.name} size={30} />
                  <span style={{ fontWeight: 600 }}>{r.name}</span></Link></td>
                <td className="hide-mobile"><RoleBadge role={r.role} /></td>
                <td style={{ textAlign: 'right', fontWeight: 700 }}>{r.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
