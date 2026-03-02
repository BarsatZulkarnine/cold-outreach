import { useState } from 'react'
import type { Message } from '../api/client'
import { approveMessage, deleteMessage } from '../api/client'
import { useToast } from './Toast'

interface MessagePreviewProps {
  message: Message
  companyName: string
  contactName?: string
  onApproved: () => void
  onDeleted: () => void
}

function Spinner() {
  return (
    <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

export function MessagePreview({
  message,
  companyName,
  contactName,
  onApproved,
  onDeleted,
}: MessagePreviewProps) {
  const { toast } = useToast()
  const [body, setBody] = useState(message.body)
  const [subject, setSubject] = useState(message.subject ?? '')
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const wordCount = body.trim().split(/\s+/).filter(Boolean).length

  async function handleApprove() {
    setLoading(true)
    try {
      await approveMessage(message.id, body, message.channel === 'email' ? subject : undefined)
      toast(`Approved for ${companyName}`, 'success')
      onApproved()
    } catch {
      toast('Failed to approve message', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete() {
    setLoading(true)
    try {
      await deleteMessage(message.id)
      toast('Message deleted', 'info')
      onDeleted()
    } catch {
      toast('Failed to delete message', 'error')
    } finally {
      setLoading(false)
      setConfirmDelete(false)
    }
  }

  return (
    <div className="border border-gray-800 rounded-lg p-4 space-y-3 bg-gray-900">
      <div className="flex items-center justify-between">
        <div>
          <span className="font-semibold text-white text-sm">{companyName}</span>
          {contactName && <span className="text-gray-500 ml-2 text-xs">→ {contactName}</span>}
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
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-gray-500"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Subject..."
          />
        ) : (
          <div className="text-xs">
            <span className="text-gray-600">Subject: </span>
            <span className="text-gray-300">{subject}</span>
          </div>
        )
      )}

      {editing ? (
        <div className="space-y-1">
          <textarea
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white h-40 resize-none focus:outline-none focus:border-gray-500 font-mono leading-relaxed"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div className={`text-xs text-right ${wordCount > 120 ? 'text-red-400' : 'text-gray-600'}`}>
            {wordCount} words {message.channel === 'email' ? '(limit ~120)' : '(limit ~80)'}
          </div>
        </div>
      ) : (
        <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono bg-gray-950 rounded p-3 leading-relaxed">
          {body}
        </pre>
      )}

      <div className="flex gap-2 items-center">
        <button
          onClick={handleApprove}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-green-800 hover:bg-green-700 text-white text-sm rounded disabled:opacity-50 transition-colors"
        >
          {loading ? <Spinner /> : '✓'}
          Approve
        </button>
        <button
          onClick={() => { setEditing(!editing); setConfirmDelete(false) }}
          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition-colors"
        >
          {editing ? 'Done' : 'Edit'}
        </button>

        {confirmDelete ? (
          <>
            <button
              onClick={handleDelete}
              disabled={loading}
              className="px-3 py-1.5 bg-red-700 hover:bg-red-600 text-white text-sm rounded disabled:opacity-50 transition-colors"
            >
              Really delete?
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="px-3 py-1.5 text-gray-500 hover:text-white text-sm transition-colors"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            disabled={loading}
            className="px-3 py-1.5 text-gray-600 hover:text-red-400 text-sm rounded disabled:opacity-50 transition-colors"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  )
}
