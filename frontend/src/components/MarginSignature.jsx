import { useEffect, useState } from 'react'
import './MarginSignature.css'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Shared axis: 0 to AXIS_MAX percent. Largest ceiling is 8%; 9 gives breathing room.
const AXIS_MAX = 9

function TierBar({ tier, index }) {
  const ceilingPct = (tier.ceiling_multiplier - 1) * 100  // e.g. 8.0
  const realizedPct = tier.avg_pct_over_loadboard * 100   // e.g. 1.7

  // Positions on the shared 0–AXIS_MAX axis, expressed as % of track width
  const realizedW = (realizedPct / AXIS_MAX) * 100
  const ceilingX  = (ceilingPct  / AXIS_MAX) * 100

  const reduced = prefersReducedMotion()
  const [ready, setReady] = useState(reduced)

  useEffect(() => {
    const id = setTimeout(() => setReady(true), 300 + index * 100)
    return () => clearTimeout(id)
  }, [index])

  const barDelay = index * 80
  const barTransition   = reduced ? 'none' : `width 700ms cubic-bezier(0.16,1,0.3,1) ${barDelay}ms`
  // Label fades in after the bar finishes travelling
  const labelTransition = reduced ? 'none' : `opacity 250ms ease ${700 + barDelay}ms`

  return (
    <div className="tier-row">
      <span className="tier-label">{tier.tier}</span>
      <div
        className="tier-track-wrap"
        role="img"
        aria-label={`${tier.tier}: ${realizedPct.toFixed(1)}% realized, ${ceilingPct.toFixed(1)}% ceiling`}
      >
        {/* Teal realized bar */}
        <div
          className="tier-realized-fill"
          style={{
            width: ready ? `${realizedW}%` : '0%',
            transition: barTransition,
          }}
        />

        {/* Realized value label — appears at bar end after animation */}
        <span
          className="tier-realized-label"
          style={{
            left: `calc(${realizedW}% + 6px)`,
            opacity: ready ? 1 : 0,
            transition: labelTransition,
          }}
        >
          {realizedPct.toFixed(1)}%
        </span>

        {/* Ceiling tick — vertical marker at that tier's ceiling */}
        <div className="tier-ceiling-tick" style={{ left: `${ceilingX}%` }} />

        {/* Ceiling label — above the tick */}
        <span className="tier-ceiling-label" style={{ left: `${ceilingX}%` }}>
          ceiling {ceilingPct.toFixed(0)}%
        </span>
      </div>
    </div>
  )
}

export default function MarginSignature({ tiers }) {
  return (
    <div className="margin-signature">
      <p className="section-label">Realized Margin vs. Ceiling — by Urgency Tier</p>

      <div className="tier-list">
        {tiers.map((t, i) => (
          <TierBar key={t.tier} tier={t} index={i} />
        ))}
      </div>

      <div className="margin-legend" aria-hidden="true">
        <span className="legend-item">
          <span className="legend-swatch swatch-realized" />
          Realized avg. over posted rate
        </span>
        <span className="legend-item">
          <span className="legend-swatch swatch-ceiling" />
          Designed ceiling
        </span>
      </div>

      <p className="margin-callout">
        Each bar is realized margin; the marker is that tier's ceiling. Realized
        sits well below ceiling across all tiers — room to negotiate firmer, though
        tighter ceilings on distant loads limit upside.
      </p>
    </div>
  )
}
