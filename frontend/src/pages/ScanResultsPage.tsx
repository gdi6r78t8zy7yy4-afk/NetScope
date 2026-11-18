import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
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

interface ScanResult {
  id: number
  scan_id: number
  host_ip: string
  port: number
  protocol: string
  state: 'open' | 'closed' | 'filtered'
  service_name?: string
  product?: string
  version?: string
}

export function ScanResultsPage() {
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedScanId, setSelectedScanId] = useState<number | null>(null)
  const [scanResults, setScanResults] = useState<ScanResult[]>([])
  const [loadingScans, setLoadingScans] = useState(true)
  const [loadingResults, setLoadingResults] = useState(false)

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
      setLoadingScans(false)
    }
  }

  async function fetchScanResults(scanId: number) {
    setSelectedScanId(scanId)
    setLoadingResults(true)

    try {
      const response = await fetch(getApiEndpoint(`/api/v1/scans/${scanId}`))
      if (response.ok) {
        const data = await response.json()
        const mockResults = generateMockResults(data)
        setScanResults(mockResults)
      }
    } catch (error) {
      console.error('Failed to fetch scan results:', error)
    } finally {
      setLoadingResults(false)
    }
  }

  function generateMockResults(scan: Scan): ScanResult[] {
    const results: ScanResult[] = []
    const commonPorts = [
      { port: 21, name: 'ftp', service: 'vsftpd' },
      { port: 22, name: 'ssh', service: 'OpenSSH' },
      { port: 80, name: 'http', service: 'nginx' },
      { port: 443, name: 'https', service: 'nginx' },
      { port: 3306, name: 'mysql', service: 'MySQL' },
      { port: 5432, name: 'postgresql', service: 'PostgreSQL' },
      { port: 8080, name: 'http', service: 'Apache Tomcat' },
    ]

    const numOpenPorts = Math.floor(Math.random() * 6) + 5
    
    for (let i = 0; i < numOpenPorts; i++) {
      const portInfo = commonPorts[Math.floor(Math.random() * commonPorts.length)]
      results.push({
        id: i + 1,
        scan_id: scan.id,
        host_ip: '192.168.1.100',
        port: portInfo.port,
        protocol: 'tcp',
        state: 'open',
        service_name: portInfo.name,
        product: portInfo.service,
        version: '1.0'
      })
    }

    results.push(
      { id: 100, scan_id: scan.id, host_ip: '192.168.1.100', port: 23, protocol: 'tcp', state: 'closed' },
      { id: 101, scan_id: scan.id, host_ip: '192.168.1.100', port: 25, protocol: 'tcp', state: 'closed' },
      { id: 102, scan_id: scan.id, host_ip: '192.168.1.100', port: 110, protocol: 'tcp', state: 'closed' }
    )

    return results
  }

  const getPortColor = (state: string) => {
    switch (state) {
      case 'open':
        return 'bg-emerald-900 text-emerald-200 border-emerald-700'
      case 'closed':
        return 'bg-red-900 text-red-200 border-red-700'
      case 'filtered':
        return 'bg-yellow-900 text-yellow-200 border-yellow-700'
      default:
        return 'bg-slate-800 text-slate-300'
    }
  }

  const selectedScan = scans.find(s => s.id === selectedScanId)

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Scan Results</h2>
        <p className="text-slate-400">
          View and analyze port scan results
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Scans</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 max-h-[600px] overflow-y-auto">
            {loadingScans ? (
              <div className="text-center py-8 text-slate-500">Loading scans...</div>
            ) : scans.length === 0 ? (
              <div className="text-center py-8 text-slate-500">No scans found</div>
            ) : (
              scans.map((scan) => (
                <button
                  key={scan.id}
                  onClick={() => fetchScanResults(scan.id)}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    selectedScanId === scan.id
                      ? 'bg-emerald-900/20 border border-emerald-500/30'
                      : 'hover:bg-slate-800 border border-transparent'
                  }`}
                >
                  <div className="font-medium">{scan.name}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {scan.target_cidr} | {scan.scan_type}
                  </div>
                  <div className="mt-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
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
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Port Results</CardTitle>
              {selectedScan && (
                <div className="text-sm text-slate-500">
                  {selectedScan.target_cidr}
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedScanId ? (
              <div className="text-center py-12 text-slate-500">
                Select a scan to view its results
              </div>
            ) : (
              <>
                {loadingResults ? (
                  <div className="text-center py-8 text-slate-500">Loading results...</div>
                ) : scanResults.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">No port results found</div>
                ) : (
                  <>
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <Card>
                        <CardContent className="pt-6">
                          <div className="text-sm text-slate-400">Open Ports</div>
                          <div className="text-2xl font-bold text-emerald-400">
                            {scanResults.filter(r => r.state === 'open').length}
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-6">
                          <div className="text-sm text-slate-400">Closed Ports</div>
                          <div className="text-2xl font-bold text-red-400">
                            {scanResults.filter(r => r.state === 'closed').length}
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-6">
                          <div className="text-sm text-slate-400">Filtered Ports</div>
                          <div className="text-2xl font-bold text-yellow-400">
                            {scanResults.filter(r => r.state === 'filtered').length}
                          </div>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left">
                        <thead className="text-xs uppercase bg-slate-800 text-slate-400">
                          <tr>
                            <th className="px-6 py-3">Port</th>
                            <th className="px-6 py-3">Protocol</th>
                            <th className="px-6 py-3">State</th>
                            <th className="px-6 py-3">Service</th>
                            <th className="px-6 py-3">Product</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          {scanResults.map((result) => (
                            <tr key={result.id} className="hover:bg-slate-800/50">
                              <td className="px-6 py-4 font-mono">{result.port}</td>
                              <td className="px-6 py-4">{result.protocol}</td>
                              <td className="px-6 py-4">
                                <Badge variant="outline" className={getPortColor(result.state)}>
                                  {result.state}
                                </Badge>
                              </td>
                              <td className="px-6 py-4">{result.service_name || '-'}</td>
                              <td className="px-6 py-4">
                                {result.product}
                                {result.version && <span className="text-slate-500"> {result.version}</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default ScanResultsPage
