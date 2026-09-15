import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { useToast } from '../store'
import { Spinner, Empty, Modal } from '../ui'
import type { Reward } from '../types'

const KINDS = ['All', 'physical', 'perk', 'digital']
const KIND_LABEL: Record<string, string> = { physical: 'Swag', perk: 'Perk', digital: 'Digital' }

export default function Store() {
  const { push } = useToast()
  const [rewards, setRewards] = useState<Reward[] | null>(null)
  const [balance, setBalance] = useState(0)
  const [lifetime, setLifetime] = useState(0)
  const [kind, setKind] = useState('All')
  const [tab, setTab] = useState<'shop' | 'mine'>('shop')
  const [mine, setMine] = useState<any[]>([])
  const [confirm, setConfirm] = useState<any>(null)

  const load = () => {
    api.get('/store/rewards').then(d => { setRewards(d.rewards); setBalance(d.balance) }).catch(() => setRewards([]))
    api.get('/store/wallet').then(w => { setBalance(w.balance); setLifetime(w.lifetime) }).catch(() => {})
    api.get('/store/redemptions').then(setMine).catch(() => {})
  }
  useEffect(load, [])

  const redeem = async (r: any) => {
    try {
      const res = await api.post(`/store/rewards/${r.id}/redeem`)
      setBalance(res.balance)
      push(`Redeemed ${r.name}! 🎁`, 'success')
      setConfirm(null)
      load()
    } catch (e) {
      push(e instanceof ApiError ? e.message : 'Could not redeem', 'error')
      setConfirm(null)
    }
  }

  if (!rewards) return <Spinner />
  const shown = rewards.filter(r => kind === 'All' || r.kind === kind)

  return (
    <div>
      <div className="page-head row between wrap" style={{ gap: 12 }}>
        <div>
          <h1>Rewards Store 🎁</h1>
          <p>Spend the points you've earned on real swag, perks and digital rewards.</p>
        </div>
        <div className="glass-card" style={{ padding: '12px 18px', textAlign: 'right' }}>
          <div className="faint" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>Your wallet</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--accent)' }}>{balance.toLocaleString()} pts</div>
          <div className="faint" style={{ fontSize: 11 }}>Spending never lowers your rank ({lifetime.toLocaleString()} lifetime)</div>
        </div>
      </div>

      <div className="row between wrap" style={{ marginBottom: 16, gap: 8 }}>
        <div className="row wrap" style={{ gap: 6 }}>
          {KINDS.map(k => (
            <button key={k} className={`btn sm ${kind === k ? 'primary' : 'ghost'}`} onClick={() => setKind(k)}>
              {k === 'All' ? 'All' : KIND_LABEL[k]}
            </button>
          ))}
        </div>
        <div className="row" style={{ gap: 6 }}>
          <button className={`btn sm ${tab === 'shop' ? 'primary' : 'ghost'}`} onClick={() => setTab('shop')}>Shop</button>
          <button className={`btn sm ${tab === 'mine' ? 'primary' : 'ghost'}`} onClick={() => setTab('mine')}>My redemptions ({mine.length})</button>
        </div>
      </div>

      {tab === 'shop' ? (
        shown.length === 0 ? <Empty icon="🎁" title="No rewards in this category" /> : (
          <div className="grid g3">
            {shown.map(r => {
              const soldOut = r.sold_out
              const cannot = !r.affordable || soldOut
              return (
                <div key={r.id} className="card reward-card" style={{ opacity: soldOut ? 0.6 : 1 }}>
                  <div className="row between" style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 40 }}>{r.icon}</div>
                    <span className="badge a">{KIND_LABEL[r.kind] || r.kind}</span>
                  </div>
                  <h3 style={{ margin: '0 0 6px' }}>{r.name}</h3>
                  <p className="faint" style={{ fontSize: 13, minHeight: 34 }}>{r.description}</p>
                  <div className="row between" style={{ marginTop: 10 }}>
                    <div style={{ fontWeight: 800, fontSize: 18, color: r.affordable ? 'var(--text)' : 'var(--muted)' }}>
                      {r.cost.toLocaleString()} pts
                    </div>
                    {r.stock >= 0 && <span className="faint" style={{ fontSize: 12 }}>{soldOut ? 'Sold out' : `${r.stock} left`}</span>}
                  </div>
                  <button className={`btn ${cannot ? 'ghost' : 'primary'}`} style={{ width: '100%', marginTop: 10 }}
                    disabled={cannot} onClick={() => setConfirm(r)}>
                    {soldOut ? 'Sold out' : r.affordable ? 'Redeem' : `Need ${(r.cost - balance).toLocaleString()} more`}
                  </button>
                </div>
              )
            })}
          </div>
        )
      ) : (
        mine.length === 0 ? <Empty icon="📦" title="No redemptions yet" sub="Redeem a reward and it'll show up here." /> : (
          <div className="grid" style={{ gap: 10 }}>
            {mine.map(m => (
              <div key={m.id} className="card row between wrap" style={{ gap: 10 }}>
                <div className="row" style={{ gap: 12 }}>
                  <div style={{ fontSize: 28 }}>{m.reward?.icon || '🎁'}</div>
                  <div>
                    <div style={{ fontWeight: 700 }}>{m.reward?.name}</div>
                    <div className="faint" style={{ fontSize: 12 }}>
                      {m.cost_at_claim.toLocaleString()} pts · {new Date(m.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <span className={`badge ${m.status === 'fulfilled' ? 'a' : m.status === 'cancelled' ? '' : 'p'}`}>
                  {m.status}
                </span>
              </div>
            ))}
          </div>
        )
      )}

      {confirm && (
        <Modal title="Confirm redemption" onClose={() => setConfirm(null)}>
          <div style={{ textAlign: 'center', padding: '8px 0' }}>
            <div style={{ fontSize: 48 }}>{confirm.icon}</div>
            <h3 style={{ margin: '8px 0 4px' }}>{confirm.name}</h3>
            <p className="faint" style={{ fontSize: 14 }}>{confirm.description}</p>
            <div style={{ margin: '14px 0', fontSize: 15 }}>
              Spend <b style={{ color: 'var(--accent)' }}>{confirm.cost.toLocaleString()} pts</b> ·
              Balance after: <b>{(balance - confirm.cost).toLocaleString()} pts</b>
            </div>
            <button className="btn primary" style={{ width: '100%' }} onClick={() => redeem(confirm)}>Confirm & redeem</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
