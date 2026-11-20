import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { getApiEndpoint } from '@/config'

interface Scan {
  id: number
  name: string
  scan_type: string
  status: 'pending' | 'running' | 'completed' | 'cancelled'
  progress: number
  target_cidr: string
  created_at?: string
  started_at?: string
  completed_at?: string
}

export function ScanHistoryPage() {
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchScans()
  }, [])

  async function fetchScans() {
    console.log('=== Fetching Scan History ===');
    try {
      const response = await fetch(getApiEndpoint('/api/v1/scans'))
      console.log('Fetch scans response status:', response.status);
      
      if (response.ok) {
        const data = await response.json()
        console.log('All scans received:', data.length, 'scans');
        setScans(data)
      } else {
        console.error('Failed to fetch scans: HTTP', response.status);
      }
    } catch (error) {
      console.error('Failed to fetch scans:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Scan History</h2>
        <p className="text-slate-400">
          Complete history of all scans performed
        </p>
      </div>

      <Card className="max-w-4xl mx-auto">
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-slate-500">
              Loading scan history...
            </div>
          ) : scans.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No scan history available
            </div>
          ) : (
            <div className="space-y-4">
              {scans.map((scan) => (
                <Card key={scan.id}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold">{scan.name}</h3>
                        <div className="mt-1 text-sm text-slate-400">
                          Target: {scan.target_cidr} | Type: {scan.scan_type}
                        </div>
                      </div>
                      <div className="text-right">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            scan.status === 'completed'
                              ? 'bg-emerald-900 text-emerald-200'
                              : scan.status === 'running'
                                ? 'bg-blue-900 text-blue-200'
                                : scan.status === 'pending'
                                  ? 'bg-yellow-900 text-yellow-200'
                                  : 'bg-red-900 text-red-200'
                          }`}
                        >
                          {scan.status}
                        </span>
                      </div>
                    </div>

                    <div className="mt-4">
                      <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                        <span>Progress</span>
                        <span>{scan.progress}%</span>
                      </div>
                      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
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
                    </div>

                    <div className="mt-2 text-xs text-slate-600">
                      Created: {new Date(scan.created_at).toLocaleString()}
                      {scan.started_at && <div>Started: {new Date(scan.started_at).toLocaleString()}</div>}
                      {scan.completed_at && <div>Completed: {new Date(scan.completed_at).toLocaleString()}</div>}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ScanHistoryPage
