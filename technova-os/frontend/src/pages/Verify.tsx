import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'
import { Spinner } from '../ui'

export default function Verify() {
  const { uid } = useParams()
  const [data, setData] = useState<any>(null)
  useEffect(() => { api.get(`/verify/${uid}`).then(setData).catch(() => setData({ valid: false, reason: 'Not found' })) }, [uid])
  if (!data) return <Spinner />

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 20,
      background: 'radial-gradient(900px 500px at 50% 0%, rgba(124,92,255,.18), transparent), var(--bg)' }}>
      <div className="card" style={{ maxWidth: 480, width: '100%', textAlign: 'center', padding: 36 }}>
        <div className="row" style={{ justifyContent: 'center', gap: 10, marginBottom: 20 }}>
          <div className="brand-logo">T</div><div className="brand-name">TECHNOVA<small>CERTIFICATE VERIFICATION</small></div>
        </div>
        <div style={{ fontSize: 64, marginBottom: 12 }}>{data.valid ? '✅' : '❌'}</div>
        <h1 style={{ margin: '0 0 6px' }}>{data.valid ? 'Certificate Verified' : 'Not Valid'}</h1>
        {!data.valid && <p className="muted">{data.reason}</p>}
        {data.valid && (
          <div style={{ textAlign: 'left', marginTop: 20 }}>
            <div className="card" style={{ background: 'var(--bg-2)' }}>
              <Row k="Recipient" v={data.recipient} />
              <Row k="Certificate" v={data.title} />
              <Row k="Type" v={data.kind} />
              {data.context && <Row k="For" v={data.context} />}
              <Row k="Issued by" v={data.issuer} />
              <Row k="Issued on" v={new Date(data.issued_at).toLocaleDateString()} />
              <Row k="ID" v={data.cert_uid} mono />
            </div>
            <p className="faint" style={{ fontSize: 12, textAlign: 'center', marginTop: 14 }}>
              This certificate is cryptographically signed by TECHNOVA and authentic.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return <div className="row between" style={{ padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
    <span className="faint" style={{ fontSize: 13 }}>{k}</span>
    <span className={mono ? 'mono' : ''} style={{ fontWeight: 600, fontSize: 14 }}>{v}</span></div>
}
