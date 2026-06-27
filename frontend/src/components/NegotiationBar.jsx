import './NegotiationBar.css'

export default function NegotiationBar({ negotiation }) {
  const { avg_rounds_to_close, settled_distribution: d } = negotiation
  const total = d.round_1 + d.round_2 + d.round_3 + d.walked

  const segments = [
    { key: 'round_1', label: 'Round 1', color: 'var(--teal)',   value: d.round_1 },
    { key: 'round_2', label: 'Round 2', color: '#1BA87E',        value: d.round_2 },
    { key: 'round_3', label: 'Round 3', color: '#137860',        value: d.round_3 },
    { key: 'walked',  label: 'Walked',  color: 'var(--clay)',    value: d.walked  },
  ]

  return (
    <div className="neg-bar-wrap">
      <div className="neg-header">
        <p className="section-label" style={{ marginBottom: 0 }}>Negotiation Effectiveness</p>
        <div className="neg-avg">
          <span className="neg-avg-num">{avg_rounds_to_close.toFixed(1)}</span>
          <span className="neg-avg-label">avg rounds to close</span>
        </div>
      </div>

      {total > 0 ? (
        <>
          <div className="neg-track" role="img" aria-label={`Negotiation outcomes: Round 1: ${d.round_1}, Round 2: ${d.round_2}, Round 3: ${d.round_3}, Walked: ${d.walked}`}>
            {segments.filter(s => s.value > 0).map(s => (
              <div
                key={s.key}
                className="neg-segment"
                style={{
                  width: `${(s.value / total) * 100}%`,
                  background: s.color,
                }}
              />
            ))}
          </div>
          <div className="neg-legend">
            {segments.map(s => s.value > 0 && (
              <div key={s.key} className="neg-legend-item">
                <span className="neg-swatch" style={{ background: s.color }} />
                <span className="neg-legend-label">{s.label}</span>
                <span className="neg-legend-count">{s.value}</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="neg-empty">No negotiation data yet.</p>
      )}
    </div>
  )
}
