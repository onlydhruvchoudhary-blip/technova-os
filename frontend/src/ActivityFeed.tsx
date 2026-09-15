import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, getToken } from './api'
import type { ActivityItem } from './types'
import { Empty, Spinner } from './ui'

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (s < 45) return 'just now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}d ago`
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function Row({ a, fresh }: { a: ActivityItem; fresh?: boolean }) {
  const body = (
    <>
      <span className="act-ico" aria-hidden>{a.icon}</span>
      <span className="act-body">
        <span className="act-text">
          <b>{a.actor || 'Someone'}</b> {a.text}
          {a.points > 0 && <span className="badge p" style={{ marginLeft: 6 }}>+{a.points}</span>}
        </span>
        <span className="act-time faint">{timeAgo(a.created_at)}</span>
      </span>
    </>
  )
  const cls = `act-row${fresh ? ' act-fresh' : ''}`
  return a.link
    ? <Link to={a.link} className={cls}>{body}</Link>
    : <div className={cls}>{body}</div>
}

/**
 * Live, club-wide activity pulse. Subscribes to the SSE stream for real-time inserts and
 * supports keyset "load more" pagination. `limit` caps how many are shown in compact mode.
 */
export default function ActivityFeed({ compact = false, limit = 8 }:
  { compact?: boolean; limit?: number }) {
  const [items, setItems] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [nextBefore, setNextBefore] = useState<number | null>(null)
  const [freshIds, setFreshIds] = useState<Set<number>>(new Set())
  const esRef = useRef<EventSource | null>(null)

  const load = async (before?: number) => {
    const d = await api.get<{ items: ActivityItem[]; next_before: number | null }>(
      `/activity?limit=${before ? 20 : limit}${before ? `&before=${before}` : ''}`)
    setItems(prev => before ? [...prev, ...d.items] : d.items)
    setNextBefore(d.next_before)
  }

  useEffect(() => {
    let alive = true
    load().catch(() => {}).finally(() => { if (alive) setLoading(false) })
    // Live subscription — mirrors the notifications SSE pattern (token via query param).
    try {
      const token = getToken()
      if (token && 'EventSource' in window) {
        const es = new EventSource(`/api/activity/stream?token=${encodeURIComponent(token)}`)
        esRef.current = es
        es.onmessage = (ev) => {
          try {
            const a = JSON.parse(ev.data) as ActivityItem
            if (!a || typeof a.id !== 'number') return
            setItems(prev => prev.some(x => x.id === a.id) ? prev : [a, ...prev])
            setFreshIds(prev => new Set(prev).add(a.id))
            setTimeout(() => setFreshIds(prev => {
              const n = new Set(prev); n.delete(a.id); return n
            }), 2600)
          } catch { /* ignore malformed frame */ }
        }
      }
    } catch { /* SSE optional; REST already loaded */ }
    return () => { alive = false; esRef.current?.close() }
  }, [])

  const shown = compact ? items.slice(0, limit) : items

  return (
    <div className="card">
      <div className="card-h">
        <h3><span className="live-dot" aria-hidden /> Live Activity</h3>
        {compact
          ? <Link className="btn ghost sm" to="/activity">All →</Link>
          : <span className="faint" style={{ fontSize: 12 }}>{items.length} events</span>}
      </div>
      {loading && <Spinner />}
      {!loading && shown.length === 0 &&
        <Empty icon="📡" title="Nothing yet" sub="Club activity will appear here in real time." />}
      <div className="act-list">
        {shown.map(a => <Row key={a.id} a={a} fresh={freshIds.has(a.id)} />)}
      </div>
      {!compact && nextBefore &&
        <div style={{ marginTop: 10, textAlign: 'center' }}>
          <button className="btn ghost sm" onClick={() => load(nextBefore)}>Load more</button>
        </div>}
    </div>
  )
}
