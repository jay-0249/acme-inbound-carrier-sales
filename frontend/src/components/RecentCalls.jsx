import { useState } from 'react'
import './RecentCalls.css'

const OUTCOME_LABELS = {
  booked:             'Booked',
  negotiation_failed: 'Neg. failed',
  carrier_ineligible: 'Ineligible',
  load_not_found:     'Not found',
  not_interested:     'Not interested',
  equipment_mismatch: 'Equip. mismatch',
  other:              'Other',
}

const OUTCOME_CLASS = {
  booked:             'chip-teal',
  negotiation_failed: 'chip-clay',
  carrier_ineligible: 'chip-clay',
  load_not_found:     'chip-muted',
  not_interested:     'chip-muted',
  equipment_mismatch: 'chip-muted',
  other:              'chip-muted',
}

function OutcomeChip({ outcome }) {
  const label = OUTCOME_LABELS[outcome] ?? outcome ?? '-'
  const cls   = OUTCOME_CLASS[outcome] ?? 'chip-muted'
  return <span className={`chip ${cls}`}>{label}</span>
}

function fmtRate(rate) {
  if (rate == null) return <span className="nil">-</span>
  return '$' + Math.round(rate).toLocaleString()
}

function fmtPct(pct) {
  if (pct == null) return <span className="nil">-</span>
  const sign = pct >= 0 ? '+' : ''
  return <span className={pct > 0 ? 'pct-over' : ''}>{sign}{(pct * 100).toFixed(1)}%</span>
}

function fmtTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))
  if (isNaN(d)) return '-'
  const now = new Date()
  const diffH = (now - d) / 3_600_000
  if (diffH < 1)   return `${Math.round(diffH * 60)}m ago`
  if (diffH < 24)  return `${Math.round(diffH)}h ago`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const COLS = [
  { key: 'carrier_name', label: 'Carrier' },
  { key: 'load_id',      label: 'Load' },
  { key: 'outcome',      label: 'Outcome' },
  { key: 'sentiment',    label: 'Sentiment' },
  { key: 'final_rate',   label: 'Rate' },
  { key: 'pct_over_loadboard', label: 'vs Posted' },
  { key: 'rounds',       label: 'Rounds' },
  { key: 'created_at',   label: 'Time' },
]

export default function RecentCalls({ calls }) {
  const [sortKey, setSortKey] = useState('created_at')
  const [sortDir, setSortDir] = useState('desc')

  const handleSort = (key) => {
    if (key === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = [...calls].sort((a, b) => {
    let av = a[sortKey], bv = b[sortKey]
    if (av == null) av = sortDir === 'asc' ? Infinity : -Infinity
    if (bv == null) bv = sortDir === 'asc' ? Infinity : -Infinity
    if (typeof av === 'string') return sortDir === 'asc'
      ? av.localeCompare(bv)
      : bv.localeCompare(av)
    return sortDir === 'asc' ? av - bv : bv - av
  })

  return (
    <section className="recent-calls animate-in card" style={{ animationDelay: '0.34s' }} aria-label="Recent calls">
      <div className="rc-header">
        <p className="section-label" style={{ marginBottom: 0 }}>Recent Calls</p>
        <span className="rc-count">{calls.length} shown</span>
      </div>

      <div className="table-scroll" tabIndex={0}>
        <table className="rc-table" aria-label="Recent call records">
          <thead>
            <tr>
              {COLS.map(c => (
                <th
                  key={c.key}
                  className={sortKey === c.key ? 'sorted' : ''}
                  onClick={() => handleSort(c.key)}
                  tabIndex={0}
                  role="columnheader"
                  aria-sort={sortKey === c.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                  onKeyDown={e => e.key === 'Enter' && handleSort(c.key)}
                >
                  {c.label}
                  {sortKey === c.key && (
                    <span className="sort-arrow" aria-hidden="true">
                      {sortDir === 'asc' ? ' ↑' : ' ↓'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map(row => {
              const RowTag = row.run_url ? 'a' : 'tr'
              const rowProps = row.run_url
                ? { href: row.run_url, target: '_blank', rel: 'noopener noreferrer' }
                : {}
              return (
                <tr
                  key={row.run_id}
                  className={row.run_url ? 'row-link' : ''}
                  onClick={row.run_url ? () => window.open(row.run_url, '_blank', 'noopener') : undefined}
                  tabIndex={row.run_url ? 0 : undefined}
                  role={row.run_url ? 'link' : undefined}
                  aria-label={row.run_url ? `Open call ${row.run_id} in HappyRobot` : undefined}
                  onKeyDown={row.run_url
                    ? e => e.key === 'Enter' && window.open(row.run_url, '_blank', 'noopener')
                    : undefined}
                >
                  <td className="td-carrier">{row.carrier_name || <span className="nil">-</span>}</td>
                  <td className="td-mono">{row.load_id || <span className="nil">-</span>}</td>
                  <td><OutcomeChip outcome={row.outcome} /></td>
                  <td>
                    {row.sentiment === 'negative'
                      ? <span className="sentiment-flag">negative</span>
                      : <span className="sent-plain">{row.sentiment ?? '-'}</span>}
                  </td>
                  <td className="td-num">{fmtRate(row.final_rate)}</td>
                  <td className="td-num">{fmtPct(row.pct_over_loadboard)}</td>
                  <td className="td-num">{row.rounds ?? <span className="nil">-</span>}</td>
                  <td className="td-time">{fmtTime(row.created_at)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
