export function CompletionGauge({ value }: { value: number }) {
  const clampedValue = Math.min(100, Math.max(0, value))
  const circumference = 2 * Math.PI * 38
  const offset = circumference * (1 - clampedValue / 100)

  return (
    <div className="completion-widget">
      <div className="completion-gauge-svg-wrap">
        <svg viewBox="0 0 100 100" className="gauge-svg">
          {/* Outer track */}
          <circle cx="50" cy="50" r="38" className="gauge-track" />
          {/* Progress arc */}
          <circle
            cx="50"
            cy="50"
            r="38"
            className="gauge-progress"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform="rotate(-90 50 50)"
          />
          {/* Inner concentric rings */}
          <circle cx="50" cy="50" r="29" className="gauge-inner-ring" />
          <circle cx="50" cy="50" r="25" className="gauge-inner-disc" />
          {/* Value label */}
          <text x="50" y="52" className="gauge-text">
            {clampedValue}%
          </text>
        </svg>
      </div>
      <div className="completion-widget-meta">
        <strong>{clampedValue}% Completed</strong>
        <small>Based on recorded actual spend vs approved contract value</small>
      </div>
    </div>
  )
}
