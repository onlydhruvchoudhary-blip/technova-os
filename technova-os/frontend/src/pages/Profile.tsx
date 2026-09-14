import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth, useToast } from '../store'
import { Spinner, Avatar, RoleBadge, Bar, Empty } from '../ui'

const TIER_COLOR: Record<string, string> = { Beginner: 'p', Intermediate: 'p', Advanced: 'g', Mentor: 'w' }

// Rarity → { border/glow color, label color }. Common is muted; Legendary shines.
const RARITY: Record<string, { c: string; glow: string }> = {
  Common: { c: '#8b93a7', glow: 'rgba(139,147,167,.25)' },
  Uncommon: { c: '#3fb950', glow: 'rgba(63,185,80,.35)' },
  Rare: { c: '#4c8dff', glow: 'rgba(76,141,255,.40)' },
  Epic: { c: '#a371f7', glow: 'rgba(163,113,247,.45)' },
  Legendary: { c: '#f0a500', glow: 'rgba(240,165,0,.55)' },
}

export default function Profile() {
  const { id } = useParams()
  const { user } = useAuth()
  const { push } = useToast()
  const [data, setData] = useState<any>(null)
  const [certs, setCerts] = useState<any[]>([])
  const [gallery, setGallery] = useState<any>(null)
  const [showLocked, setShowLocked] = useState(false)
  const canRevoke = ['CLUB_HEAD', 'SUPER_ADMIN'].includes(user!.role)

  const loadCerts = () => { if (!id) api.get('/certificates/me').then(setCerts) }
  useEffect(() => {
    const path = id ? `/users/${id}/profile` : '/me/profile'
    api.get(path).then(setData)
    loadCerts()
    if (!id) api.get('/achievements').then(setGallery).catch(() => {})
  }, [id])

  const revoke = async (uid: string) => {
    try { await api.post(`/certificates/${uid}/revoke`); push('Certificate revoked', 'success'); loadCerts() }
    catch (e: any) { push(e.message, 'error') }
  }
  if (!data) return <Spinner />
  const u = data.user
  const shownCerts = id ? data.certificates : certs

  return (
    <div>
      <div className="card" style={{ marginBottom: 18, background: 'radial-gradient(600px 200px at 90% 0%, rgba(124,92,255,.15), transparent), var(--surface)' }}>
        <div className="row" style={{ gap: 18, flexWrap: 'wrap' }}>
          <Avatar seed={u.avatar_seed} name={u.name} size={72} />
          <div style={{ flex: 1, minWidth: 200 }}>
            <div className="row" style={{ gap: 10 }}><h1 style={{ margin: 0 }}>{u.name}</h1><RoleBadge role={u.role} /></div>
            <p className="muted" style={{ margin: '4px 0' }}>{u.bio || 'TECHNOVA member'}</p>
          </div>
          <div className="row" style={{ gap: 24 }}>
            <div className="stat" style={{ alignItems: 'center' }}><span className="n">{data.points}</span><span className="l">Points</span></div>
            <div className="stat" style={{ alignItems: 'center' }}><span className="n">#{data.rank ?? '—'}</span><span className="l">Rank</span></div>
            <div className="stat" style={{ alignItems: 'center' }}><span className="n">{data.stats.challenges_solved}</span><span className="l">Solved</span></div>
          </div>
        </div>
      </div>

      <div className="grid g2">
        <div className="card"><h3 style={{ marginTop: 0 }}>🌳 Skills</h3>
          {data.skills.length === 0 ? <Empty icon="🌱" title="No skills yet" sub="Complete lessons to grow skills." /> :
            data.skills.map((s: any) => (
              <div key={s.key} style={{ marginBottom: 12 }}>
                <div className="row between" style={{ marginBottom: 5 }}>
                  <span className="row" style={{ gap: 6 }}><span>{s.icon}</span><strong style={{ fontSize: 14 }}>{s.name}</strong>
                    <span className={`badge ${TIER_COLOR[s.tier] || ''}`}>{s.tier}</span></span>
                  <span className="faint" style={{ fontSize: 12 }}>{s.xp} XP</span>
                </div>
                <Bar value={s.tier_index} max={4} />
              </div>
            ))}
        </div>

        <div className="grid">
          <div className="card">
            <div className="row between" style={{ marginTop: 0, alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>🏆 Achievements</h3>
              {!id && gallery && (
                <span className="faint" style={{ fontSize: 12 }}>
                  {gallery.unlocked}/{gallery.total} unlocked · {gallery.points_earned} pts
                </span>
              )}
            </div>

            {/* Rarity summary + progress bar (own profile only) */}
            {!id && gallery && (
              <>
                <div style={{ margin: '10px 0 4px', height: 8, borderRadius: 6, background: 'var(--bg-2)', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.round((gallery.unlocked / gallery.total) * 100)}%`, height: '100%',
                    background: 'linear-gradient(90deg,#4c8dff,#a371f7,#f0a500)', transition: 'width .4s',
                  }} />
                </div>
                <div className="row wrap" style={{ gap: 6, margin: '8px 0 14px' }}>
                  {Object.keys(RARITY).map(r => {
                    const n = gallery.items.filter((i: any) => i.rarity === r && i.earned).length
                    const tot = gallery.items.filter((i: any) => i.rarity === r).length
                    return (
                      <span key={r} className="badge" style={{
                        background: RARITY[r].glow, color: RARITY[r].c,
                        border: `1px solid ${RARITY[r].c}`, fontSize: 11,
                      }}>{r} {n}/{tot}</span>
                    )
                  })}
                </div>
              </>
            )}

            {/* Earned cards (with rarity styling). On other profiles use data.achievements. */}
            {(() => {
              const source = !id && gallery
                ? gallery.items.filter((i: any) => showLocked || i.earned)
                : data.achievements.map((a: any) => ({ ...a, earned: true }))
              if (source.length === 0) return <div className="faint">No achievements yet.</div>
              return (
                <div className="row wrap" style={{ gap: 10 }}>
                  {source.map((a: any) => {
                    const r = RARITY[a.rarity] || RARITY.Common
                    return (
                      <div key={a.key} className="card" title={`${a.description} · ${a.rarity} · +${a.points} pts`}
                        style={{
                          background: a.earned ? 'var(--bg-2)' : 'transparent',
                          padding: '10px 12px', minWidth: 130, flex: '1 1 40%',
                          border: `1px solid ${a.earned ? r.c : 'var(--border)'}`,
                          boxShadow: a.earned ? `0 0 12px ${r.glow}` : 'none',
                          opacity: a.earned ? 1 : 0.45, position: 'relative',
                        }}>
                        <div className="row between" style={{ alignItems: 'flex-start' }}>
                          <div style={{ fontSize: 24, filter: a.earned ? 'none' : 'grayscale(1)' }}>{a.earned ? a.icon : '🔒'}</div>
                          <span style={{ fontSize: 9, fontWeight: 700, color: r.c, textTransform: 'uppercase', letterSpacing: .5 }}>{a.rarity}</span>
                        </div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginTop: 4 }}>{a.name}</div>
                        <div className="faint" style={{ fontSize: 11 }}>{a.description}</div>
                        <div className="faint" style={{ fontSize: 10, marginTop: 4, color: r.c }}>+{a.points} pts</div>
                      </div>
                    )
                  })}
                </div>
              )
            })()}

            {!id && gallery && gallery.unlocked < gallery.total && (
              <button className="btn ghost" style={{ marginTop: 12, fontSize: 12 }}
                onClick={() => setShowLocked(v => !v)}>
                {showLocked ? 'Hide locked' : `Show ${gallery.total - gallery.unlocked} locked`}
              </button>
            )}
          </div>

          <div className="card"><h3 style={{ marginTop: 0 }}>🛠️ Projects</h3>
            {data.projects.length === 0 ? <div className="faint">No projects yet.</div> :
              data.projects.map((p: any) => (
                <Link to={`/projects/${p.slug}`} key={p.id} className="row between" style={{ padding: '7px 0' }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{p.title}</span>
                  <span className="badge">{p.role}</span>
                </Link>
              ))}
          </div>
        </div>
      </div>

      {shownCerts && shownCerts.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 style={{ marginTop: 0 }}>📜 Certificates</h3>
          <div className="grid g3">
            {shownCerts.map((c: any) => (
              <div key={c.cert_uid} className="card" style={{ background: 'var(--bg-2)' }}>
                <div className="row between"><span className="badge a">{c.kind}</span></div>
                <div style={{ fontWeight: 700, margin: '8px 0 4px' }}>{c.title}</div>
                <div className="faint" style={{ fontSize: 12 }}>{new Date(c.issued_at).toLocaleDateString()}</div>
                <a className="mono" style={{ fontSize: 11, color: 'var(--primary)' }} href={`/verify/${c.cert_uid}`} target="_blank" rel="noreferrer">Verify {c.cert_uid} ↗</a>
                {!id && canRevoke && <div><button className="btn danger sm" style={{ marginTop: 8 }} onClick={() => revoke(c.cert_uid)}>Revoke</button></div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
