import type { Stats } from '../api/client'

interface StatsBarProps {
  stats: Stats
}

export function StatsBar({ stats }: StatsBarProps) {
  const items = [
    { label: 'Discovered', value: stats.total_discovered, color: 'text-gray-300', icon: '📥' },
    { label: 'Emails Sent', value: stats.emails_sent, color: 'text-purple-400', icon: '📧' },
    { label: 'LinkedIn Sent', value: stats.linkedin_sent, color: 'text-blue-400', icon: '💼' },
    { label: 'Replied', value: stats.replied, color: 'text-green-400', icon: '💬' },
    { label: 'Meetings', value: stats.meetings, color: 'text-emerald-400', icon: '🤝' },
    {
      label: 'Reply Rate',
      value: `${(stats.reply_rate * 100).toFixed(1)}%`,
      color: 'text-yellow-400',
      icon: '📊',
    },
  ]

  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
      {items.map((item) => (
        <div key={item.label} className="bg-gray-900 rounded-lg p-4 text-center border border-gray-800 hover:border-gray-700 transition-colors">
          <div className="text-lg mb-1">{item.icon}</div>
          <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
          <div className="text-xs text-gray-600 mt-1">{item.label}</div>
        </div>
      ))}
    </div>
  )
}
