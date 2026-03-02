import { useState } from 'react'
import type { Message } from '../api/client'
import { approveMessage, deleteMessage } from '../api/client'

interface MessagePreviewProps {
  message: Message
  companyName: string
  contactName?: string
  onApproved: () => void
  onDeleted: () => void
}

export function MessagePreview({
  message,
  companyName,
  contactName,
  onApproved,
  onDeleted,
}: MessagePreviewProps) {
  const [body, setBody] = useState(message.body)
  const [subject, setSubject] = useState(message.subject ?? '')
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleApprove() {
    setLoading(true)
    try {
      await approveMessage(message.id, body, message.channel === 'email' ? subject : undefined)
      onApproved()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete() {
    if (!confirm('Delete this message?')) return
    setLoading(true)
    try {
      await deleteMessage(message.id)
      onDeleted()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border border-gray-800 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="font-semibold text-white">{companyName}</span>
          {contactName && <span className="text-gray-400 ml-2">→ {contactName}</span>}
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded ${
            message.channel === 'email'
              ? 'bg-purple-900 text-purple-300'
              : 'bg-blue-900 text-blue-300'
          }`}
        >
          {message.channel}
        </span>
      </div>

      {message.channel === 'email' && (
        editing ? (
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1 text-sm"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        ) : (
          <div className="text-sm text-gray-400">
            <span className="text-gray-500">Subject: </span>{subject}
          </div>
        )
      )}

      {editing ? (
        <textarea
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm h-40 resize-none"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      ) : (
        <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono bg-gray-900 rounded p-3">
          {body}
        </pre>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleApprove}
          disabled={loading}
          className="px-3 py-1.5 bg-green-700 hover:bg-green-600 text-white text-sm rounded disabled:opacity-50"
        >
          ✅ Approve
        </button>
        <button
          onClick={() => setEditing(!editing)}
          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded"
        >
          ✏️ {editing ? 'Done' : 'Edit'}
        </button>
        <button
          onClick={handleDelete}
          disabled={loading}
          className="px-3 py-1.5 bg-red-900 hover:bg-red-700 text-white text-sm rounded disabled:opacity-50"
        >
          ❌ Delete
        </button>
      </div>
    </div>
  )
}
