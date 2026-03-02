import { useEffect, useState } from 'react'
import { fetchTargets, sendBatch, type Target, type Message } from '../api/client'
import { MessagePreview } from '../components/MessagePreview'
import api from '../api/client'

interface MessageWithTarget extends Message {
  company_name: string
  contact_name?: string
}

export function Outreach() {
  const [pending, setPending] = useState<MessageWithTarget[]>([])
  const [approved, setApproved] = useState<MessageWithTarget[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)

  async function load() {
    setLoading(true)
    try {
      // Fetch all targets and their messages
      const data = await fetchTargets({ limit: 100 })
      const allTargets: Target[] = data.items

      // We need messages with status pending_approval or approved
      // Fetch each target's full detail to get messages
      const pendingMsgs: MessageWithTarget[] = []
      const approvedMsgs: MessageWithTarget[] = []

      // Batch fetch targets with messages
      await Promise.all(
        allTargets
          .filter((t) => ['message_generated', 'approved'].includes(t.status))
          .map(async (t) => {
            try {
              const detail = await api.get(`/targets/${t.id}`).then((r) => r.data)
              for (const m of detail.messages ?? []) {
                const enriched = { ...m, company_name: t.company_name, contact_name: t.contact_name }
                if (m.status === 'pending_approval') pendingMsgs.push(enriched)
                else if (m.status === 'approved') approvedMsgs.push(enriched)
              }
            } catch (e) {
              console.error(e)
            }
          })
      )

      setPending(pendingMsgs)
      setApproved(approvedMsgs)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleSendAll() {
    if (!approved.length) return
    const count = approved.length
    if (!confirm(`Send ${count} approved message${count > 1 ? 's' : ''}?`)) return

    setSending(true)
    try {
      const result = await sendBatch(approved.map((m) => m.id))
      alert(`Sent: ${result.sent} | Failed: ${result.failed}`)
      await load()
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? 'Batch send failed')
    } finally {
      setSending(false)
    }
  }

  if (loading) return <div className="text-gray-500 p-8 text-center">Loading messages...</div>

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold text-white">Outreach</h1>

      {/* Pending approval */}
      <section>
        <h2 className="text-lg font-semibold text-gray-300 mb-3">
          Pending Review <span className="text-gray-500 font-normal">({pending.length})</span>
        </h2>
        {pending.length === 0 ? (
          <div className="text-gray-600 text-sm">No messages waiting for review.</div>
        ) : (
          <div className="space-y-4">
            {pending.map((m) => (
              <MessagePreview
                key={m.id}
                message={m}
                companyName={m.company_name}
                contactName={m.contact_name}
                onApproved={load}
                onDeleted={load}
              />
            ))}
          </div>
        )}
      </section>

      {/* Approved — ready to send */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-300">
            Approved & Ready <span className="text-gray-500 font-normal">({approved.length})</span>
          </h2>
          {approved.length > 0 && (
            <button
              onClick={handleSendAll}
              disabled={sending}
              className="px-4 py-2 bg-green-700 hover:bg-green-600 text-white text-sm rounded font-semibold disabled:opacity-50"
            >
              {sending ? 'Sending...' : `Send All (${approved.length})`}
            </button>
          )}
        </div>

        {approved.length === 0 ? (
          <div className="text-gray-600 text-sm">No approved messages yet.</div>
        ) : (
          <div className="space-y-3">
            {approved.map((m) => (
              <div key={m.id} className="border border-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-white">{m.company_name}</span>
                    {m.contact_name && <span className="text-gray-400 ml-2 text-sm">→ {m.contact_name}</span>}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${m.channel === 'email' ? 'bg-purple-900 text-purple-300' : 'bg-blue-900 text-blue-300'}`}>
                    {m.channel}
                  </span>
                </div>
                {m.subject && <div className="text-sm text-gray-400 mt-1">Subject: {m.subject}</div>}
                <pre className="text-xs text-gray-400 mt-2 whitespace-pre-wrap bg-gray-900 rounded p-2 max-h-32 overflow-hidden">
                  {m.body}
                </pre>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
