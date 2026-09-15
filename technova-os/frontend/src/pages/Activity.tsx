import ActivityFeed from '../ActivityFeed'

export default function Activity() {
  return (
    <div>
      <div className="page-head">
        <h1>Club Activity</h1>
        <p>The live pulse of TECHNOVA — badges, graded code, projects shipped, rewards, and votes as they happen.</p>
      </div>
      <div style={{ maxWidth: 680 }}>
        <ActivityFeed limit={30} />
      </div>
    </div>
  )
}
