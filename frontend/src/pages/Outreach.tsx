import { useEffect, useState } from 'react'
import { fetchTargets, sendBatch, scheduleEmail, scheduleBatch, type Target, type Message } from '../api/client'
import { MessagePreview } from '../components/MessagePreview'
import { useToast } from '../components/Toast'
import api from '../api/client'

interface MessageWithTarget extends Message {
  company_name: string
  contact_name?: string
}

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

export function Outreach() {
  const { toast } = useToast()
  const [pending, setPending] = useState<MessageWithTarget[]>([])
  const [approved, setApproved] = useState<MessageWithTarget[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [scheduling, setScheduling] = useState(false)
  const [confirmSend, setConfirmSend] = useState(false)
  const [confirmSchedule, setConfirmSchedule] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await fetchTargets({ limit: 100 })
      const allTargets: Target[] = data.items

      const pendingMsgs: MessageWithTarget[] = []
      const approvedMsgs: MessageWithTarget[] = []

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
    } catch {
      toast('Failed to load messages', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleSendAll() {
    if (!approved.length) return
    setSending(true)
    setConfirmSend(false)
    try {
      const result = await sendBatch(approved.map((m) => m.id))
      toast(`Sent: ${result.sent} | Failed: ${result.failed}`, result.failed > 0 ? 'error' : 'success')
      await load()
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? 'Batch send failed', 'error')
    } finally {
      setSending(false)
    }
  }

  async function handleScheduleAll() {
    const emailMsgs = approved.filter((m) => m.channel === 'email' && !m.scheduled_send_at)
    if (!emailMsgs.length) return
    setScheduling(true)
    setConfirmSchedule(false)
    try {
      const result = await scheduleBatch(emailMsgs.map((m) => m.id))
      toast(`Scheduled ${result.scheduled} email(s)`, 'success')
      await load()
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? 'Scheduling failed', 'error')
    } finally {
      setScheduling(false)
    }
  }

  async function handleScheduleOne(msgId: number) {
    try {
      const result = await scheduleEmail(msgId)
      toast(`Scheduled for ${result.scheduled_for_melbourne}`, 'success')
      await load()
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? 'Schedule failed', 'error')
    }
  }

  if (loading) return <div className="text-gray-500 p-8 text-center text-sm">Loading messages...</div>

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold text-white">Outreach</h1>

      {/* Pending approval */}
      <section>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Pending Review <span className="text-gray-600 font-normal normal-case">({pending.length})</span>
        </h2>
        {pending.length === 0 ? (
          <div className="text-gray-700 text-sm py-6 border border-dashed border-gray-800 rounded-lg text-center">
            No messages waiting for review.
          </div>
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
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Approved & Ready <span className="text-gray-600 font-normal normal-case">({approved.length})</span>
          </h2>
          {approved.length > 0 && (
            <div className="flex items-center gap-2">
              {/* Schedule All */}
              {confirmSchedule ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-400">Schedule {approved.filter(m => m.channel === 'email' && !m.scheduled_send_at).length} emails?</span>
                  <button
                    onClick={handleScheduleAll}
                    disabled={scheduling}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-700 hover:bg-blue-600 text-white text-sm rounded font-semibold disabled:opacity-50"
                  >
                    {scheduling && <Spinner />}
                    Yes, schedule
                  </button>
                  <button onClick={() => setConfirmSchedule(false)} className="px-3 py-1.5 text-sm border border-gray-700 rounded text-gray-400 hover:text-white">
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmSchedule(true)}
                  className="px-3 py-1.5 bg-blue-900 hover:bg-blue-800 text-white text-sm rounded font-semibold transition-colors"
                >
                  Schedule All
                </button>
              )}
              {/* Send All Now */}
              {confirmSend ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-400">Send {approved.length} now?</span>
                  <button
                    onClick={handleSendAll}
                    disabled={sending}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-green-700 hover:bg-green-600 text-white text-sm rounded font-semibold disabled:opacity-50"
                  >
                    {sending && <Spinner />}
                    Yes, send
                  </button>
                  <button onClick={() => setConfirmSend(false)} className="px-3 py-1.5 text-sm border border-gray-700 rounded text-gray-400 hover:text-white">
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmSend(true)}
                  className="px-4 py-2 bg-green-800 hover:bg-green-700 text-white text-sm rounded font-semibold transition-colors"
                >
                  Send All Now ({approved.length})
                </button>
              )}
            </div>
          )}
        </div>

        {approved.length === 0 ? (
          <div className="text-gray-700 text-sm py-6 border border-dashed border-gray-800 rounded-lg text-center">
            No approved messages yet. Review pending messages above.
          </div>
        ) : (
          <div className="space-y-2">
            {approved.map((m) => (
              <div key={m.id} className="border border-gray-800 rounded-lg p-4 bg-gray-900">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="font-semibold text-white text-sm">{m.company_name}</span>
                    {m.contact_name && <span className="text-gray-500 ml-2 text-xs">→ {m.contact_name}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    {m.scheduled_send_at && (
                      <span className="text-xs text-blue-400 bg-blue-950 px-2 py-0.5 rounded">
                        ⏰ {new Date(m.scheduled_send_at + 'Z').toLocaleString('en-AU', { weekday: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Australia/Melbourne' })} AEST
                      </span>
                    )}
                    {m.channel === 'email' && !m.scheduled_send_at && (
                      <button
                        onClick={() => handleScheduleOne(m.id)}
                        className="text-xs px-2 py-0.5 bg-blue-900 hover:bg-blue-800 text-blue-200 rounded transition-colors"
                        title="Schedule for optimal send time (Tue–Thu)"
                      >
                        Schedule
                      </button>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded ${m.channel === 'email' ? 'bg-purple-900 text-purple-300' : 'bg-blue-900 text-blue-300'}`}>
                      {m.channel}
                    </span>
                  </div>
                </div>
                {m.subject && <div className="text-xs text-gray-500 mb-1">Subject: {m.subject}</div>}
                <pre className="text-xs text-gray-400 whitespace-pre-wrap bg-gray-950 rounded p-2 max-h-28 overflow-hidden font-mono leading-relaxed">
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
