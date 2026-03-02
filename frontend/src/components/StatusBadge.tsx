const STATUS_COLORS: Record<string, string> = {
  discovered: 'bg-gray-700 text-gray-300',
  message_generated: 'bg-blue-900 text-blue-300',
  approved: 'bg-yellow-900 text-yellow-300',
  sent: 'bg-purple-900 text-purple-300',
  replied: 'bg-green-900 text-green-300',
  meeting: 'bg-emerald-500 text-white',
  rejected: 'bg-red-900 text-red-300',
}

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? 'bg-gray-700 text-gray-300'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {status.replace('_', ' ')}
    </span>
  )
}
