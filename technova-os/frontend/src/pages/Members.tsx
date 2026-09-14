import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Spinner, Avatar, RoleBadge } from '../ui'

export default function Members() {
  const [members, setMembers] = useState<any[]>([])
  const [q, setQ] = useState('')
  useEffect(() => { api.get('/members').then(setMembers) }, [])
  if (!members) return <Spinner />
  const shown = members.filter(m => m.name.toLowerCase().includes(q.toLowerCase()))

  return (
    <div>
      <div className="page-head"><h1>Members</h1><p>{members.length} members in TECHNOVA.</p></div>
      <input className="input" style={{ maxWidth: 320, marginBottom: 16 }} placeholder="Search members…" value={q} onChange={e => setQ(e.target.value)} />
      <div className="grid g4">
        {shown.map(m => (
          <Link to={`/members/${m.id}`} key={m.id} className="card" style={{ display: 'block', textAlign: 'center' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}><Avatar seed={m.avatar_seed} name={m.name} size={54} /></div>
            <div style={{ fontWeight: 700 }}>{m.name}</div>
            <div style={{ margin: '6px 0' }}><RoleBadge role={m.role} /></div>
            <span className="badge p">{m.points} pts</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
