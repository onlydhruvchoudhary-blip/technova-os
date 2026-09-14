import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useToast } from '../store'
import { Spinner, StateBadge, Empty, Modal } from '../ui'

export default function Projects() {
  const { push } = useToast()
  const [projects, setProjects] = useState<any[]>([])
  const [mine, setMine] = useState(false)
  const [show, setShow] = useState(false)
  const [form, setForm] = useState({ title: '', problem: '', solution: '', required_skills: '', tech: '', team_size: 4 })

  const load = () => api.get(`/projects${mine ? '?mine=true' : ''}`).then(setProjects)
  useEffect(() => { load() }, [mine])
  if (!projects) return <Spinner />

  const create = async () => {
    try {
      const body = {
        ...form,
        required_skills: form.required_skills.split(',').map(s => s.trim()).filter(Boolean),
        tech: form.tech.split(',').map(s => s.trim()).filter(Boolean),
        team_size: Number(form.team_size),
      }
      const r = await api.post('/projects', body)
      push('Project created! It starts in PROPOSED.', 'success')
      setShow(false); load()
    } catch (e: any) { push(e.message, 'error') }
  }

  return (
    <div>
      <div className="page-head row between">
        <div><h1>Project Incubator</h1><p>Turn ideas into real projects. Form teams, plan, build, ship, showcase.</p></div>
        <button className="btn primary" onClick={() => setShow(true)}>+ New project</button>
      </div>
      <div className="row" style={{ marginBottom: 16 }}>
        <button className={`btn sm ${!mine ? 'primary' : 'ghost'}`} onClick={() => setMine(false)}>All projects</button>
        <button className={`btn sm ${mine ? 'primary' : 'ghost'}`} onClick={() => setMine(true)}>My projects</button>
      </div>

      {projects.length === 0 ? <Empty icon="🛠️" title="No projects yet" sub="Start the first one!" /> : (
        <div className="grid g3">
          {projects.map(p => (
            <Link to={`/projects/${p.slug}`} key={p.id} className="card" style={{ display: 'block' }}>
              <div className="row between" style={{ marginBottom: 8 }}>
                <StateBadge state={p.state} />
                <span className="faint" style={{ fontSize: 12 }}>👥 {p.member_count}/{p.team_size}</span>
              </div>
              <h3 style={{ margin: '0 0 6px' }}>{p.title}</h3>
              <p className="faint" style={{ fontSize: 13, minHeight: 34 }}>{p.problem}</p>
              <div className="row wrap" style={{ gap: 5, marginTop: 8 }}>
                {(p.tech || []).slice(0, 4).map((t: string) => <span key={t} className="badge">{t}</span>)}
                {p.is_member && <span className="badge g">Member</span>}
              </div>
            </Link>
          ))}
        </div>
      )}

      {show && (
        <Modal title="New project" onClose={() => setShow(false)} wide>
          <label className="field"><span>Title</span>
            <input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
          <label className="field"><span>Problem it solves</span>
            <textarea className="input" rows={2} value={form.problem} onChange={e => setForm({ ...form, problem: e.target.value })} /></label>
          <label className="field"><span>Proposed solution</span>
            <textarea className="input" rows={2} value={form.solution} onChange={e => setForm({ ...form, solution: e.target.value })} /></label>
          <div className="grid g2">
            <label className="field"><span>Required skills (comma separated keys, e.g. python, apis)</span>
              <input className="input" value={form.required_skills} onChange={e => setForm({ ...form, required_skills: e.target.value })} /></label>
            <label className="field"><span>Tech stack (comma separated)</span>
              <input className="input" value={form.tech} onChange={e => setForm({ ...form, tech: e.target.value })} /></label>
          </div>
          <label className="field"><span>Team size</span>
            <input className="input" type="number" min={1} max={10} value={form.team_size} onChange={e => setForm({ ...form, team_size: Number(e.target.value) })} /></label>
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn primary" onClick={create} disabled={!form.title}>Create project</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
