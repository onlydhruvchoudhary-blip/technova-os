import React from 'react'

interface State { error: Error | null }

/** Catches render-time crashes so one broken component can't blank the whole app. */
export default class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('UI crashed:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
          <div className="glass-card" style={{ padding: 28, maxWidth: 440, textAlign: 'center' }}>
            <div style={{ fontSize: 44 }}>🛠️</div>
            <h2 style={{ margin: '10px 0 6px' }}>Something broke on this screen</h2>
            <p className="faint" style={{ fontSize: 14 }}>
              The rest of TECHNOVA OS is fine. Try reloading — if it keeps happening, tell an admin.
            </p>
            <div className="row" style={{ justifyContent: 'center', marginTop: 14 }}>
              <button className="btn primary" onClick={() => window.location.reload()}>Reload</button>
              <button className="btn ghost" onClick={() => { window.location.href = '/' }}>Go home</button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
