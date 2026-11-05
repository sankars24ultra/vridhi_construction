import type { Dashboard } from '../../lib/api'
import { currency } from '../../lib/format'

export function CostBreakdownDonut({ dash }: { dash?: Dashboard }) {
  const actualCost = Number(dash?.actual_cost || 0)

  // Use recorded breakdown categories or project cost items
  const recordedBreakdown = dash?.cost_breakdown?.filter(c => c.recorded && Number(c.amount || 0) > 0) || []
  const hasRecordedBreakdown = recordedBreakdown.length > 0

  const rawCategories = hasRecordedBreakdown
    ? recordedBreakdown
    : (dash?.cost_breakdown && dash.cost_breakdown.length > 0
        ? dash.cost_breakdown
        : [
            { category: 'Material', amount: String(actualCost * 0.45) },
            { category: 'Labour', amount: String(actualCost * 0.35) },
            { category: 'Equipment', amount: String(actualCost * 0.15) },
            { category: 'Other', amount: String(actualCost * 0.05) }
          ])

  const totalBreakdownAmt = rawCategories.reduce((acc, cat) => acc + Number(cat.amount || 0), 0) || actualCost || 1
  const defaultColors = ['#004b87', '#56a5eb', '#1e88e5', '#8dc6ff', '#002e5b', '#00bcd4']

  const categories = rawCategories.map((cat, i) => {
    const amt = Number(cat.amount || 0)
    const pct = Math.round((amt / totalBreakdownAmt) * 100)
    return {
      name: cat.category,
      amount: amt,
      percent: pct,
      color: defaultColors[i % defaultColors.length] || '#004b87'
    }
  })

  // Slices
  let currentAngle = 0
  const donutSlices = categories.map(cat => {
    const sliceAngle = (Math.max(4, cat.percent) / 100) * 360
    const start = currentAngle
    const end = currentAngle + sliceAngle
    currentAngle = end
    return {
      ...cat,
      startAngle: start,
      endAngle: end,
      midAngle: (start + end) / 2
    }
  })

  return (
    <div className="cost-breakdown-donut-widget">
      {/* Donut Graphic */}
      <div className="cost-donut-chart-wrap">
        <svg viewBox="0 0 280 180" className="cost-donut-svg">
          {donutSlices.map(slice => (
            <path
              key={slice.name}
              d={describeArc(140, 90, 32, 54, slice.startAngle, slice.endAngle)}
              fill={slice.color}
            />
          ))}

          {/* Callout Lines & Percentages */}
          {donutSlices.map(slice => {
            const rad = ((slice.midAngle - 90) * Math.PI) / 180
            const dotX = 140 + 56 * Math.cos(rad)
            const dotY = 90 + 56 * Math.sin(rad)
            const isRight = Math.cos(rad) >= 0
            const lineEndX = isRight ? dotX + 18 : dotX - 18
            const lineEndY = dotY + (Math.sin(rad) >= 0 ? 9 : -9)
            const horizEndX = isRight ? lineEndX + 14 : lineEndX - 14
            const textX = isRight ? horizEndX + 4 : horizEndX - 4

            return (
              <g key={`callout-${slice.name}`}>
                <circle cx={dotX} cy={dotY} r="2" fill={slice.color} />
                <line x1={dotX} y1={dotY} x2={lineEndX} y2={lineEndY} stroke={slice.color} strokeWidth="1" />
                <line x1={lineEndX} y1={lineEndY} x2={horizEndX} y2={lineEndY} stroke={slice.color} strokeWidth="1" />
                <text
                  x={textX}
                  y={lineEndY + 3}
                  className="cost-donut-callout-text"
                  textAnchor={isRight ? 'start' : 'end'}
                >
                  {slice.percent}%
                </text>
              </g>
            )
          })}

          {/* Center Medallion Emblem */}
          <circle cx="140" cy="90" r="28" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1.2" />
          <g transform="translate(127, 77)">
            <circle cx="13" cy="7" r="5" fill="#f8fafc" stroke="#334155" strokeWidth="1" />
            <text x="13" y="10" fontSize="7.5" fontWeight="800" textAnchor="middle" fill="#334155">
              ₹
            </text>
            <rect x="4" y="15" width="2.5" height="10" fill="#334155" rx="0.5" />
            <rect x="8.5" y="17.5" width="2.5" height="7.5" fill="#334155" rx="0.5" />
            <rect x="13" y="20" width="2.5" height="5" fill="#334155" rx="0.5" />
            <rect x="17.5" y="22" width="2.5" height="3" fill="#334155" rx="0.5" />
            <path
              d="M 3 14 L 21 24 M 21 24 L 17 24 M 21 24 L 21 20"
              stroke="#334155"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>
        </svg>
      </div>

      {/* Single-line compact legends */}
      <div className="cost-breakdown-single-line-legends">
        {categories.map(item => (
          <span key={item.name} className="cost-legend-pill">
            <i style={{ backgroundColor: item.color }} />
            <span className="cost-legend-label">{item.name}</span>
            <strong className="cost-legend-value">{currency(item.amount, dash?.currency)}</strong>
            <small className="cost-legend-pct">({item.percent}%)</small>
          </span>
        ))}
      </div>
    </div>
  )
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  R: number,
  startAngleDeg: number,
  endAngleDeg: number
): string {
  const diff = endAngleDeg - startAngleDeg
  const clampedEnd = diff >= 360 ? startAngleDeg + 359.99 : endAngleDeg

  const toRad = (deg: number) => ((deg - 90) * Math.PI) / 180
  const a1 = toRad(startAngleDeg)
  const a2 = toRad(clampedEnd)

  const x1 = cx + R * Math.cos(a1)
  const y1 = cy + R * Math.sin(a1)
  const x2 = cx + R * Math.cos(a2)
  const y2 = cy + R * Math.sin(a2)

  const x3 = cx + r * Math.cos(a2)
  const y3 = cy + r * Math.sin(a2)
  const x4 = cx + r * Math.cos(a1)
  const y4 = cy + r * Math.sin(a1)

  const largeArc = clampedEnd - startAngleDeg > 180 ? 1 : 0

  return `M ${x1} ${y1} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${r} ${r} 0 ${largeArc} 0 ${x4} ${y4} Z`
}
