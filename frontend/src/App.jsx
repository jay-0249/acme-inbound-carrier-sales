import { useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import HeroStrip from './components/HeroStrip.jsx'
import Diagnostics from './components/Diagnostics.jsx'
import HealthStrip from './components/HealthStrip.jsx'
import RecentCalls from './components/RecentCalls.jsx'
import Skeleton from './components/Skeleton.jsx'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const API_KEY  = import.meta.env.VITE_API_KEY  ?? ''

export default function App() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/metrics`, {
      headers: { 'X-API-Key': API_KEY },
    })
      .then(r => {
        if (!r.ok) throw new Error(`API returned ${r.status}`)
        return r.json()
      })
      .then(d => { if (!cancelled) { setData(d); setLoading(false) } })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false) } })

    return () => { cancelled = true }
  }, [])

  return (
    <div className="app">
      <Header />

      {loading && <Skeleton />}

      {error && (
        <div className="error-state">
          <p className="error-title">Dashboard unavailable</p>
          <p className="error-detail">
            Could not reach <code>/metrics</code>. Check that the API server
            is running and <code>VITE_API_KEY</code> matches the server&rsquo;s
            <code>LOADS_API_KEY</code>.
          </p>
          <p className="error-hint">Error: {error}</p>
        </div>
      )}

      {data && !loading && (
        <main className="content">
          <HeroStrip capacity={data.capacity} value={data.value_model} />
          <Diagnostics
            outcomes={data.outcomes}
            topDecline={data.top_decline_reason}
            margin={data.margin}
            negotiation={data.negotiation}
          />
          <HealthStrip
            totalDollarsOver={data.margin.total_dollars_over_loadboard}
            sentiment={data.sentiment}
          />
          <RecentCalls calls={data.recent_calls} />
        </main>
      )}
    </div>
  )
}
