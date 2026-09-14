import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth, useToast } from '../store'
import { Spinner, Empty, Modal } from '../ui'

export default function Competitions() {
  const { user } = useAuth()
  const { push } = useToast()
  const [comps, setComps] = useState<any[]>([])
  const [show, setShow] = useState(false)
  const [form, setForm] = useState({ title: '', kind: 'Project', description: '' })
  const canManage = ['CLUB_HEAD', 'SUPER_ADMIN'].includes(user!.role)

  const load = () => api.get('/competitions').then(setComps)
  useEffect(() => { load() }, [])
  if (!comps) return <Spinner />

  const create = async () => {
    try { await api.post('/competitions', { ...form, rubric: [] }); push('Competition created', 'success'); setShow(false); load() }
    catch (e: any) { push(e.message, 'error') }
  }

  return (
    <div>
      <div className="page-head row between">
        <div><h1>Competitions</h1><p>Hackathons, coding contests, project competitions — judged with real rubrics.</p></div>
        {canManage && <button className="btn primary" onClick={() => setShow(true)}>+ New competition</button>}
      </div>
      {comps.length === 0 ? <Empty icon="🥇" title="No competitions yet" /> : (
        <div className="grid g2">
          {comps.map(c => (
            <Link to={`/competitions/${c.id}`} key={c.id} className="card" style={{ display: 'block' }}>
              <div className="row between" style={{ marginBottom: 8 }}>
                <span className="badge a">{c.kind}</span>
                <span className={`badge ${c.status === 'open' ? 'g' : c.status === 'judging' ? 'w' : ''}`}>{c.status}</span>
              </div>
              <h3 style={{ margin: '0 0 6px' }}>{c.title}</h3>
              <p className="faint" style={{ fontSize: 13 }}>{c.description}</p>
              <div className="row between" style={{ marginTop: 8 }}>
                <span className="faint" style={{ fontSize: 12 }}>🧑‍💻 {c.entry_count} entries</span>
                {c.registered && <span className="badge p">Registered</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
      {show && (
        <Modal title="New competition" onClose={() => setShow(false)}>
          <label className="field"><span>Title</span><input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
          <label className="field"><span>Type</span>
            <select className="input" value={form.kind} onChange={e => setForm({ ...form, kind: e.target.value })}>
              {['Project', 'Coding', 'Hackathon', 'Quiz', 'Team'].map(k => <option key={k}>{k}</option>)}</select></label>
          <label className="field"><span>Description</span><textarea className="input" rows={3} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
          <p className="faint" style={{ fontSize: 12 }}>A default rubric (Innovation, Technical Quality, Usefulness, Design, Presentation, Documentation) is applied.</p>
          <div className="row" style={{ justifyContent: 'flex-end' }}><button className="btn primary" onClick={create} disabled={!form.title}>Create</button></div>
        </Modal>
      )}
    </div>
  )
}
