import './HealthStrip.css'

function SentimentBar({ counts, label }) {
  const total = counts.positive + counts.neutral + counts.negative
  const pW = total > 0 ? (counts.positive / total) * 100 : 0
  const nW = total > 0 ? (counts.neutral  / total) * 100 : 0
  const gW = total > 0 ? (counts.negative / total) * 100 : 0

  return (
    <div className="sent-row">
      <span className="sent-row-label">{label}</span>
      <div
        className="sentiment-track"
        role="img"
        aria-label={`${label}: ${counts.positive} positive, ${counts.neutral} neutral, ${counts.negative} negative`}
      >
        {pW > 0 && <div className="sent-seg sent-positive" style={{ width: `${pW}%` }} />}
        {nW > 0 && <div className="sent-seg sent-neutral"  style={{ width: `${nW}%` }} />}
        {gW > 0 && <div className="sent-seg sent-negative" style={{ width: `${gW}%` }} />}
      </div>
      <div className="sent-counts-inline">
        <span className="sent-label positive">{counts.positive}</span>
        <span className="sent-label neutral">{counts.neutral}</span>
        <span className="sent-label negative">{counts.negative}</span>
      </div>
    </div>
  )
}

export default function HealthStrip({ totalDollarsOver, sentiment }) {
  const fmt = (n) => '$' + Math.round(n).toLocaleString()

  return (
    <div className="health-strip card animate-in" style={{ animationDelay: '0.28s' }} aria-label="Health metrics">
      <div className="health-inner">

        <div className="health-stat">
          <span className="health-label">Total Margin Over Posted Rate</span>
          <span className="health-value">{fmt(totalDollarsOver)}</span>
        </div>

        <div className="health-divider" aria-hidden="true" />

        <div className="health-sentiment">
          <span className="health-label">Caller Sentiment</span>

          <div className="sent-legend" aria-hidden="true">
            <span className="sent-legend-item"><span className="sent-swatch sent-positive" />Positive</span>
            <span className="sent-legend-item"><span className="sent-swatch sent-neutral" />Neutral</span>
            <span className="sent-legend-item"><span className="sent-swatch sent-negative" />Negative</span>
          </div>

          <div className="sent-bars">
            <SentimentBar counts={sentiment.overall}    label="Overall" />
            <SentimentBar counts={sentiment.booked}     label="Booked" />
            <SentimentBar counts={sentiment.not_booked} label="Not booked" />
          </div>

          <p className="sent-honesty">
            Sentiment of AI agent calls only. No human-agent baseline is collected,
            so these figures are not comparative.
          </p>
        </div>

      </div>
    </div>
  )
}
