import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useToast } from '../store'
import { Spinner, StateBadge, Empty, Modal } from '../ui'
import type { ProjectCard, GitHubStats } from '../types'

const STATES: Array<ProjectCard['state'] | 'ALL'> = [
  'ALL', 'PROPOSED', 'TEAM_FORMING', 'PLANNING', 'DEVELOPMENT', 'TESTING', 'DEMO', 'COMPLETED', 'SHOWCASE',
]

export default function Projects() {
  const { push } = useToast()
  const [projects, setProjects] = useState<ProjectCard[] | null>(null)
  const [mine, setMine] = useState(false)
  const [show, setShow] = useState(false)
  const [ghFor, setGhFor] = useState<ProjectCard | null>(null)
  const [form, setForm] = useState({ title: '', problem: '', solution: '', required_skills: '', tech: '', team_size: 4 })

  // filters
  const [state, setState] = useState<(typeof STATES)[number]>('ALL')
  const [tech, setTech] = useState('All')
  const [q, setQ] = useState('')

  const load = () => api.get<ProjectCard[]>(`/projects${mine ? '?mine=true' : ''}`).then(setProjects).catch(() => setProjects([]))
  useEffect(() => { load() }, [mine])

  const allTech = useMemo(() => {
    const s = new Set<string>()
    ;(projects || []).forEach(p => (p.tech || []).forEach(t => s.add(t)))
    return ['All', ...Array.from(s).sort()]
  }, [projects])

  if (!projects) return <Spinner />

  const shown = projects.filter(p =>
    (state === 'ALL' || p.state === state) &&
    (tech === 'All' || (p.tech || []).includes(tech)) &&
    (q === '' || p.title.toLowerCase().includes(q.toLowerCase()) || p.problem.toLowerCase().includes(q.toLowerCase())),
  )

  const create = async () => {
    try {
      await api.post('/projects', {
        ...form,
        required_skills: form.required_skills.split(',').map(s => s.trim()).filter(Boolean),
        tech: form.tech.split(',').map(s => s.trim()).filter(Boolean),
        team_size: Number(form.team_size),
      })
      push('Project created! It starts in PROPOSED.', 'success')
      setShow(false); load()
    } catch (e) { push(e instanceof ApiError ? e.message : 'Failed', 'error') }
  }

  return (
    <div>
      <div className="page-head row between wrap" style={{ gap: 12 }}>
        <div><h1>Project Incubator</h1><p>Turn ideas into real projects. Form teams, plan, build, ship, showcase.</p></div>
        <button className="btn primary" onClick={() => setShow(true)}>+ New project</button>
      </div>

      {/* filter bar */}
      <div className="glass-card" style={{ padding: 12, marginBottom: 16 }}>
        <div className="row wrap between" style={{ gap: 10 }}>
          <div className="row wrap" style={{ gap: 6 }}>
            <button className={`btn sm ${!mine ? 'primary' : 'ghost'}`} onClick={() => setMine(false)}>All</button>
            <button className={`btn sm ${mine ? 'primary' : 'ghost'}`} onClick={() => setMine(true)}>Mine</button>
          </div>
          <input className="input" style={{ maxWidth: 220 }} placeholder="Search projects…" value={q} onChange={e => setQ(e.target.value)} />
        </div>
        <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
          {STATES.map(s => (
            <button key={s} className={`btn sm ${state === s ? 'primary' : 'ghost'}`} onClick={() => setState(s)}>
              {s === 'ALL' ? 'Any status' : s.replace('_', ' ').toLowerCase()}
            </button>
          ))}
        </div>
        {allTech.length > 1 && (
          <div className="row wrap" style={{ gap: 6, marginTop: 8 }}>
            {allTech.map(t => (
              <button key={t} className={`btn sm ${tech === t ? 'primary' : 'ghost'}`} onClick={() => setTech(t)}>{t}</button>
            ))}
          </div>
        )}
      </div>

      <div className="faint" style={{ fontSize: 13, marginBottom: 10 }}>{shown.length} project{shown.length === 1 ? '' : 's'}</div>

      {shown.length === 0 ? <Empty icon="🛠️" title="No matching projects" sub="Try clearing a filter." /> : (
        <div className="grid g3">
          {shown.map(p => (
            <div key={p.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="row between" style={{ marginBottom: 8 }}>
                <StateBadge state={p.state} />
                <span className="faint" style={{ fontSize: 12 }}>👥 {p.member_count}/{p.team_size}</span>
              </div>
              <Link to={`/projects/${p.slug}`} style={{ display: 'block' }}>
                <h3 style={{ margin: '0 0 6px' }}>{p.title}</h3>
                <p className="faint" style={{ fontSize: 13, minHeight: 34 }}>{p.problem}</p>
              </Link>
              <div className="row wrap" style={{ gap: 5, marginTop: 8 }}>
                {(p.tech || []).slice(0, 4).map(t => <span key={t} className="badge">{t}</span>)}
                {p.is_member && <span className="badge g">Member</span>}
              </div>
              <div className="row" style={{ gap: 6, marginTop: 'auto', paddingTop: 10 }}>
                <Link to={`/projects/${p.slug}`} className="btn sm ghost">Open</Link>
                {p.repo_url && <button className="btn sm ghost" onClick={() => setGhFor(p)}>⭐ GitHub</button>}
                {p.demo_url && <a className="btn sm ghost" href={p.demo_url} target="_blank" rel="noreferrer">Demo ↗</a>}
              </div>
            </div>
          ))}
        </div>
      )}

      {ghFor && <GitHubModal project={ghFor} onClose={() => setGhFor(null)} />}

      {show && (
        <Modal title="New project" onClose={() => setShow(false)} wide>
          <label className="field"><span>Title</span>
            <input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
          <label className="field"><span>Problem it solves</span>
            <textarea className="input" rows={2} value={form.problem} onChange={e => setForm({ ...form, problem: e.target.value })} /></label>
          <label className="field"><span>Proposed solution</span>
            <textarea className="input" rows={2} value={form.solution} onChange={e => setForm({ ...form, solution: e.target.value })} /></label>
          <div className="grid g2">
            <label className="field"><span>Required skills (comma keys, e.g. python, apis)</span>
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

function GitHubModal({ project, onClose }: { project: ProjectCard; onClose: () => void }) {
  const [data, setData] = useState<GitHubStats | null>(null)
  useEffect(() => {
    api.get<GitHubStats>(`/projects/${project.slug}/github`).then(setData).catch(() => setData({ linked: true, error: 'Could not load.' }))
  }, [project.slug])

  return (
    <Modal title={`GitHub · ${project.title}`} onClose={onClose}>
      {!data ? <Spinner /> : !data.linked ? (
        <Empty icon="🔗" title="No repository linked" sub={data.reason} />
      ) : data.error ? (
        <Empty icon="⚠️" title="GitHub unavailable" sub={data.error} />
      ) : (
        <div>
          <div className="row between wrap" style={{ gap: 8 }}>
            <a href={data.url} target="_blank" rel="noreferrer" className="mono" style={{ color: 'var(--accent)' }}>{data.repo} ↗</a>
            {data.language && <span className="badge a">{data.language}</span>}
          </div>
          {data.description && <p className="faint" style={{ fontSize: 13, marginTop: 6 }}>{data.description}</p>}
          <div className="grid g3" style={{ gap: 10, margin: '14px 0' }}>
            <Stat label="Stars" value={data.stars ?? 0} icon="⭐" />
            <Stat label="Forks" value={data.forks ?? 0} icon="🍴" />
            <Stat label="Open issues" value={data.open_issues ?? 0} icon="🐛" />
          </div>
          <div className="faint" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Recent commits</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(data.commits || []).map(c => (
              <a key={c.sha} href={c.url} target="_blank" rel="noreferrer" className="card" style={{ padding: '8px 10px' }}>
                <div className="row between" style={{ gap: 8 }}>
                  <span style={{ fontSize: 13 }}>{c.message}</span>
                  <span className="mono faint" style={{ fontSize: 11 }}>{c.sha}</span>
                </div>
                <div className="faint" style={{ fontSize: 11 }}>{c.author} · {c.date ? new Date(c.date).toLocaleDateString() : ''}</div>
              </a>
            ))}
            {(data.commits || []).length === 0 && <span className="faint" style={{ fontSize: 13 }}>No commits found.</span>}
          </div>
        </div>
      )}
    </Modal>
  )
}

function Stat({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="glass-card" style={{ padding: '12px', textAlign: 'center' }}>
      <div style={{ fontSize: 20 }}>{icon}</div>
      <div style={{ fontSize: 22, fontWeight: 800 }}>{value.toLocaleString()}</div>
      <div className="faint" style={{ fontSize: 11 }}>{label}</div>
    </div>
  )
}
