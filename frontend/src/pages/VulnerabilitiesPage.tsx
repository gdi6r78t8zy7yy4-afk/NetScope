import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '../components/ui/card'
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Input } from '../components/ui/input'
import { getApiEndpoint } from '@/config'

interface Vulnerability {
  id: number
  cve_id?: string
  name?: string
  severity?: 'critical' | 'high' | 'medium' | 'low' | string
  description?: string
  affected_assets?: number
  is_kev?: boolean
  epss_score?: number
}

export function VulnerabilitiesPage() {
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredVulnerabilities, setFilteredVulnerabilities] =
    useState<Vulnerability[]>([])
  const [syncStatus, setSyncStatus] = useState<string>('')

  // Fetch vulnerabilities on load
  useEffect(() => {
    fetchVulnerabilities()
    // Try to sync intelligence data on load if no vulns found
  }, [])

  useEffect(() => {
    const filtered = vulnerabilities.filter((vuln) =>
      (vuln.cve_id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (vuln.description || '').toLowerCase().includes(searchQuery.toLowerCase())
    )
    setFilteredVulnerabilities(filtered)
  }, [searchQuery, vulnerabilities])

  async function fetchVulnerabilities() {
    try {
      const response = await fetch(getApiEndpoint('/api/v1/intelligence/status'))
      if (response.ok) {
        const data = await response.json()
        // Check if there are sync records
        const hasSyncData = data.syncs && data.syncs.length > 0
        if (!hasSyncData) {
          setSyncStatus('No sync data found. Attempting initial sync...')
          await triggerIntelligenceSync()
        }
      }
    } catch (error) {
      console.error('Failed to fetch sync status:', error)
    }

    try {
      const response = await fetch(getApiEndpoint('/api/v1/vulnerabilities'))
      if (response.ok) {
        const data = await response.json()
        setVulnerabilities(data)
        setFilteredVulnerabilities(data)
        if (data.length > 0 && !syncStatus) {
          setSyncStatus(`Loaded ${data.length} vulnerabilities`)
        } else if (data.length === 0 && !syncStatus) {
          setSyncStatus('No vulnerabilities found. Try syncing intelligence data.')
        }
      }
    } catch (error) {
      console.error('Failed to fetch vulnerabilities:', error)
      if (!syncStatus) {
        setSyncStatus('Error loading vulnerabilities')
      }
    } finally {
      setLoading(false)
    }
  }

  async function triggerIntelligenceSync() {
    try {
      setSyncing(true)
      const response = await fetch(getApiEndpoint('/api/v1/intelligence/sync'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ sources: ['all'] })
      })
      
      if (response.ok) {
        const data = await response.json()
        setSyncStatus(`Intelligence sync completed: ${JSON.stringify(data.results || data)}`)
        // Refresh vulnerabilities after sync
        await fetchVulnerabilities()
      } else {
        const errorData = await response.json()
        setSyncStatus(`Sync failed: ${errorData.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to sync intelligence:', error)
      setSyncStatus(`Sync failed: ${error.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-red-900 text-red-200'
      case 'high':
        return 'bg-orange-900 text-orange-200'
      case 'medium':
        return 'bg-yellow-900 text-yellow-200'
      case 'low':
        return 'bg-blue-900 text-blue-200'
      default:
        return 'bg-slate-700 text-slate-300'
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Vulnerabilities</h2>
        <p className="text-slate-400">
          Identified security vulnerabilities and CVEs
        </p>
      </div>

      {/* Sync Status Card */}
      <Card className="border-blue-500/30">
        <CardContent className="pt-6">
          <div className={`flex items-center space-x-2 ${syncing ? 'text-blue-400' : 'text-slate-400'}`}>
            {syncing ? (
              <span className="animate-pulse">↻</span>
            ) : (
              <span>ℹ️</span>
            )}
            <span className="text-sm">{syncStatus || 'Ready'}</span>
          </div>
        </CardContent>
      </Card>

      {/* Search and Sync Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-center">
        <Card className="w-full sm:w-auto flex-grow">
          <CardContent className="pt-6">
            <div className="relative">
              <input
                type="text"
                placeholder="Search CVEs or descriptions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </CardContent>
        </Card>
        
        {!loading && vulnerabilities.length === 0 && (
          <button
            onClick={triggerIntelligenceSync}
            disabled={syncing}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              syncing
                ? 'bg-slate-700 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
            {syncing ? 'Syncing...' : 'Sync Intelligence Data'}
          </button>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Critical', color: 'text-red-500' },
          { label: 'High', color: 'text-orange-500' },
          { label: 'Medium', color: 'text-yellow-500' },
          { label: 'Low', color: 'text-blue-500' }
        ].map((item) => (
          <Card key={item.label}>
            <CardContent className="pt-6">
              <div className={`text-sm font-medium ${item.color}`}>{item.label}</div>
              <div className="text-3xl font-bold text-white">
                {filteredVulnerabilities.filter((v) => v.severity?.toLowerCase() === item.label.toLowerCase()).length}
              </div>
            </CardContent>
          </Card>
        ))}

        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-slate-400">Total</div>
            <div className="text-3xl font-bold text-white">
              {filteredVulnerabilities.length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-slate-400">KEV</div>
            <div className="text-3xl font-bold text-orange-500">
              {filteredVulnerabilities.filter((v) => v.is_kev).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-slate-400">EPSS</div>
            <div className="text-3xl font-bold text-green-500">
              {filteredVulnerabilities.filter((v) => v.epss_score !== undefined).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Vulnerability Table */}
      <Card className="overflow-hidden">
        <CardHeader className="pb-3">
          <CardTitle>Vulnerability Findings</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="text-center py-8 text-slate-500">
              Loading vulnerabilities...
            </div>
          ) : filteredVulnerabilities.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              {searchQuery
                ? 'No vulnerabilities match your search.'
                : 'No vulnerabilities found. Click "Sync Intelligence Data" to populate CVEs.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-slate-800 text-slate-400">
                  <tr>
                    <th className="px-6 py-3">Severity</th>
                    <th className="px-6 py-3">CVE ID</th>
                    <th className="px-6 py-3">Description</th>
                    <th className="px-6 py-3 text-center">KEV</th>
                    <th className="px-6 py-3 text-right">EPSS Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredVulnerabilities.map((vuln) => (
                    <tr
                      key={vuln.cve_id || vuln.id}
                      className="hover:bg-slate-800/50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(
                            vuln.severity || 'unknown'
                          )}`}
                        >
                          {vuln.severity || 'unknown'}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs">
                        <Link
                          to={`/vulnerabilities/${vuln.cve_id}`}
                          className="text-blue-400 hover:text-blue-300 hover:underline"
                        >
                          {vuln.cve_id || '-'}
                        </Link>
                      </td>
                      <td className="px-6 py-4 max-w-md truncate" title={vuln.description}>
                        {vuln.description || 'No description available'}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {vuln.is_kev ? (
                          <span className="inline-block px-2 py-1 text-xs font-medium bg-red-900/50 text-red-300 rounded">
                            KEV
                          </span>
                        ) : (
                          <span className="text-slate-600">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {vuln.epss_score !== undefined ? (
                          <span className="text-green-400 font-mono">
                            {vuln.epss_score.toFixed(4)}
                          </span>
                        ) : (
                          <span className="text-slate-600">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default VulnerabilitiesPage
