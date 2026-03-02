import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { fetchStats, type Stats } from '../api/client'
import { StatsBar } from '../components/StatsBar'
import { StatusBadge } from '../components/StatusBadge'

const STATUS_ORDER = [
  'discovered', 'message_generated', 'approved', 'sent', 'replied', 'meeting', 'rejected',
]

const BAR_COLORS: Record<string, string> = {
  discovered: '#6b7280',
  message_generated: '#3b82f6',
  approved: '#eab308',
  sent: '#a855f7',
  replied: '#22c55e',
  meeting: '#10b981',
  rejected: '#ef4444',
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const data = await fetchStats()
      setStats(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const handleFocus = () => load()
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [])

  if (loading) return <div className="text-gray-500 p-8 text-sm">Loading stats...</div>
  if (!stats) return <div className="text-red-400 p-8 text-sm">Failed to load stats. Is the backend running?</div>

  const chartData = STATUS_ORDER
    .filter((s) => (stats.by_status[s] ?? 0) > 0 || s === 'discovered')
    .map((s) => ({
      name: s.replace(/_/g, ' '),
      value: stats.by_status[s] ?? 0,
      key: s,
    }))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <button
          onClick={load}
          className="text-sm text-gray-400 hover:text-white border border-gray-700 px-3 py-1 rounded transition-colors"
        >
          Refresh
        </button>
      </div>

      <StatsBar stats={stats} />

      {/* Pipeline chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-sm font-semibold mb-4 text-gray-400 uppercase tracking-wider">Pipeline</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 30 }}>
            <XAxis
              dataKey="name"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '6px', fontSize: '12px' }}
              labelStyle={{ color: '#f3f4f6' }}
              cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.key} fill={BAR_COLORS[entry.key] ?? '#6b7280'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* By status breakdown */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-sm font-semibold mb-4 text-gray-400 uppercase tracking-wider">By Status</h2>
        <div className="space-y-2">
          {STATUS_ORDER.map((s) => {
            const count = stats.by_status[s] ?? 0
            const total = stats.total_discovered || 1
            const pct = Math.round((count / total) * 100)
            return (
              <div key={s} className="flex items-center gap-3">
                <div className="w-32 shrink-0">
                  <StatusBadge status={s} />
                </div>
                <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full transition-all"
                    style={{ width: `${pct}%`, backgroundColor: BAR_COLORS[s] ?? '#6b7280' }}
                  />
                </div>
                <span className="font-mono text-sm text-white w-8 text-right">{count}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
