import type { Stats } from '../api/client'

interface StatsBarProps {
  stats: Stats
}

export function StatsBar({ stats }: StatsBarProps) {
  const items = [
    { label: 'Discovered', value: stats.total_discovered, color: 'text-gray-300' },
    { label: 'Emails Sent', value: stats.emails_sent, color: 'text-purple-400' },
    { label: 'LinkedIn Sent', value: stats.linkedin_sent, color: 'text-blue-400' },
    { label: 'Replied', value: stats.replied, color: 'text-green-400' },
    { label: 'Meetings', value: stats.meetings, color: 'text-emerald-400' },
    {
      label: 'Reply Rate',
      value: `${(stats.reply_rate * 100).toFixed(1)}%`,
      color: 'text-yellow-400',
    },
  ]

  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
      {items.map((item) => (
        <div key={item.label} className="bg-gray-900 rounded-lg p-4 text-center border border-gray-800">
          <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
          <div className="text-xs text-gray-500 mt-1">{item.label}</div>
        </div>
      ))}
    </div>
  )
}
