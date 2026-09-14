import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Spinner, Bar, Empty } from '../ui'

export default function Academy() {
  const [courses, setCourses] = useState<any[]>([])
  const [cat, setCat] = useState('All')
  useEffect(() => { api.get('/academy/courses').then(setCourses) }, [])
  if (!courses) return <Spinner />

  const cats = ['All', ...Array.from(new Set(courses.map(c => c.category)))]
  const shown = cat === 'All' ? courses : courses.filter(c => c.category === cat)

  return (
    <div>
      <div className="page-head"><h1>TECHNOVA Academy</h1>
        <p>Structured learning paths. Every lesson you complete grows a real skill.</p></div>
      <div className="row wrap" style={{ marginBottom: 18 }}>
        {cats.map(c => <button key={c} className={`btn sm ${cat === c ? 'primary' : 'ghost'}`} onClick={() => setCat(c)}>{c}</button>)}
      </div>
      {shown.length === 0 ? <Empty icon="📚" title="No courses here yet" /> : (
        <div className="grid g3">
          {shown.map(c => (
            <Link to={`/academy/${c.slug}`} key={c.id} className="card" style={{ display: 'block' }}>
              <div className="row between" style={{ marginBottom: 8 }}>
                <span className="badge a">{c.category}</span>
                <span className="badge">{c.difficulty}</span>
              </div>
              <h3 style={{ margin: '0 0 6px' }}>{c.title}</h3>
              <p className="faint" style={{ fontSize: 13, minHeight: 38 }}>{c.description}</p>
              <div className="row between" style={{ margin: '10px 0 6px', fontSize: 12 }}>
                <span className="muted">{c.completed}/{c.lessons} lessons</span>
                <span className="muted">{c.progress}%</span>
              </div>
              <Bar value={c.progress} />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
