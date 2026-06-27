import { useRef, useState } from 'react'
import { useCountUp } from './useCountUp.js'
import './HeroStrip.css'

function fmt(n) {
  return Math.round(n).toLocaleString()
}

function StatCard({ label, hero, sub, accent, delay, estimate }) {
  return (
    <div className="stat-card animate-in card" style={{ animationDelay: delay }}>
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        {estimate && <span className="estimate-badge">estimate</span>}
      </div>
      <div className={`stat-hero ${accent ? 'accent' : ''}`}>{hero}</div>
      <div className="stat-sub">{sub}</div>
    </div>
  )
}

// Straight annualization: scale the 14-day window to a full year.
const WINDOW_DAYS = 14

function fmtAnnual(usd) {
  if (usd >= 1000) return `~$${(usd / 1000).toFixed(1)}k`
  return `~$${Math.round(usd)}`
}

function ValueCard({ value }) {
  const [open, setOpen] = useState(false)
  const closeTimer = useRef(null)

  const show = () => {
    clearTimeout(closeTimer.current)
    setOpen(true)
  }
  const hide = () => {
    // Small delay lets the cursor move from button into tooltip without closing
    closeTimer.current = setTimeout(() => setOpen(false), 120)
  }
  const toggle = () => setOpen(v => !v)

  // Headline: measured rep-hours freed (count up from 0)
  const hoursAnimated = useCountUp(value.rep_hours_freed, 700)

  // Supporting: modeled value + straight annualization of the same window
  const annualUsd = (value.value_captured_usd / WINDOW_DAYS) * 365

  return (
    <div className="stat-card animate-in card" style={{ animationDelay: '0.18s' }}>
      <div className="stat-top">
        <span className="stat-label">Rep-Hours Freed</span>

        {/* Anchor wraps button + tooltip so hover stays open while moving between them */}
        <div
          className="tooltip-anchor"
          onMouseEnter={show}
          onMouseLeave={hide}
        >
          <button
            className={`info-btn ${open ? 'open' : ''}`}
            onClick={toggle}
            onFocus={show}
            onBlur={hide}
            aria-label="Show value model assumptions"
            aria-expanded={open}
            aria-haspopup="true"
          >
            ⓘ
          </button>

          {open && (
            <div
              className="value-tooltip"
              role="tooltip"
              onMouseEnter={show}
              onMouseLeave={hide}
            >
              <p>
                <strong>Rep-hours freed</strong> = total agent talk-time across
                handled calls ({value.rep_hours_freed.toFixed(1)} hrs measured).
              </p>
              <p>
                <strong>Value</strong> = rep-hours
                &times; <strong>${value.assumed_loaded_wage_per_hour}/hr</strong> fully-loaded
                carrier-rep wage, minus <strong>${value.assumed_agent_cost_per_call}/call</strong> agent cost.
              </p>
              <p>
                The <strong>{fmtAnnual(annualUsd)}/yr</strong> figure projects
                the current {WINDOW_DAYS}-day rate forward at the same call volume.
                Straight extrapolation — actual volume may vary.
              </p>
              <p className="tooltip-caveat">
                Illustrative assumptions, not billed figures.
                Rep-hours freed is measured; all dollar figures are derived.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Measured headline */}
      <div className="stat-hero">
        {hoursAnimated.toFixed(1)}<span className="hero-unit"> hrs</span>
      </div>

      {/* Modeled dollars as supporting subline — clearly labeled */}
      <div className="stat-sub value-sub">
        <span className="value-estimate">
          ~${Math.round(value.value_captured_usd)} modeled
          &nbsp;·&nbsp;
          {fmtAnnual(annualUsd)}/yr projected
        </span>
      </div>

      <div className="estimate-tag">est.</div>
    </div>
  )
}

export default function HeroStrip({ capacity, value }) {
  const calls   = useCountUp(capacity.calls_handled, 600)
  const booking = useCountUp(capacity.booking_rate * 100, 650)
  const auto    = useCountUp(capacity.automation_rate * 100, 650)

  return (
    <section className="hero-strip" aria-label="Summary metrics">
      <StatCard
        label="Calls Handled"
        hero={fmt(calls)}
        sub={`${capacity.calls_after_hours} after-hours · ${capacity.calls_missed} missed · 0 hold time`}
        delay="0s"
      />
      <StatCard
        label="Booking Rate"
        hero={`${Math.round(booking)}%`}
        sub={`${capacity.loads_booked} loads covered`}
        accent
        delay="0.06s"
      />
      <StatCard
        label="Automation Rate"
        hero={`${Math.round(auto)}%`}
        sub="agent-resolved without human"
        delay="0.12s"
      />
      <ValueCard value={value} />
    </section>
  )
}
