import './OutcomeBreakdown.css'

const LABELS = {
  booked:              'Booked',
  negotiation_failed:  'Negotiation failed',
  carrier_ineligible:  'Carrier ineligible',
  load_not_found:      'Load not found',
  not_interested:      'Not interested',
  equipment_mismatch:  'Equipment mismatch',
  other:               'Other / unresolved',
}

export default function OutcomeBreakdown({ outcomes, topDecline }) {
  const total = outcomes.reduce((s, o) => s + o.count, 0)

  return (
    <div className="outcome-breakdown">
      <p className="section-label">Outcome Breakdown</p>

      <ol className="outcome-list" aria-label="Call outcomes">
        {outcomes.map((o) => {
          const isBooked = o.outcome === 'booked'
          // Width = share of TOTAL calls so bar length = honest proportion
          const barW = total > 0 ? (o.count / total) * 100 : 0
          return (
            <li key={o.outcome} className="outcome-row">
              <div className="outcome-meta">
                <span className="outcome-name">{LABELS[o.outcome] ?? o.outcome}</span>
                <span className="outcome-count">{o.count}</span>
              </div>
              <div className="outcome-track" aria-hidden="true">
                <div
                  className={`outcome-bar ${isBooked ? 'bar-teal' : 'bar-neutral'}`}
                  style={{ width: `${barW}%` }}
                />
              </div>
            </li>
          )
        })}
      </ol>

      <p className="decline-callout">
        Biggest gap:{' '}
        <span className="callout-outcome">
          {LABELS[topDecline.outcome] ?? topDecline.outcome}
        </span>{' '}
        <span className="callout-count">({topDecline.count} calls)</span>
      </p>
    </div>
  )
}
