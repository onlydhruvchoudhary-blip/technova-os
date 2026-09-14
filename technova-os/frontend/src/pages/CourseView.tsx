import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Spinner } from '../ui'

export default function CourseView() {
  const { slug } = useParams()
  const nav = useNavigate()
  const [course, setCourse] = useState<any>(null)
  useEffect(() => { api.get(`/academy/courses/${slug}`).then(setCourse) }, [slug])
  if (!course) return <Spinner />

  const done = course.lessons.filter((l: any) => l.completed).length

  return (
    <div>
      <Link to="/academy" className="faint" style={{ fontSize: 13 }}>← Academy</Link>
      <div className="page-head" style={{ marginTop: 8 }}>
        <h1>{course.title}</h1>
        <p>{course.description}</p>
        <div className="row" style={{ marginTop: 6 }}>
          <span className="badge a">{course.category}</span>
          <span className="badge">{course.difficulty}</span>
          <span className="badge p">{done}/{course.lessons.length} complete</span>
        </div>
      </div>

      <div className="card" style={{ maxWidth: 720 }}>
        <h3 style={{ marginTop: 0 }}>Learning path</h3>
        {course.lessons.map((l: any, i: number) => (
          <div key={l.id} className="row between"
            style={{ padding: '12px 0', borderTop: i ? '1px solid var(--border)' : 'none',
              opacity: l.unlocked ? 1 : 0.5 }}>
            <div className="row">
              <div style={{
                width: 30, height: 30, borderRadius: '50%', display: 'grid', placeItems: 'center',
                background: l.completed ? 'var(--grad)' : 'var(--bg-2)', fontWeight: 700, fontSize: 13,
                color: l.completed ? '#fff' : 'var(--text-dim)',
              }}>{l.completed ? '✓' : i + 1}</div>
              <div>
                <div style={{ fontWeight: 600 }}>{l.title}</div>
                <span className="faint" style={{ fontSize: 12 }}>
                  {l.kind === 'quiz' ? '📝 Quiz' : l.kind === 'video' ? '▶ Video' : '📄 Article'} · +{l.xp} XP
                  {l.completed && l.score ? ` · scored ${l.score}%` : ''}
                </span>
              </div>
            </div>
            {l.unlocked
              ? <button className="btn sm primary" onClick={() => nav(`/lesson/${l.id}`)}>{l.completed ? 'Review' : 'Start'}</button>
              : <span className="badge">🔒 Locked</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
