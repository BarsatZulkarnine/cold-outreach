import { useEffect, useState } from 'react'
import {
  fetchTargets, generateMessage, enrichTarget,
  type Target,
} from '../api/client'
import { StatusBadge } from '../components/StatusBadge'

const STATUS_OPTIONS = [
  '', 'discovered', 'message_generated', 'approved', 'sent', 'replied', 'meeting', 'rejected',
]

export function Targets() {
  const [targets, setTargets] = useState<Target[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  async function load() {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, limit: 20 }
      if (status) params.status = status
      if (source) params.source = source
      const data = await fetchTargets(params)
      setTargets(data.items)
      setTotal(data.total)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, status, source])

  async function handleGenerateMessage(target: Target, channel: 'email' | 'linkedin') {
    setActionLoading(target.id)
    try {
      await generateMessage(target.id, channel)
      await load()
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? 'Failed to generate message')
    } finally {
      setActionLoading(null)
    }
  }

  async function handleEnrich(target: Target) {
    setActionLoading(target.id)
    try {
      const result = await enrichTarget(target.id)
      alert(result.email_found ? `Found: ${result.email_found}` : 'No email found')
      await load()
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? 'Enrichment failed')
    } finally {
      setActionLoading(null)
    }
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Targets <span className="text-gray-500 text-lg">({total})</span></h1>
        <button onClick={load} className="text-sm text-gray-400 hover:text-white border border-gray-700 px-3 py-1 rounded">
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1) }}
          className="bg-gray-900 border border-gray-700 text-sm rounded px-2 py-1 text-gray-300"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s || 'All statuses'}</option>
          ))}
        </select>
        <select
          value={source}
          onChange={(e) => { setSource(e.target.value); setPage(1) }}
          className="bg-gray-900 border border-gray-700 text-sm rounded px-2 py-1 text-gray-300"
        >
          <option value="">All sources</option>
          <option value="google_maps">Google Maps</option>
          <option value="linkedin">LinkedIn</option>
        </select>
      </div>

      {loading ? (
        <div className="text-gray-500 py-8 text-center">Loading...</div>
      ) : (
        <div className="space-y-2">
          {targets.map((t) => (
            <div key={t.id} className="border border-gray-800 rounded-lg overflow-hidden">
              {/* Row */}
              <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-900"
                onClick={() => setExpanded(expanded === t.id ? null : t.id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white truncate">{t.company_name}</span>
                    <StatusBadge status={t.status} />
                    {t.has_open_roles && (
                      <span className="text-xs bg-green-900 text-green-300 px-1.5 py-0.5 rounded">open roles</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5 truncate">
                    {t.contact_name && <span>{t.contact_name} · </span>}
                    {t.contact_title && <span>{t.contact_title} · </span>}
                    {t.company_website && <span>{t.company_website}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1 text-xs shrink-0">
                  {t.contact_email && <span className="text-green-500">📧</span>}
                  {t.linkedin_url && <span className="text-blue-500">💼</span>}
                  <span className="text-gray-600">{t.source === 'google_maps' ? '🗺️' : '🔗'}</span>
                </div>
              </div>

              {/* Expanded */}
              {expanded === t.id && (
                <div className="border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-3">
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
                    {t.contact_email && (
                      <div><span className="text-gray-500">Email: </span>{t.contact_email}</div>
                    )}
                    {t.linkedin_url && (
                      <div><span className="text-gray-500">LinkedIn: </span>
                        <a href={t.linkedin_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                          Profile
                        </a>
                      </div>
                    )}
                    {t.tech_stack?.length > 0 && (
                      <div className="col-span-2">
                        <span className="text-gray-500">Stack: </span>
                        {t.tech_stack.join(', ')}
                      </div>
                    )}
                    {t.notes && (
                      <div className="col-span-2 text-gray-400 text-xs">{t.notes}</div>
                    )}
                  </div>

                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => handleGenerateMessage(t, 'email')}
                      disabled={actionLoading === t.id || !t.contact_email}
                      className="text-xs px-3 py-1.5 bg-purple-900 hover:bg-purple-800 text-white rounded disabled:opacity-40"
                      title={!t.contact_email ? 'No email address' : ''}
                    >
                      Generate Email
                    </button>
                    <button
                      onClick={() => handleGenerateMessage(t, 'linkedin')}
                      disabled={actionLoading === t.id || !t.linkedin_url}
                      className="text-xs px-3 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded disabled:opacity-40"
                      title={!t.linkedin_url ? 'No LinkedIn URL' : ''}
                    >
                      Generate LinkedIn DM
                    </button>
                    {!t.contact_email && t.contact_name && t.company_website && (
                      <button
                        onClick={() => handleEnrich(t)}
                        disabled={actionLoading === t.id}
                        className="text-xs px-3 py-1.5 bg-yellow-900 hover:bg-yellow-800 text-yellow-200 rounded disabled:opacity-40"
                      >
                        Find Email
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex gap-2 justify-center pt-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm border border-gray-700 rounded disabled:opacity-40"
          >
            Prev
          </button>
          <span className="text-gray-500 text-sm px-3 py-1">{page} / {totalPages}</span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 text-sm border border-gray-700 rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
