import { useState } from 'react'
import { discoverMaps, discoverLinkedIn } from '../api/client'

export function Settings() {
  const [mapsLoading, setMapsLoading] = useState(false)
  const [mapsResult, setMapsResult] = useState<string>('')
  const [linkedinQuery, setLinkedinQuery] = useState('Engineering Manager Melbourne')
  const [linkedinLoading, setLinkedinLoading] = useState(false)
  const [linkedinResult, setLinkedinResult] = useState<string>('')

  async function handleRunMaps() {
    if (!confirm('Start Google Maps discovery? This will make API calls.')) return
    setMapsLoading(true)
    setMapsResult('')
    try {
      const result = await discoverMaps()
      setMapsResult(`Done: ${result.discovered} discovered, ${result.saved} saved to DB`)
    } catch (e: any) {
      setMapsResult('Error: ' + (e?.response?.data?.detail ?? e.message))
    } finally {
      setMapsLoading(false)
    }
  }

  async function handleRunLinkedIn() {
    if (!linkedinQuery.trim()) return
    if (!confirm(`Start LinkedIn search: "${linkedinQuery}"?\n\nNOTE: This will open a browser window. Make sure you're not already rate-limited.`)) return
    setLinkedinLoading(true)
    setLinkedinResult('')
    try {
      const result = await discoverLinkedIn(linkedinQuery)
      setLinkedinResult(`Done: ${result.discovered} discovered, ${result.saved} saved to DB`)
    } catch (e: any) {
      setLinkedinResult('Error: ' + (e?.response?.data?.detail ?? e.message))
    } finally {
      setLinkedinLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* API Keys info */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-300">API Keys</h2>
        <p className="text-sm text-gray-500">
          Set your API keys in the <code className="text-yellow-400">.env</code> file in the project root.
          Restart the backend after changes.
        </p>
        <div className="space-y-2 text-sm font-mono">
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
          Place your <code className="text-yellow-400">credentials.json</code> (downloaded from Google Cloud Console)
          in the <code className="text-yellow-400">backend/</code> directory.
          On first email send, a browser window will open for OAuth approval.
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

      {/* Discovery triggers */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-4">
        <h2 className="text-lg font-semibold text-gray-300">Run Discovery</h2>

        <div className="space-y-2">
          <div className="text-sm text-gray-400">Google Maps (Melbourne tech companies)</div>
          <button
            onClick={handleRunMaps}
            disabled={mapsLoading}
            className="px-4 py-2 bg-blue-800 hover:bg-blue-700 text-white text-sm rounded disabled:opacity-50"
          >
            {mapsLoading ? 'Running...' : '🗺️ Run Maps Discovery'}
          </button>
          {mapsResult && <div className="text-sm text-green-400">{mapsResult}</div>}
        </div>

        <div className="space-y-2">
          <div className="text-sm text-gray-400">LinkedIn search query</div>
          <input
            value={linkedinQuery}
            onChange={(e) => setLinkedinQuery(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white"
          />
          <button
            onClick={handleRunLinkedIn}
            disabled={linkedinLoading}
            className="px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white text-sm rounded disabled:opacity-50"
          >
            {linkedinLoading ? 'Running...' : '🔗 Run LinkedIn Discovery'}
          </button>
          {linkedinResult && <div className="text-sm text-green-400">{linkedinResult}</div>}
        </div>
      </section>

      {/* Daily limits */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-300">Daily Limits (configured in .env)</h2>
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
