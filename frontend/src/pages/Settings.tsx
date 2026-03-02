import { useState, useEffect } from 'react'
import { discoverMaps, discoverLinkedIn, fetchPersona, savePersona, type Persona } from '../api/client'
import { useToast } from '../components/Toast'

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

export function Settings() {
  const { toast } = useToast()

  const [persona, setPersona] = useState<Persona>({
    full_name: '', short_name: '', phone: '', industry: '', background: '', tone_rules: '',
  })
  const [personaLoading, setPersonaLoading] = useState(true)
  const [personaSaving, setPersonaSaving] = useState(false)

  useEffect(() => {
    fetchPersona()
      .then((p) => setPersona(p))
      .catch(() => toast('Could not load persona', 'error'))
      .finally(() => setPersonaLoading(false))
  }, [])

  async function handleSavePersona() {
    if (!persona.full_name.trim() || !persona.short_name.trim()) {
      toast('Full name and sign-off name are required', 'error')
      return
    }
    setPersonaSaving(true)
    try {
      await savePersona(persona)
      toast('Persona saved', 'success')
    } catch {
      toast('Failed to save persona', 'error')
    } finally {
      setPersonaSaving(false)
    }
  }

  const [mapsLoading, setMapsLoading] = useState(false)
  const [linkedinQuery, setLinkedinQuery] = useState('Engineering Manager Melbourne')
  const [linkedinLoading, setLinkedinLoading] = useState(false)

  async function handleRunMaps() {
    if (!confirm('Start Google Maps discovery? This will make API calls.')) return
    setMapsLoading(true)
    try {
      const result = await discoverMaps()
      toast(`Done: ${result.discovered} discovered, ${result.saved} saved to DB`, 'success')
    } catch (e: any) {
      toast('Error: ' + (e?.response?.data?.detail ?? e.message), 'error')
    } finally {
      setMapsLoading(false)
    }
  }

  async function handleRunLinkedIn() {
    if (!linkedinQuery.trim()) return
    if (!confirm(`Start LinkedIn search: "${linkedinQuery}"?\n\nNOTE: This will open a browser window.`)) return
    setLinkedinLoading(true)
    try {
      const result = await discoverLinkedIn(linkedinQuery)
      toast(`Done: ${result.discovered} discovered, ${result.saved} saved to DB`, 'success')
    } catch (e: any) {
      toast('Error: ' + (e?.response?.data?.detail ?? e.message), 'error')
    } finally {
      setLinkedinLoading(false)
    }
  }

  const inputCls = 'w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-gray-500'
  const labelCls = 'block text-xs text-gray-500 mb-1'

  return (
    <div className="p-6 space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* Persona config */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-200">Persona</h2>
          <p className="text-xs text-gray-500 mt-1">
            Used for every generated message. Change this to use the system for a different person.
          </p>
        </div>

        {personaLoading ? (
          <div className="text-gray-600 text-sm">Loading...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>Full Name</label>
                <input
                  className={inputCls}
                  value={persona.full_name}
                  onChange={(e) => setPersona({ ...persona, full_name: e.target.value })}
                  placeholder="Jane Smith"
                />
              </div>
              <div>
                <label className={labelCls}>Sign-off Name</label>
                <input
                  className={inputCls}
                  value={persona.short_name}
                  onChange={(e) => setPersona({ ...persona, short_name: e.target.value })}
                  placeholder="Jane"
                />
              </div>
              <div>
                <label className={labelCls}>Phone</label>
                <input
                  className={inputCls}
                  value={persona.phone}
                  onChange={(e) => setPersona({ ...persona, phone: e.target.value })}
                  placeholder="0400 000 000"
                />
              </div>
              <div>
                <label className={labelCls}>Industry / Role Type</label>
                <input
                  className={inputCls}
                  value={persona.industry}
                  onChange={(e) => setPersona({ ...persona, industry: e.target.value })}
                  placeholder="Investment Banking"
                />
              </div>
            </div>

            <div>
              <label className={labelCls}>Background (bullet points)</label>
              <textarea
                className={`${inputCls} h-32 resize-none`}
                value={persona.background}
                onChange={(e) => setPersona({ ...persona, background: e.target.value })}
              />
            </div>

            <div>
              <label className={labelCls}>Tone Rules</label>
              <textarea
                className={`${inputCls} h-24 resize-none`}
                value={persona.tone_rules}
                onChange={(e) => setPersona({ ...persona, tone_rules: e.target.value })}
              />
            </div>

            <button
              onClick={handleSavePersona}
              disabled={personaSaving}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white text-sm rounded disabled:opacity-50 transition-colors"
            >
              {personaSaving && <Spinner />}
              {personaSaving ? 'Saving...' : 'Save Persona'}
            </button>
          </>
        )}
      </section>

      {/* API Keys info */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-300">API Keys</h2>
        <p className="text-sm text-gray-500">
          Set in <code className="text-yellow-400">.env</code> and restart the backend.
        </p>
        <div className="space-y-1.5 text-sm font-mono">
          <div className="text-gray-400">ANTHROPIC_API_KEY=<span className="text-gray-600">sk-ant-...</span></div>
          <div className="text-gray-400">GOOGLE_MAPS_API_KEY=<span className="text-gray-600">AIza...</span></div>
          <div className="text-gray-400">HUNTER_API_KEY=<span className="text-gray-600">...</span></div>
          <div className="text-gray-400">LINKEDIN_EMAIL=<span className="text-gray-600">your@email.com</span></div>
          <div className="text-gray-400">LINKEDIN_PASSWORD=<span className="text-gray-600">...</span></div>
        </div>
      </section>

      {/* Gmail Auth */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-300">Gmail Auth</h2>
        <p className="text-sm text-gray-500">
          Place <code className="text-yellow-400">credentials.json</code> (Desktop app type from Google Cloud Console)
          in <code className="text-yellow-400">backend/</code>. A browser window opens on first send.
        </p>
        <a
          href="https://console.cloud.google.com/apis/credentials"
          target="_blank"
          rel="noreferrer"
          className="inline-block text-sm text-blue-400 hover:underline"
        >
          Open Google Cloud Console →
        </a>
      </section>

      {/* Discovery */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-4">
        <h2 className="text-lg font-semibold text-gray-300">Run Discovery</h2>

        <div className="space-y-2">
          <div className="text-sm text-gray-400">Google Maps (Melbourne tech companies)</div>
          <button
            onClick={handleRunMaps}
            disabled={mapsLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-800 hover:bg-blue-700 text-white text-sm rounded disabled:opacity-50 transition-colors"
          >
            {mapsLoading && <Spinner />}
            {mapsLoading ? 'Running...' : 'Run Maps Discovery'}
          </button>
        </div>

        <div className="space-y-2">
          <div className="text-sm text-gray-400">LinkedIn search query</div>
          <input
            value={linkedinQuery}
            onChange={(e) => setLinkedinQuery(e.target.value)}
            className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-gray-500"
          />
          <button
            onClick={handleRunLinkedIn}
            disabled={linkedinLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white text-sm rounded disabled:opacity-50 transition-colors"
          >
            {linkedinLoading && <Spinner />}
            {linkedinLoading ? 'Running...' : 'Run LinkedIn Discovery'}
          </button>
        </div>
      </section>

      {/* Daily limits */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-300">Daily Limits</h2>
        <p className="text-xs text-gray-600">Configured in .env</p>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">MAX_EMAILS_PER_DAY</span>
            <span className="text-gray-300 font-mono">40</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">MAX_CONNECTION_REQUESTS_PER_DAY</span>
            <span className="text-gray-300 font-mono">15</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">MAX_DMS_PER_DAY</span>
            <span className="text-gray-300 font-mono">10</span>
          </div>
        </div>
      </section>
    </div>
  )
}
