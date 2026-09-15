import { useEffect, useState } from 'react'
import { api } from '../api'
import { Spinner, Empty } from '../ui'

export default function Resources() {
  const [resources, setResources] = useState<any[]>([])
  const [q, setQ] = useState('')
  const [tech, setTech] = useState('All')
  useEffect(() => { api.get('/resources').then(setResources) }, [])
  if (!resources) return <Spinner />

  const techs = ['All', ...Array.from(new Set(resources.map(r => r.technology)))]
  const shown = resources.filter(r =>
    (tech === 'All' || r.technology === tech) &&
    (r.title.toLowerCase().includes(q.toLowerCase()) || r.description.toLowerCase().includes(q.toLowerCase())))

  return (
    <div>
      <div className="page-head"><h1>Resource Library</h1><p>Curated tutorials, docs, cheat sheets and references.</p></div>
      <div className="row wrap" style={{ marginBottom: 16 }}>
        <input className="input" style={{ maxWidth: 280 }} placeholder="Search resources…" value={q} onChange={e => setQ(e.target.value)} />
        {techs.map(t => <button key={t} className={`btn sm ${tech === t ? 'primary' : 'ghost'}`} onClick={() => setTech(t)}>{t}</button>)}
      </div>
      {shown.length === 0 ? <Empty icon="📖" title="No resources found" /> : (
        <div className="grid g3">
          {shown.map(r => (
            <a key={r.id} href={r.url} target="_blank" rel="noreferrer" className="card" style={{ display: 'block' }}>
              <div className="row between" style={{ marginBottom: 8 }}><span className="badge a">{r.kind}</span><span className="badge">{r.difficulty}</span></div>
              <h3 style={{ margin: '0 0 6px' }}>{r.title}</h3>
              <p className="faint" style={{ fontSize: 13 }}>{r.description}</p>
              <div className="row" style={{ marginTop: 8, gap: 6 }}><span className="badge p">{r.technology}</span><span className="faint" style={{ fontSize: 12 }}>{r.topic}</span></div>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
