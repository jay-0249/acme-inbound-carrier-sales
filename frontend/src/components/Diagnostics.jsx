import OutcomeBreakdown from './OutcomeBreakdown.jsx'
import MarginSignature from './MarginSignature.jsx'
import NegotiationBar from './NegotiationBar.jsx'
import './Diagnostics.css'

export default function Diagnostics({ outcomes, topDecline, margin, negotiation }) {
  return (
    <section className="diagnostics animate-in" style={{ animationDelay: '0.22s' }} aria-label="Diagnostics">
      <div className="diag-row">
        <div className="diag-left card">
          <OutcomeBreakdown outcomes={outcomes} topDecline={topDecline} />
        </div>
        <div className="diag-right card">
          <MarginSignature tiers={margin.by_urgency_tier} />
        </div>
      </div>
      <div className="card">
        <NegotiationBar negotiation={negotiation} />
      </div>
    </section>
  )
}
