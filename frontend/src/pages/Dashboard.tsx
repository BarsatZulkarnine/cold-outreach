import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { fetchStats, type Stats } from '../api/client'
import { StatsBar } from '../components/StatsBar'

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

  useEffect(() => { load() }, [])

  if (loading) return <div className="text-gray-500 p-8">Loading stats...</div>
  if (!stats) return <div className="text-red-400 p-8">Failed to load stats</div>

  const chartData = STATUS_ORDER
    .filter((s) => stats.by_status[s] !== undefined)
    .map((s) => ({ name: s.replace('_', ' '), value: stats.by_status[s] ?? 0, key: s }))

  return (
    <div className="p-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <button
          onClick={load}
          className="text-sm text-gray-400 hover:text-white border border-gray-700 px-3 py-1 rounded"
        >
          Refresh
        </button>
      </div>

      <StatsBar stats={stats} />

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 text-gray-300">Pipeline</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
              labelStyle={{ color: '#f3f4f6' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.key} fill={BAR_COLORS[entry.key] ?? '#6b7280'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-3 text-gray-300">By Status</h2>
        <div className="space-y-2">
          {STATUS_ORDER.map((s) => (
            <div key={s} className="flex items-center justify-between text-sm">
              <span className="text-gray-400 capitalize">{s.replace('_', ' ')}</span>
              <span className="font-mono text-white">{stats.by_status[s] ?? 0}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
