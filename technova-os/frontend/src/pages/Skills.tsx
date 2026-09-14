import { useEffect, useState } from 'react'
import { api } from '../api'
import { Spinner } from '../ui'

const TIERS = ['None', 'Beginner', 'Intermediate', 'Advanced', 'Mentor']

export default function Skills() {
  const [profile, setProfile] = useState<any>(null)
  const [all, setAll] = useState<any[]>([])
  useEffect(() => { Promise.all([api.get('/me/profile'), api.get('/academy/skills')]).then(([p, s]) => { setProfile(p); setAll(s) }) }, [])
  if (!profile || !all.length) return <Spinner />

  const mine = new Map(profile.skills.map((s: any) => [s.key, s]))
  const byCat: Record<string, any[]> = {}
  all.forEach(s => { (byCat[s.category] ||= []).push(s) })

  return (
    <div>
      <div className="page-head"><h1>Skill Tree</h1>
        <p>Skills level up through real evidence — lessons, quizzes, challenges, projects and teaching. Not clicks.</p></div>

      {Object.entries(byCat).map(([cat, skills]) => (
        <div key={cat} style={{ marginBottom: 20 }}>
          <h2>{cat}</h2>
          <div className="grid g2">
            {skills.map(s => {
              const u: any = mine.get(s.key)
              const tierIdx = u?.tier_index || 0
              return (
                <div className="card" key={s.key}>
                  <div className="row between" style={{ marginBottom: 10 }}>
                    <div className="row"><span style={{ fontSize: 22 }}>{s.icon}</span>
                      <div><div style={{ fontWeight: 700 }}>{s.name}</div>
                        <span className="faint" style={{ fontSize: 12 }}>{u ? `${u.xp} XP` : 'Not started'}</span></div></div>
                    <span className={`badge ${tierIdx >= 3 ? 'g' : tierIdx >= 1 ? 'p' : ''}`}>{TIERS[tierIdx]}</span>
                  </div>
                  <div className="tier-track">
                    {TIERS.slice(1).map((t, i) => (
                      <div key={t} className={`tier-node ${tierIdx >= i + 1 ? 'reached' : ''}`}>{t}</div>
                    ))}
                  </div>
                  {u && (u.lessons + u.challenges + u.projects > 0) && (
                    <div className="faint" style={{ fontSize: 12, marginTop: 10 }}>
                      Evidence: {u.lessons} lessons · {u.challenges} challenges · {u.projects} projects
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
