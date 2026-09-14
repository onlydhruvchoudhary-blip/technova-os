import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth, useToast } from '../store'
import { Spinner, RoleBadge } from '../ui'

const ROLES = ['MEMBER', 'COMMITTEE', 'MENTOR', 'ADVISOR', 'CLUB_HEAD', 'SUPER_ADMIN']
const CAT_COLORS: Record<string, string> = {
  learning: '#5b8cff', challenge: '#22d3ee', attendance: '#34d399',
  project: '#7c5cff', social: '#fbbf24', competition: '#f87171',
}

export default function Admin() {
  const { user } = useAuth()
  const { push } = useToast()
  const [tab, setTab] = useState('analytics')
  const [analytics, setAnalytics] = useState<any>(null)
  const [members, setMembers] = useState<any[]>([])
  const [audit, setAudit] = useState<any[]>([])
  const [ann, setAnn] = useState({ title: '', body: '', pinned: false })

  const canRoles = ['CLUB_HEAD', 'SUPER_ADMIN'].includes(user!.role)
  const isSuper = user!.role === 'SUPER_ADMIN'
  const load = () => {
    api.get('/admin/analytics').then(setAnalytics).catch(() => {})
    api.get('/admin/members').then(setMembers).catch(() => {})
    if (canRoles) api.get('/admin/audit').then(setAudit).catch(() => {})
  }
  useEffect(() => { load() }, [])

  const setRole = async (uid: number, role: string) => {
    try { await api.post(`/admin/members/${uid}/role`, { role }); push('Role updated', 'success'); load() }
    catch (e: any) { push(e.message, 'error') }
  }
  const postAnn = async () => {
    try { await api.post('/announcements', ann); push('Announcement posted', 'success'); setAnn({ title: '', body: '', pinned: false }) }
    catch (e: any) { push(e.message, 'error') }
  }

  // ---- admin command console
  const [history, setHistory] = useState<{ cmd: string; out: string; ok: boolean }[]>([
    { cmd: '', out: "TECHNOVA OS Admin Console — type 'help' and press Enter.", ok: true },
  ])
  const [cmdLine, setCmdLine] = useState('')
  const [cmdBusy, setCmdBusy] = useState(false)
  const [recall, setRecall] = useState<string[]>([])
  const [recallIdx, setRecallIdx] = useState(-1)

  const runCmd = async () => {
    const command = cmdLine.trim()
    if (!command) return
    setCmdBusy(true)
    setCmdLine('')
    setRecall(r => [command, ...r]); setRecallIdx(-1)
    try {
      const r = await api.post('/admin/console', { command })
      setHistory(h => [...h, { cmd: command, out: r.output, ok: r.ok }])
    } catch (e: any) {
      setHistory(h => [...h, { cmd: command, out: '! ' + e.message, ok: false }])
    } finally { setCmdBusy(false) }
  }
  const onCmdKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') runCmd()
    else if (e.key === 'ArrowUp') { e.preventDefault(); const ni = Math.min(recallIdx + 1, recall.length - 1); if (ni >= 0) { setRecallIdx(ni); setCmdLine(recall[ni]) } }
    else if (e.key === 'ArrowDown') { e.preventDefault(); const ni = recallIdx - 1; if (ni < 0) { setRecallIdx(-1); setCmdLine('') } else { setRecallIdx(ni); setCmdLine(recall[ni]) } }
  }

  if (!analytics) return <Spinner />
  const club = analytics.club
  const totalPts = analytics.points_by_category.reduce((a: number, c: any) => a + c.points, 0)

  return (
    <div>
      <div className="page-head"><h1>Admin</h1><p>Manage the club. Analytics that help you make decisions.</p></div>
      <div className="row wrap" style={{ marginBottom: 18 }}>
        {['analytics', 'members', 'announce', ...(canRoles ? ['audit'] : []), ...(isSuper ? ['console'] : [])].map(t =>
          <button key={t} className={`btn sm ${tab === t ? 'primary' : 'ghost'}`} onClick={() => setTab(t)}>
            {t === 'console' ? '⌘ Console' : t[0].toUpperCase() + t.slice(1)}</button>)}
      </div>

      {tab === 'analytics' && (
        <div>
          <div className="grid g4" style={{ marginBottom: 16 }}>
            <div className="card stat"><span className="n">{club.total_members}</span><span className="l">Total Members</span></div>
            <div className="card stat"><span className="n">{club.active_members}</span><span className="l">Active (30d)</span></div>
            <div className="card stat"><span className="n">{club.attendance_rate}%</span><span className="l">Attendance Rate</span></div>
            <div className="card stat"><span className="n">{club.projects_completed}</span><span className="l">Projects Done</span></div>
            <div className="card stat"><span className="n">{club.challenges_solved}</span><span className="l">Challenges Solved</span></div>
            <div className="card stat"><span className="n">{club.events_held}</span><span className="l">Events Held</span></div>
            <div className="card stat"><span className="n">{club.competitions}</span><span className="l">Competitions</span></div>
            <div className="card stat"><span className="n">{club.certificates_issued}</span><span className="l">Certificates</span></div>
          </div>
          <div className="grid g2">
            <div className="card"><h3 style={{ marginTop: 0 }}>Popular courses</h3>
              {analytics.popular_courses.length === 0 && <div className="faint">No completions yet.</div>}
              {analytics.popular_courses.map((c: any) => (
                <div key={c.title} className="row between" style={{ padding: '6px 0' }}>
                  <span>{c.title}</span><span className="badge p">{c.completions}</span></div>))}
            </div>
            <div className="card"><h3 style={{ marginTop: 0 }}>Points by category</h3>
              {totalPts === 0 ? <div className="faint">No points yet.</div> : (
                <>
                  <div style={{ display: 'flex', height: 14, borderRadius: 7, overflow: 'hidden', marginBottom: 10 }}>
                    {analytics.points_by_category.map((c: any) => c.points > 0 &&
                      <div key={c.category} title={`${c.category}: ${c.points}`} style={{ width: `${(c.points / totalPts) * 100}%`, background: CAT_COLORS[c.category] || '#888' }} />)}
                  </div>
                  {analytics.points_by_category.map((c: any) => (
                    <div key={c.category} className="row between" style={{ padding: '4px 0', fontSize: 13 }}>
                      <span className="row" style={{ gap: 6 }}><span style={{ width: 10, height: 10, borderRadius: 3, background: CAT_COLORS[c.category], display: 'inline-block' }} />{c.category}</span>
                      <span>{c.points}</span></div>))}
                </>
              )}
            </div>
          </div>
          {analytics.projects_by_tech.length > 0 && (
            <div className="card" style={{ marginTop: 16 }}><h3 style={{ marginTop: 0 }}>Projects by technology</h3>
              <div className="row wrap" style={{ gap: 8 }}>
                {analytics.projects_by_tech.map((t: any) => <span key={t.tech} className="badge a">{t.tech} · {t.count}</span>)}</div>
            </div>
          )}
        </div>
      )}

      {tab === 'members' && (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table>
            <thead><tr><th>Name</th><th className="hide-mobile">Email</th><th>Role</th><th>Points</th>{canRoles && <th>Change role</th>}</tr></thead>
            <tbody>
              {members.map(m => (
                <tr key={m.id}>
                  <td style={{ fontWeight: 600 }}>{m.name}{!m.is_active && <span className="badge r" style={{ marginLeft: 6 }}>inactive</span>}</td>
                  <td className="hide-mobile faint">{m.email}</td>
                  <td><RoleBadge role={m.role} /></td>
                  <td>{m.points}</td>
                  {canRoles && <td>
                    <select className="input" style={{ padding: '5px 8px', width: 'auto' }} value={m.role}
                      onChange={e => setRole(m.id, e.target.value)} disabled={m.id === user!.id}>
                      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'announce' && (
        <div className="card" style={{ maxWidth: 560 }}>
          <h3 style={{ marginTop: 0 }}>Post announcement</h3>
          <label className="field"><span>Title</span><input className="input" value={ann.title} onChange={e => setAnn({ ...ann, title: e.target.value })} /></label>
          <label className="field"><span>Body</span><textarea className="input" rows={3} value={ann.body} onChange={e => setAnn({ ...ann, body: e.target.value })} /></label>
          <label className="row" style={{ gap: 8, marginBottom: 14 }}><input type="checkbox" checked={ann.pinned} onChange={e => setAnn({ ...ann, pinned: e.target.checked })} /> Pin to top</label>
          <button className="btn primary" onClick={postAnn} disabled={!ann.title}>Post & notify all members</button>
        </div>
      )}

      {tab === 'audit' && (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table>
            <thead><tr><th>Actor</th><th>Action</th><th>Target</th><th className="hide-mobile">Detail</th><th className="hide-mobile">When</th></tr></thead>
            <tbody>
              {audit.map(a => (
                <tr key={a.id}><td>{a.actor}</td><td><span className="badge">{a.action}</span></td>
                  <td className="mono faint" style={{ fontSize: 12 }}>{a.target}</td>
                  <td className="hide-mobile faint">{a.detail}</td>
                  <td className="hide-mobile faint" style={{ fontSize: 12 }}>{new Date(a.created_at).toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'console' && isSuper && (
        <div>
          <p className="faint" style={{ fontSize: 13, marginTop: 0 }}>
            God-mode command console (Super Admin only). Every command is written to the audit log.
            Try <code className="mono">help</code>, <code className="mono">whoami</code>,
            or <code className="mono">grant points me 5000</code>. ↑/↓ recalls history.
          </p>
          <div className="code-editor" style={{ minHeight: 340, overflow: 'auto', cursor: 'text' }}
            onClick={() => document.getElementById('cmdinput')?.focus()}>
            {history.map((h, i) => (
              <div key={i}>
                {h.cmd && <div><span style={{ color: 'var(--accent)' }}>technova@admin</span>
                  <span style={{ color: 'var(--text-faint)' }}>:~$</span> {h.cmd}</div>}
                <div style={{ color: h.ok ? '#8fe3b0' : '#ff9b9b', whiteSpace: 'pre-wrap', marginBottom: 6 }}>{h.out}</div>
              </div>
            ))}
            <div className="row" style={{ gap: 6 }}>
              <span style={{ color: 'var(--accent)' }}>technova@admin</span>
              <span style={{ color: 'var(--text-faint)' }}>:~$</span>
              <input id="cmdinput" autoFocus value={cmdLine} disabled={cmdBusy}
                onChange={e => setCmdLine(e.target.value)} onKeyDown={onCmdKey}
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none',
                  color: '#d6e0f5', fontFamily: 'var(--mono)', fontSize: 13 }} />
              {cmdBusy && <span className="faint">running…</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
