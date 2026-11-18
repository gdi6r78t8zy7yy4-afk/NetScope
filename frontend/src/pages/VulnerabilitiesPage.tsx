import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription
} from '../components/ui/card'
import { Input } from '../components/ui/input'
import { getApiEndpoint } from '@/config'

interface Vulnerability {
  id: number
  cve_id?: string
  name?: string
  severity?: 'critical' | 'high' | 'medium' | 'low' | string
  description?: string
  affected_assets?: number
}

export function VulnerabilitiesPage() {
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredVulnerabilities, setFilteredVulnerabilities] =
    useState<Vulnerability[]>([])

  useEffect(() => {
    fetchVulnerabilities()
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
      const response = await fetch(getApiEndpoint('/api/v1/vulnerabilities'))
      if (response.ok) {
        const data = await response.json()
        setVulnerabilities(data)
        setFilteredVulnerabilities(data)
      }
    } catch (error) {
      console.error('Failed to fetch vulnerabilities:', error)
    } finally {
      setLoading(false)
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

      {/* Search Bar */}
      <Card>
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
                : 'No vulnerabilities found. Run vulnerability scans to identify issues.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-slate-800 text-slate-400">
                  <tr>
                    <th className="px-6 py-3">Severity</th>
                    <th className="px-6 py-3">CVE ID</th>
                    <th className="px-6 py-3">Description</th>
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
