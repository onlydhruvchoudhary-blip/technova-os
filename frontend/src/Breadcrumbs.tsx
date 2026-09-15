import { Link, useLocation } from 'react-router-dom'

const LABELS: Record<string, string> = {
  '': 'Dashboard', leaderboard: 'Leaderboard', profile: 'My Portfolio', academy: 'Academy',
  skills: 'Skill Tree', challenges: 'Challenges', grading: 'Code Review', projects: 'Projects',
  competitions: 'Competitions', events: 'Events', members: 'Members', governance: 'Governance',
  store: 'Rewards Store', showcase: 'Showcase', resources: 'Resources', admin: 'Admin', lesson: 'Lesson',
}

export default function Breadcrumbs() {
  const loc = useLocation()
  const parts = loc.pathname.split('/').filter(Boolean)
  if (parts.length === 0) return null  // no crumbs on the dashboard root

  const crumbs = parts.map((p, i) => {
    const to = '/' + parts.slice(0, i + 1).join('/')
    const label = LABELS[p] || decodeURIComponent(p).replace(/-/g, ' ')
    return { to, label, last: i === parts.length - 1 }
  })

  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      <Link to="/" className="crumb">Home</Link>
      {crumbs.map(c => (
        <span key={c.to} className="crumb-wrap">
          <span className="crumb-sep">/</span>
          {c.last ? <span className="crumb current">{c.label}</span>
            : <Link to={c.to} className="crumb">{c.label}</Link>}
        </span>
      ))}
    </nav>
  )
}
