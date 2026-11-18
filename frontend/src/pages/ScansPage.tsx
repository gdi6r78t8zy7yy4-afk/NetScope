import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Link } from 'react-router-dom'
import { getApiEndpoint } from '@/config'

interface Scan {
  id: number
  name: string
  scan_type: string
  status: 'pending' | 'running' | 'completed' | 'cancelled'
  progress: number
  target_cidr: string
  rate_limit: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchScans()
  }, [])

  async function fetchScans() {
    try {
      const response = await fetch(getApiEndpoint('/api/v1/scans'))
      if (response.ok) {
        const data = await response.json()
        setScans(data)
      }
    } catch (error) {
      console.error('Failed to fetch scans:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-900 text-emerald-200'
      case 'running':
        return 'bg-blue-900 text-blue-200'
      case 'pending':
        return 'bg-yellow-900 text-yellow-200'
      case 'cancelled':
        return 'bg-red-900 text-red-200'
      default:
        return 'bg-slate-700 text-slate-300'
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Scan History</h2>
        <p className="text-slate-400">
          View and manage your scan history
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Recent Scans</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-slate-500">
              Loading scans...
            </div>
          ) : scans.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No scans found. Create a new scan to get started.
            </div>
          ) : (
            <div className="space-y-4">
              {scans.map((scan) => (
                <Link key={scan.id} to={`/scans/${scan.id}`} className="block">
                  <Card className="cursor-pointer hover:border-emerald-500/50 transition-colors">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">{scan.name}</h3>
                          <div className="mt-1 space-y-1 text-sm text-slate-400">
                            <div>Target: {scan.target_cidr}</div>
                            <div>Type: {scan.scan_type} | Rate: {scan.rate_limit}</div>
                          </div>
                        </div>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                            scan.status
                          )}`}
                        >
                          {scan.status}
                        </span>
                      </div>

                      <div className="mt-4 flex items-center gap-2">
                        <span className="text-sm text-slate-500">Progress:</span>
                        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              scan.status === 'completed'
                                ? 'bg-emerald-500'
                                : scan.status === 'running'
                                  ? 'bg-blue-500'
                                  : 'bg-yellow-500'
                            }`}
                            style={{ width: `${scan.progress}%` }}
                          />
                        </div>
                        <span className="text-sm text-slate-500">{scan.progress}%</span>
                      </div>

                      <div className="mt-2 text-xs text-slate-600">
                        Created: {new Date(scan.created_at).toLocaleString()}
                        {scan.started_at && <div>Started: {new Date(scan.started_at).toLocaleString()}</div>}
                        {scan.completed_at && <div>Completed: {new Date(scan.completed_at).toLocaleString()}</div>}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Completed', color: 'text-emerald-500' },
          { label: 'Running', color: 'text-blue-500' },
          { label: 'Pending', color: 'text-yellow-500' },
          { label: 'Cancelled', color: 'text-red-500' }
        ].map((item) => (
          <Card key={item.label}>
            <CardContent className="pt-6">
              <div className={`text-sm font-medium ${item.color}`}>{item.label}</div>
              <div className="text-3xl font-bold text-white">
                {scans.filter((s) => s.status === item.label.toLowerCase()).length}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default ScansPage
