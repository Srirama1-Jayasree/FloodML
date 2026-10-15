import { useEffect, useState } from 'react'
import './App.css'

const defaultLocation = 'Hyderabad'
const chartWidth = 720
const chartHeight = 250
const chartMargin = { top: 18, right: 20, bottom: 42, left: 48 }

const riskClassMap = {
  LOW: 'status-low',
  MODERATE: 'status-moderate',
  HIGH: 'status-high',
  CRITICAL: 'status-critical',
  'Data unavailable': 'status-unavailable',
}

function App() {
  const [location, setLocation] = useState(defaultLocation)
  const [dashboard, setDashboard] = useState(null)
  const [history, setHistory] = useState([])
  const [forecast, setForecast] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchDashboard = async (nextLocation = location) => {
    try {
      const predictRes = await fetch(`/api/predict?location=${encodeURIComponent(nextLocation)}`)
      if (!predictRes.ok) {
        throw new Error(`Prediction request failed (HTTP ${predictRes.status}).`)
      }
      const prediction = await predictRes.json()
      const [historyRes, forecastRes] = await Promise.all([
        fetch(`/api/history?location=${encodeURIComponent(nextLocation)}`),
        fetch(`/api/forecast?location=${encodeURIComponent(nextLocation)}`),
      ])
      if (!historyRes.ok || !forecastRes.ok) {
        throw new Error('Unable to load historical or forecast data.')
      }

      const historyPayload = await historyRes.json()
      const forecastPayload = await forecastRes.json()

      setDashboard(prediction)
      setHistory(historyPayload.history || [])

      const projections = forecastPayload?.projection?.projections || {}
      const combined = [
        ...(projections['24h'] || []),
        ...(projections['48h'] || []),
        ...(projections['72h'] || []),
      ]
      setForecast(combined.slice(0, 5))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Live dashboard data is temporarily unavailable.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard(defaultLocation)
  }, [])

  const data = dashboard?.data || {}
  const weather = data.weather || {}
  const water = data.water_management || {}
  const riskLevel = data.risk_level || 'Data unavailable'
  const probability = data.probability ?? 'Data unavailable'
  const chartPoints = history.slice(-12).map((row, index, rows) => {
    const plotWidth = chartWidth - chartMargin.left - chartMargin.right
    const plotHeight = chartHeight - chartMargin.top - chartMargin.bottom
    const value = Math.max(0, Math.min(100, Number(row.probability) || 0))
    const x = rows.length === 1
      ? chartMargin.left + plotWidth / 2
      : chartMargin.left + (index / (rows.length - 1)) * plotWidth
    const y = chartMargin.top + ((100 - value) / 100) * plotHeight
    return { ...row, value, x, y }
  })
  const chartLine = chartPoints.map((point) => `${point.x},${point.y}`).join(' ')

  const formatHistoryTime = (value) => {
    const timestamp = new Date(value.replace(/ UTC$/, 'Z'))
    return Number.isNaN(timestamp.getTime())
      ? value
      : timestamp.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    fetchDashboard(location)
  }

  return (
    <div className="app-shell">
      <header className="topbar container">
        <div className="brand">AquaSentinel AI</div>
        <div className="badge">{loading ? 'Loading…' : 'Live monitoring'}</div>
      </header>

      <main className="container dashboard">
        <section className="hero-grid">
          <div className="card main-card">
            <div className="eyebrow">Flood risk overview</div>
            <div className="headline-row">
              <h1>{dashboard?.location || location}</h1>
              <span className={`status-pill ${riskClassMap[riskLevel] || 'status-unavailable'}`}>
                {riskLevel}
              </span>
            </div>

            <p className="summary-text">
              {weather.message || weather.condition || 'Weather summary unavailable.'}
            </p>

            <form onSubmit={handleSubmit} className="search-row">
              <input
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="Enter a city"
              />
              <button type="submit">Refresh</button>
            </form>

            <div className="footnote">
              <strong>Recommended Action:</strong> {water.recommended_action || 'Recommended Action'}
              <br />
              {water.confirmation_required || 'Requires human/operator confirmation.'}
            </div>
          </div>

        </section>

        <section className="stats-grid">
          <div className="card metric-card">
            <div className="label">Probability</div>
            <div className="metric-value">{probability === 'Data unavailable' ? 'Data unavailable' : `${probability}%`}</div>
          </div>

          <div className="card metric-card">
            <div className="label">Water status</div>
            <div className="metric-value">{water.status || 'Data unavailable'}</div>
          </div>

          <div className="card metric-card">
            <div className="label">Temperature</div>
            <div className="metric-value">{weather.temperature ?? 'Data unavailable'}</div>
          </div>

          <div className="card metric-card">
            <div className="label">
              Rainfall (past {weather.rainfall_period_hours || 1} {Number(weather.rainfall_period_hours || 1) === 1 ? 'hour' : 'hours'})
            </div>
            <div className="metric-value">
              {weather.status === 'ok' && weather.rainfall != null
                ? `${Number(weather.rainfall).toFixed(1)} mm`
                : 'Data unavailable'}
            </div>
            {weather.status === 'ok' && (
              <div className="rainfall-note">
                {Number(weather.rainfall) === 0
                  ? 'No measurable precipitation reported for this period.'
                  : 'Precipitation reported for this period.'}
              </div>
            )}
          </div>
        </section>

        <section className="detail-grid">
          <div className="card chart-card">
            <div className="label">Historic risk trend · {dashboard?.location || location}</div>
            <div className="chart-container">
              {chartPoints.length ? (
                <svg
                  className="history-chart"
                  viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                  role="img"
                  aria-label={`Historical flood risk percentages for ${dashboard?.location || location}`}
                >
                  {[0, 50, 100].map((tick) => {
                    const y = chartMargin.top + ((100 - tick) / 100) * (chartHeight - chartMargin.top - chartMargin.bottom)
                    return (
                      <g key={tick}>
                        <line x1={chartMargin.left} y1={y} x2={chartWidth - chartMargin.right} y2={y} className="chart-gridline" />
                        <text x={chartMargin.left - 10} y={y + 4} textAnchor="end" className="chart-axis-label">{tick}%</text>
                      </g>
                    )
                  })}
                  {chartPoints.length > 1 && <polyline points={chartLine} className="chart-line" />}
                  {chartPoints.map((point) => (
                    <circle key={point.id} cx={point.x} cy={point.y} r="5" className="chart-point">
                      <title>{`${point.value.toFixed(2)}% · ${formatHistoryTime(point.created_at)}`}</title>
                    </circle>
                  ))}
                  {[chartPoints[0], chartPoints[Math.floor((chartPoints.length - 1) / 2)], chartPoints[chartPoints.length - 1]]
                    .filter((point, index, points) => points.findIndex((candidate) => candidate.id === point.id) === index)
                    .map((point, index, points) => (
                      <text
                        key={`${point.id}-time`}
                        x={point.x}
                        y={chartHeight - 12}
                        textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
                        className="chart-axis-label"
                      >
                        {formatHistoryTime(point.created_at)}
                      </text>
                    ))}
                </svg>
              ) : (
                <div className="empty-state">No saved prediction history for this location yet.</div>
              )}
            </div>
          </div>

          <div className="card forecast-card">
            <div className="label">Forecast outlook</div>
            <ul>
              {forecast.length ? (
                forecast.map((item, index) => (
                  <li key={`${item.timestamp || index}`}>
                    <strong>{item.timestamp ? new Date(item.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric' }) : 'Forecast'}</strong>
                    <span> — {item.risk_level || 'LOW'} ({item.probability ?? 'n/a'}%)</span>
                  </li>
                ))
              ) : (
                <li>Forecast data unavailable.</li>
              )}
            </ul>
          </div>
        </section>

        <section className="detail-grid lower-grid">
          <div className="card guidance-card">
            <div className="label">Alert guidance</div>
            <ul>
              {(water.actions && water.actions.length ? water.actions : ['Continue normal monitoring.']).map((action, index) => (
                <li key={`${action}-${index}`}>{action}</li>
              ))}
            </ul>
          </div>

          <div className="card alerts-card">
            <div className="label">Recent alerts</div>
            <ul>
              {(data.alert ? [data.alert] : []).concat(history.slice(0, 4)).length ? (
                (data.alert ? [data.alert] : []).concat(history.slice(0, 4)).map((item, index) => (
                  <li key={`${item.title || 'alert'}-${index}`}>
                    {item.title || 'Alert'} — {item.risk_level || riskLevel}
                  </li>
                ))
              ) : (
                <li>No alerts logged yet.</li>
              )}
            </ul>
          </div>
        </section>

        {error && <div className="error-banner">{error}</div>}
      </main>
    </div>
  )
}

export default App
