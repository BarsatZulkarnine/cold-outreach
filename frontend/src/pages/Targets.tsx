import { useEffect, useState, useRef } from 'react'
import {
  fetchTargets, generateMessage, enrichTarget,
  type Target,
} from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import { useToast } from '../components/Toast'

const STATUS_OPTIONS = [
  '', 'discovered', 'message_generated', 'approved', 'sent', 'replied', 'meeting', 'rejected',
]

type SortKey = 'company_name' | 'status' | 'has_email' | ''

function Spinner() {
  return (
    <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

export function Targets() {
  const { toast } = useToast()
  const [targets, setTargets] = useState<Target[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('')
  const [sortAsc, setSortAsc] = useState(true)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)
    }, 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [search])

  async function load() {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, limit: 20 }
      if (status) params.status = status
      if (source) params.source = source
      if (debouncedSearch) params.search = debouncedSearch
      const data = await fetchTargets(params)
      setTargets(data.items)
      setTotal(data.total)
    } catch {
      toast('Failed to load targets', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, status, source, debouncedSearch])

  async function handleGenerateMessage(target: Target, channel: 'email' | 'linkedin') {
    setActionLoading(target.id)
    try {
      await generateMessage(target.id, channel)
      toast(`Message generated for ${target.company_name}`, 'success')
      await load()
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? 'Failed to generate message', 'error')
    } finally {
      setActionLoading(null)
    }
  }

  async function handleEnrich(target: Target) {
    setActionLoading(target.id)
    try {
      const result = await enrichTarget(target.id)
      if (result.email_found) {
        toast(`Found: ${result.email_found}`, 'success')
      } else {
        toast('No email found', 'info')
      }
      await load()
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? 'Enrichment failed', 'error')
    } finally {
      setActionLoading(null)
    }
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  const sortedTargets = [...targets].sort((a, b) => {
    if (!sortKey) return 0
    let av: string | number = '', bv: string | number = ''
    if (sortKey === 'company_name') { av = a.company_name.toLowerCase(); bv = b.company_name.toLowerCase() }
    if (sortKey === 'status') { av = a.status; bv = b.status }
    if (sortKey === 'has_email') { av = a.contact_email ? 1 : 0; bv = b.contact_email ? 1 : 0 }
    if (av < bv) return sortAsc ? -1 : 1
    if (av > bv) return sortAsc ? 1 : -1
    return 0
  })

  const totalPages = Math.ceil(total / 20)

  function SortBtn({ label, k }: { label: string; k: SortKey }) {
    const active = sortKey === k
    return (
      <button
        onClick={() => toggleSort(k)}
        className={`text-xs px-2 py-1 rounded transition-colors ${
          active ? 'text-white bg-gray-700' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
        }`}
      >
        {label} {active ? (sortAsc ? '↑' : '↓') : '↕'}
      </button>
    )
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">
          Targets <span className="text-gray-500 text-lg font-normal">({total})</span>
        </h1>
        <button onClick={load} className="text-sm text-gray-400 hover:text-white border border-gray-700 px-3 py-1 rounded transition-colors">
          Refresh
        </button>
      </div>

      {/* Search + filters */}
      <div className="flex flex-wrap gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search company..."
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-gray-500 w-52"
        />
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1) }}
          className="bg-gray-900 border border-gray-700 text-sm rounded px-2 py-1.5 text-gray-300 focus:outline-none"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s || 'All statuses'}</option>
          ))}
        </select>
        <select
          value={source}
          onChange={(e) => { setSource(e.target.value); setPage(1) }}
          className="bg-gray-900 border border-gray-700 text-sm rounded px-2 py-1.5 text-gray-300 focus:outline-none"
        >
          <option value="">All sources</option>
          <option value="google_maps">Google Maps</option>
          <option value="linkedin">LinkedIn</option>
        </select>
      </div>

      {/* Sort controls */}
      <div className="flex items-center gap-1">
        <span className="text-xs text-gray-600 mr-1">Sort:</span>
        <SortBtn label="Company" k="company_name" />
        <SortBtn label="Status" k="status" />
        <SortBtn label="Has Email" k="has_email" />
      </div>

      {loading ? (
        <div className="text-gray-500 py-8 text-center text-sm">Loading...</div>
      ) : sortedTargets.length === 0 ? (
        <div className="py-12 text-center">
          <div className="text-gray-600 text-sm">
            {search || status || source
              ? 'No targets match your filters.'
              : 'No targets yet. Run discovery in Settings.'}
          </div>
        </div>
      ) : (
        <div className="space-y-1.5">
          {sortedTargets.map((t) => (
            <div key={t.id} className="border border-gray-800 rounded-lg overflow-hidden">
              <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-900 transition-colors"
                onClick={() => setExpanded(expanded === t.id ? null : t.id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-white text-sm">{t.company_name}</span>
                    <StatusBadge status={t.status} />
                    {t.has_open_roles && (
                      <span className="text-xs bg-green-900 text-green-300 px-1.5 py-0.5 rounded">open roles</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5 truncate">
                    {t.contact_name && <span>{t.contact_name}</span>}
                    {t.contact_title && <span className="text-gray-600"> · {t.contact_title}</span>}
                    {t.company_website && <span className="text-gray-700"> · {t.company_website}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 text-xs">
                  <span
                    className={t.contact_email ? 'text-green-500' : 'text-gray-800'}
                    title={t.contact_email ? `Email: ${t.contact_email}` : 'No email'}
                  >✉</span>
                  <span
                    className={t.linkedin_url ? 'text-blue-500' : 'text-gray-800'}
                    title={t.linkedin_url ? 'Has LinkedIn' : 'No LinkedIn'}
                  >in</span>
                  <span className="text-gray-700">{t.source === 'google_maps' ? 'Maps' : 'LI'}</span>
                  <span className="text-gray-600">{expanded === t.id ? '▲' : '▼'}</span>
                </div>
              </div>

              {expanded === t.id && (
                <div className="border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-3">
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
                    {t.contact_email && (
                      <div className="col-span-2">
                        <span className="text-gray-600 text-xs">Email </span>
                        <span className="text-gray-300 text-xs">{t.contact_email}</span>
                      </div>
                    )}
                    {t.linkedin_url && (
                      <div>
                        <span className="text-gray-600 text-xs">LinkedIn </span>
                        <a href={t.linkedin_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline text-xs">
                          Profile →
                        </a>
                      </div>
                    )}
                    {t.tech_stack?.length > 0 && (
                      <div className="col-span-2">
                        <span className="text-gray-600 text-xs">Stack </span>
                        <span className="text-gray-400 text-xs">{t.tech_stack.join(', ')}</span>
                      </div>
                    )}
                    {t.notes && (
                      <div className="col-span-2 text-xs text-gray-500 italic">{t.notes}</div>
                    )}
                  </div>

                  <div className="flex gap-2 flex-wrap pt-1">
                    <button
                      onClick={() => handleGenerateMessage(t, 'email')}
                      disabled={actionLoading === t.id || !t.contact_email}
                      className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-purple-900 hover:bg-purple-800 text-white rounded disabled:opacity-40 transition-colors"
                      title={!t.contact_email ? 'No email address' : ''}
                    >
                      {actionLoading === t.id && <Spinner />}
                      Generate Email
                    </button>
                    <button
                      onClick={() => handleGenerateMessage(t, 'linkedin')}
                      disabled={actionLoading === t.id || !t.linkedin_url}
                      className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded disabled:opacity-40 transition-colors"
                      title={!t.linkedin_url ? 'No LinkedIn URL' : ''}
                    >
                      {actionLoading === t.id && <Spinner />}
                      Generate LinkedIn DM
                    </button>
                    {!t.contact_email && t.contact_name && t.company_website && (
                      <button
                        onClick={() => handleEnrich(t)}
                        disabled={actionLoading === t.id}
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-yellow-900 hover:bg-yellow-800 text-yellow-200 rounded disabled:opacity-40 transition-colors"
                      >
                        {actionLoading === t.id && <Spinner />}
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

      {totalPages > 1 && (
        <div className="flex gap-2 justify-center pt-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm border border-gray-700 rounded disabled:opacity-40 hover:border-gray-500 transition-colors"
          >
            Prev
          </button>
          <span className="text-gray-500 text-sm px-3 py-1">{page} / {totalPages}</span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 text-sm border border-gray-700 rounded disabled:opacity-40 hover:border-gray-500 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
