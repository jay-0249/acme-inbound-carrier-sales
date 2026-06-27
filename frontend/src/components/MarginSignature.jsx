import { useEffect, useRef, useState } from 'react'
import './MarginSignature.css'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

function pct(v) {
  return (v * 100).toFixed(1) + '%'
}

function TierBar({ tier, index }) {
  const ceilingPct = (tier.ceiling_multiplier - 1) * 100   // e.g. 8 for 1.08
  const realizedPct = tier.avg_pct_over_loadboard * 100     // e.g. 1.73

  // Normalize both against the max ceiling (8%) so bars fill the available width
  const maxCeiling = 8
  const ceilingWidth = (ceilingPct / maxCeiling) * 100      // % of track width
  const realizedWidth = (realizedPct / maxCeiling) * 100

  const [animated, setAnimated] = useState(prefersReducedMotion())

  useEffect(() => {
    const delay = 300 + index * 120
    const id = setTimeout(() => setAnimated(true), delay)
    return () => clearTimeout(id)
  }, [index])

  const gapPct = ceilingPct > 0 ? ((ceilingPct - realizedPct) / ceilingPct * 100).toFixed(0) : 0

  return (
    <div className="tier-row">
      <div className="tier-header">
        <span className="tier-label">{tier.tier}</span>
        <div className="tier-numbers">
          <span className="tier-realized">{pct(tier.avg_pct_over_loadboard)}</span>
          <span className="tier-sep"> / </span>
          <span className="tier-ceiling">{pct(tier.ceiling_multiplier - 1)} ceiling</span>
        </div>
      </div>

      {/* SVG bar: ceiling track + realized fill */}
      <div className="tier-track-wrap" aria-hidden="true">
        {/* ceiling track (full available width) */}
        <div
          className="tier-ceiling-track"
          style={{ width: `${ceilingWidth}%` }}
        />
        {/* realized fill */}
        <div
          className="tier-realized-fill"
          style={{
            width: animated ? `${realizedWidth}%` : '0%',
            transition: prefersReducedMotion()
              ? 'none'
              : `width 700ms cubic-bezier(0.16, 1, 0.3, 1) ${index * 80}ms`,
          }}
        />
        {/* gap annotation */}
        {ceilingPct > 0 && (
          <div
            className="tier-gap-label"
            style={{ left: `${realizedWidth + 1}%` }}
          >
            {gapPct}% gap
          </div>
        )}
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
        Realized margin runs well under the ceiling across all tiers.
        The gap represents room the agent could hold firmer without
        losing the lane — but tighter ceilings risk coverage.
      </p>
    </div>
  )
}
