import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { useAuth, useToast } from '../store'
import { Spinner, Empty, Bar, Modal } from '../ui'

const COMMITTEE_PLUS = ['COMMITTEE', 'MENTOR', 'ADVISOR', 'CLUB_HEAD', 'SUPER_ADMIN']

export default function Governance() {
  const { user } = useAuth()
  const { push } = useToast()
  const [standing, setStanding] = useState<any>(null)
  const [proposals, setProposals] = useState<any[] | null>(null)
  const [creating, setCreating] = useState(false)

  const canManage = COMMITTEE_PLUS.includes(user!.role)
  const canFund = ['CLUB_HEAD', 'SUPER_ADMIN'].includes(user!.role)

  const load = () => {
    api.get('/governance/standing').then(setStanding).catch(() => {})
    api.get('/governance/proposals').then(setProposals).catch(() => setProposals([]))
  }
  useEffect(load, [])

  const vote = async (pid: number, choice: string) => {
    try {
      await api.post(`/governance/proposals/${pid}/vote`, { choice })
      push('Vote cast! 🗳️', 'success')
      load()
    } catch (e) {
      push(e instanceof ApiError ? e.message : 'Could not vote', 'error')
    }
  }
  const close = async (pid: number) => {
    try { await api.post(`/governance/proposals/${pid}/close`); push('Proposal closed', 'success'); load() }
    catch (e) { push(e instanceof ApiError ? e.message : 'Failed', 'error') }
  }
  const claim = async () => {
    try { const r = await api.post('/governance/eligibility/claim'); push(`Requested: ${r.claimed} 🎉`, 'success') }
    catch (e) { push(e instanceof ApiError ? e.message : 'Failed', 'error') }
  }

  if (!standing || !proposals) return <Spinner />

  const tier = standing.tier
  const nxt = standing.next_tier
  const qualified = (standing.eligibility || []).filter((e: any) => e.qualified && !e.already_held)

  return (
    <div>
      <div className="page-head">
        <h1>Club Governance 🗳️</h1>
        <p>Your contribution earns your say. Climb tiers, unlock voting power, and shape club decisions.</p>
      </div>

      {/* ---- your standing ---- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="row between wrap" style={{ gap: 16 }}>
          <div>
            <div className="faint" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>Your membership tier</div>
            <h2 style={{ margin: '4px 0' }}>{tier.icon} {tier.name}</h2>
            <div className="faint" style={{ fontSize: 13 }}>{standing.points.toLocaleString()} lifetime points</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div className="faint" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>Voting power</div>
            <div style={{ fontSize: 34, fontWeight: 800, color: standing.can_vote ? 'var(--accent)' : 'var(--muted)' }}>
              {standing.can_vote ? `×${standing.vote_weight}` : '—'}
            </div>
            <div className="faint" style={{ fontSize: 12 }}>
              {standing.can_vote ? 'votes per ballot' : `Reach ${standing.min_voting_tier.name} to vote`}
            </div>
          </div>
        </div>
        {nxt && (
          <div style={{ marginTop: 14 }}>
            <div className="row between" style={{ fontSize: 12, marginBottom: 4 }}>
              <span className="faint">Progress to {nxt.icon} {nxt.name}</span>
              <span className="faint">{standing.points_to_next.toLocaleString()} pts to go</span>
            </div>
            <Bar value={standing.points - tier.min_points} max={nxt.min_points - tier.min_points} />
          </div>
        )}
        {qualified.length > 0 && (
          <div className="card" style={{ marginTop: 14, background: 'var(--accent-soft, rgba(124,92,255,0.1))' }}>
            <div className="row between wrap" style={{ gap: 10 }}>
              <div>🎉 <b>You're eligible for a promotion:</b> {qualified.map((q: any) => q.label).join(', ')}</div>
              <button className="btn sm primary" onClick={claim}>Request review</button>
            </div>
          </div>
        )}
      </div>

      {/* ---- create ---- */}
      {canManage && (
        <div className="row" style={{ marginBottom: 16 }}>
          <button className="btn primary" onClick={() => setCreating(true)}>+ New proposal</button>
        </div>
      )}

      {/* ---- proposals ---- */}
      {proposals.length === 0 ? <Empty icon="🗳️" title="No proposals yet" sub="Check back when the club opens a vote." /> : (
        <div className="grid" style={{ gap: 16 }}>
          {proposals.map(p => (
            <ProposalCard key={p.id} p={p} standing={standing} onVote={vote} onClose={close} canManage={canManage} />
          ))}
        </div>
      )}

      {creating && (
        <CreateModal canFund={canFund} onClose={() => setCreating(false)}
          onCreated={() => { setCreating(false); load() }} />
      )}
    </div>
  )
}

function ProposalCard({ p, standing, onVote, onClose, canManage }: any) {
  const t = p.tally
  const total = t.total_weight || 0
  const open = p.status === 'open'
  const pct = (opt: string) => total ? Math.round((t.by_choice[opt]?.weight || 0) / total * 100) : 0

  return (
    <div className="card">
      <div className="row between wrap" style={{ gap: 8, marginBottom: 6 }}>
        <span className={`badge ${p.kind === 'funding' ? 'a' : 'p'}`}>
          {p.kind === 'funding' ? `💰 Funding${p.amount ? ` · ${p.amount.toLocaleString()}` : ''}` : '📋 Decision'}
        </span>
        <span className={`badge ${open ? '' : 'a'}`}>{open ? 'Open' : 'Closed'}</span>
      </div>
      <h3 style={{ margin: '0 0 6px' }}>{p.title}</h3>
      {p.description && <p className="faint" style={{ fontSize: 14 }}>{p.description}</p>}
      {p.project && <div className="faint" style={{ fontSize: 12, marginBottom: 8 }}>↳ Project: {p.project.title}</div>}

      {/* results bars */}
      <div style={{ margin: '12px 0' }}>
        {p.options.map((opt: string) => (
          <div key={opt} style={{ marginBottom: 8 }}>
            <div className="row between" style={{ fontSize: 13, marginBottom: 3 }}>
              <span>{p.my_vote === opt ? '✅ ' : ''}{opt}</span>
              <span className="faint">{pct(opt)}% · {t.by_choice[opt]?.count || 0} voters</span>
            </div>
            <Bar value={t.by_choice[opt]?.weight || 0} max={total || 1} />
          </div>
        ))}
      </div>

      <div className="faint" style={{ fontSize: 12, marginBottom: 10 }}>
        {t.total_votes} voter{t.total_votes === 1 ? '' : 's'} · {total} weighted votes
        {p.outcome && <> · <b>Outcome:</b> {p.outcome}</>}
      </div>

      {/* actions */}
      {open && (
        p.my_vote
          ? <div className="badge" style={{ display: 'inline-block' }}>You voted: {p.my_vote}</div>
          : standing.can_vote
            ? <div className="row wrap" style={{ gap: 8 }}>
                {p.options.map((opt: string) => (
                  <button key={opt} className="btn sm ghost" onClick={() => onVote(p.id, opt)}>{opt}</button>
                ))}
                <span className="faint" style={{ fontSize: 12, alignSelf: 'center' }}>(your vote counts ×{standing.vote_weight})</span>
              </div>
            : <div className="faint" style={{ fontSize: 13 }}>🔒 Reach {standing.min_voting_tier.name} tier to vote on this.</div>
      )}
      {open && canManage && (
        <div style={{ marginTop: 10 }}>
          <button className="btn sm" onClick={() => onClose(p.id)}>Close voting</button>
        </div>
      )}
    </div>
  )
}

function CreateModal({ canFund, onClose, onCreated }: any) {
  const { push } = useToast()
  const [form, setForm] = useState<any>({
    title: '', description: '', kind: 'decision', amount: 0,
    options: 'Approve, Reject, Abstain', closes_in_days: 7,
  })
  const submit = async () => {
    try {
      await api.post('/governance/proposals', {
        ...form,
        amount: Number(form.amount) || 0,
        options: form.options.split(',').map((s: string) => s.trim()).filter(Boolean),
      })
      push('Proposal opened for voting! 🗳️', 'success')
      onCreated()
    } catch (e) {
      push(e instanceof ApiError ? e.message : 'Could not create', 'error')
    }
  }
  return (
    <Modal title="New proposal" onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <input className="input" placeholder="Title / question" value={form.title}
          onChange={e => setForm({ ...form, title: e.target.value })} />
        <textarea className="input" rows={3} placeholder="Describe the decision…" value={form.description}
          onChange={e => setForm({ ...form, description: e.target.value })} />
        <div className="row wrap" style={{ gap: 8 }}>
          <button className={`btn sm ${form.kind === 'decision' ? 'primary' : 'ghost'}`}
            onClick={() => setForm({ ...form, kind: 'decision' })}>📋 Decision</button>
          {canFund && <button className={`btn sm ${form.kind === 'funding' ? 'primary' : 'ghost'}`}
            onClick={() => setForm({ ...form, kind: 'funding' })}>💰 Funding</button>}
        </div>
        {form.kind === 'funding' && (
          <input className="input" type="number" placeholder="Amount requested" value={form.amount}
            onChange={e => setForm({ ...form, amount: e.target.value })} />
        )}
        <input className="input" placeholder="Options (comma-separated)" value={form.options}
          onChange={e => setForm({ ...form, options: e.target.value })} />
        <label className="faint" style={{ fontSize: 13 }}>
          Closes in
          <input className="input" type="number" min={1} max={90} style={{ width: 70, margin: '0 6px' }}
            value={form.closes_in_days} onChange={e => setForm({ ...form, closes_in_days: Number(e.target.value) })} />
          days
        </label>
        <button className="btn primary" onClick={submit} disabled={!form.title.trim()}>Open for voting</button>
      </div>
    </Modal>
  )
}
