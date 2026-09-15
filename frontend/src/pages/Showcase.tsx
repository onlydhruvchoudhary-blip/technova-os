import { useEffect, useState } from 'react'
import { api } from '../api'
import { Spinner, Empty } from '../ui'

export default function Showcase() {
  const [projects, setProjects] = useState<any[]>([])
  useEffect(() => { api.get('/projects/showcase/public').then(setProjects) }, [])
  if (!projects) return <Spinner />

  return (
    <div>
      <div className="page-head"><h1>✨ Project Showcase</h1>
        <p>What TECHNOVA builds. A public representation of the club's work.</p></div>
      {projects.length === 0 ? <Empty icon="✨" title="No showcased projects yet" sub="Complete a project and move it to SHOWCASE." /> : (
        <div className="grid g2">
          {projects.map(p => (
            <div key={p.slug} className="card card-hover">
              <div className="row between" style={{ marginBottom: 8 }}>
                <span className="badge g">{p.state}</span>
                <span className="faint" style={{ fontSize: 12 }}>👥 {p.member_count} builders</span>
              </div>
              <h2 style={{ margin: '0 0 8px' }}>{p.title}</h2>
              <div style={{ fontSize: 13 }}><strong className="faint">Problem</strong><p style={{ marginTop: 2 }}>{p.problem}</p>
                <strong className="faint">Solution</strong><p style={{ marginTop: 2 }}>{p.solution}</p></div>
              <div className="row wrap" style={{ gap: 6, margin: '10px 0' }}>
                {(p.tech || []).map((t: string) => <span key={t} className="badge a">{t}</span>)}</div>
              <div className="row">
                {p.repo_url && <a className="btn sm" href={p.repo_url} target="_blank" rel="noreferrer">↗ Repo</a>}
                {p.demo_url && <a className="btn sm primary" href={p.demo_url} target="_blank" rel="noreferrer">▶ Demo</a>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
