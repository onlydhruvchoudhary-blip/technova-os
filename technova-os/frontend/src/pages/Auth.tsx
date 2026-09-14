import { useState } from 'react'
import { useAuth, useToast } from '../store'

const FLOW = ['Discover', 'Learn', 'Practice', 'Collaborate', 'Build', 'Compete', 'Showcase', 'Earn', 'Lead']

export default function Auth() {
  const { login, register } = useAuth()
  const { push } = useToast()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await register(email, name, password)
    } catch (err: any) {
      push(err.message || 'Something went wrong', 'error')
    } finally { setBusy(false) }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <div className="row" style={{ marginBottom: 22 }}>
          <div className="brand-logo" style={{ width: 44, height: 44, fontSize: 20 }}>T</div>
          <div className="brand-name" style={{ fontSize: 22 }}>TECHNOVA<small>OPERATING SYSTEM</small></div>
        </div>
        <h1 style={{ fontSize: 40, lineHeight: 1.1, maxWidth: 520 }}>
          The digital operating system of your <span style={{ background: 'var(--grad)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>technology club.</span>
        </h1>
        <p className="muted" style={{ fontSize: 16, maxWidth: 480, marginTop: 14 }}>
          Learning, projects, competitions, events and achievement — connected into one ecosystem.
          Grow real skills, build real projects, and build a portfolio that proves it.
        </p>
        <div style={{ marginTop: 26, maxWidth: 540 }}>
          {FLOW.map((f, i) => <span key={f} className="flow-chip">{i + 1}. {f}</span>)}
        </div>
      </div>

      <div className="auth-form">
        <div className="auth-card">
          <h2>{mode === 'login' ? 'Welcome back' : 'Join TECHNOVA'}</h2>
          <p className="muted" style={{ marginTop: -6, marginBottom: 20 }}>
            {mode === 'login' ? 'Sign in to your club account.' : 'Create your member account.'}
          </p>
          <form onSubmit={submit}>
            {mode === 'register' && (
              <label className="field"><span>Full name</span>
                <input className="input" value={name} onChange={e => setName(e.target.value)} required minLength={2} placeholder="Isha Verma" />
              </label>
            )}
            <label className="field"><span>Email</span>
              <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@school.edu" />
            </label>
            <label className="field"><span>Password</span>
              <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} placeholder="At least 8 characters" />
            </label>
            <button className="btn primary" style={{ width: '100%', justifyContent: 'center', marginTop: 6 }} disabled={busy}>
              {busy ? '…' : mode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>
          <p className="muted" style={{ textAlign: 'center', marginTop: 16, fontSize: 14 }}>
            {mode === 'login' ? "New to TECHNOVA? " : 'Already a member? '}
            <a style={{ color: 'var(--primary)', cursor: 'pointer', fontWeight: 600 }}
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
              {mode === 'login' ? 'Create an account' : 'Sign in'}
            </a>
          </p>
          <div className="card" style={{ marginTop: 18, background: 'var(--bg-2)', fontSize: 12.5 }}>
            <strong>Demo accounts</strong> (password: <code className="mono">password123</code>)
            <div className="faint" style={{ marginTop: 6 }}>
              admin@technova.club · head@technova.club · mentor@technova.club · isha@technova.club
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
