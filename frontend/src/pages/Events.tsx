import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth, useToast } from '../store'
import { Spinner, Empty, Modal } from '../ui'

export default function Events() {
  const { user } = useAuth()
  const { push } = useToast()
  const [events, setEvents] = useState<any[]>([])
  const [qrModal, setQrModal] = useState<any>(null)
  const [qr, setQr] = useState<any>(null)
  const [scanModal, setScanModal] = useState<any>(null)
  const [token, setToken] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ title: '', kind: 'Workshop', location: '', starts_at: '', capacity: 40, description: '' })

  const isOrganiser = ['COMMITTEE', 'MENTOR', 'ADVISOR', 'CLUB_HEAD', 'SUPER_ADMIN'].includes(user!.role)
  const load = () => api.get('/events').then(setEvents)
  useEffect(() => { load() }, [])
  if (!events) return <Spinner />

  const act = async (fn: () => Promise<any>, msg: string) => {
    try { await fn(); push(msg, 'success'); load() } catch (e: any) { push(e.message, 'error') }
  }

  // organiser: open attendance and show rotating QR token
  const openQr = async (ev: any) => {
    await api.post(`/events/${ev.id}/attendance/open?open=true`)
    setQrModal(ev)
    const refresh = async () => { try { setQr(await api.get(`/events/${ev.id}/qr`)) } catch {} }
    refresh()
    const t = setInterval(refresh, 30000)
    ;(window as any)._qrTimer = t
  }
  const closeQr = () => { clearInterval((window as any)._qrTimer); setQrModal(null); setQr(null); load() }

  // member: enter token to mark attendance (simulates scanning the QR)
  const scan = async () => {
    try {
      const r = await api.post(`/events/${scanModal.id}/attendance`, { token })
      push(`Attendance recorded for ${r.event}! +20 pts`, 'success')
      setScanModal(null); setToken(''); load()
    } catch (e: any) { push(e.message, 'error') }
  }

  const create = () => act(async () => {
    await api.post('/events', { ...form, capacity: Number(form.capacity), starts_at: new Date(form.starts_at).toISOString(), is_public: true })
    setShowCreate(false)
  }, 'Event created')

  return (
    <div>
      <div className="page-head row between">
        <div><h1>Events</h1><p>Workshops, meetings, hackathons. Register, attend via QR, earn points.</p></div>
        {isOrganiser && <button className="btn primary" onClick={() => setShowCreate(true)}>+ New event</button>}
      </div>

      {events.length === 0 ? <Empty icon="📅" title="No events scheduled" /> : (
        <div className="grid g2">
          {events.map(e => {
            const upcoming = new Date(e.starts_at) >= new Date()
            return (
              <div className="card" key={e.id}>
                <div className="row between" style={{ marginBottom: 8 }}>
                  <span className="badge a">{e.kind}</span>
                  {!e.is_public && <span className="badge">Private</span>}
                </div>
                <h3 style={{ margin: '0 0 4px' }}>{e.title}</h3>
                <p className="faint" style={{ fontSize: 13 }}>{e.description}</p>
                <div className="faint" style={{ fontSize: 13, margin: '8px 0' }}>
                  📅 {new Date(e.starts_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  {e.location && ` · 📍 ${e.location}`}
                </div>
                <div className="row between">
                  <span className="faint" style={{ fontSize: 12 }}>👥 {e.registrations}/{e.capacity} · ✅ {e.attendance} present</span>
                  <div className="row">
                    {e.attended ? <span className="badge g">✓ Attended</span>
                      : e.registered ? <span className="badge p">Registered</span>
                      : upcoming ? <button className="btn sm" onClick={() => act(() => api.post(`/events/${e.id}/register`), 'Registered!')}>Register</button> : null}
                    {!e.attended && (e.registered || e.attendance_open) &&
                      <button className="btn sm primary" onClick={() => setScanModal(e)}>Scan QR</button>}
                    {isOrganiser && <button className="btn sm ghost" onClick={() => openQr(e)}>📱 Show QR</button>}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {qrModal && (
        <Modal title={`Attendance · ${qrModal.title}`} onClose={closeQr}>
          <p className="muted">Members enter this code to mark attendance. It rotates every 90 seconds and expires — screenshots won't work later.</p>
          <div className="card" style={{ background: 'var(--bg-2)', textAlign: 'center', padding: 30 }}>
            <div style={{ fontSize: 60 }}>📱</div>
            <div className="mono" style={{ fontSize: 22, fontWeight: 700, letterSpacing: 1, marginTop: 10, wordBreak: 'break-all' }}>{qr?.token || '…'}</div>
            <div className="faint" style={{ marginTop: 8, fontSize: 12 }}>Expires in ~{qr?.expires_in}s · auto-refreshing</div>
          </div>
        </Modal>
      )}

      {scanModal && (
        <Modal title={`Mark attendance · ${scanModal.title}`} onClose={() => setScanModal(null)}>
          <p className="muted">Enter the code shown on the organiser's screen.</p>
          <input className="input mono" placeholder="e.g. 1.12345.abcd…" value={token} onChange={e => setToken(e.target.value)} />
          <div className="row" style={{ marginTop: 14, justifyContent: 'flex-end' }}>
            <button className="btn primary" onClick={scan} disabled={!token}>Submit</button>
          </div>
        </Modal>
      )}

      {showCreate && (
        <Modal title="New event" onClose={() => setShowCreate(false)}>
          <label className="field"><span>Title</span><input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
          <div className="grid g2">
            <label className="field"><span>Type</span>
              <select className="input" value={form.kind} onChange={e => setForm({ ...form, kind: e.target.value })}>
                {['Workshop', 'Meeting', 'Hackathon', 'Competition', 'Presentation', 'Training session'].map(k => <option key={k}>{k}</option>)}
              </select></label>
            <label className="field"><span>Capacity</span><input className="input" type="number" value={form.capacity} onChange={e => setForm({ ...form, capacity: Number(e.target.value) })} /></label>
          </div>
          <label className="field"><span>Date & time</span><input className="input" type="datetime-local" value={form.starts_at} onChange={e => setForm({ ...form, starts_at: e.target.value })} /></label>
          <label className="field"><span>Location</span><input className="input" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} /></label>
          <label className="field"><span>Description</span><textarea className="input" rows={2} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
          <div className="row" style={{ justifyContent: 'flex-end' }}><button className="btn primary" onClick={create} disabled={!form.title || !form.starts_at}>Create</button></div>
        </Modal>
      )}
    </div>
  )
}
