import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { useNavigate } from 'react-router-dom'
import { getApiEndpoint } from '@/config'

// Define asset type
interface Asset {
  id: number
  ip_address: string
}

interface Scan {
  id: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'cancelled' | 'failed'
  progress: number
  target_cidr: string
  scan_type: string
}

export function DashboardPage() {
  const navigate = useNavigate()
  
  // Assets array - used in the JSX for displaying recent discoveries
  const [assets, setAssets] = useState<Asset[]>([])
  const [stats, setStats] = useState({
    totalDevices: 0,
    activeDevices: 0,
    vulnerabilities: 0,
    kevFindings: 0
  })
  const [activeScans, setActiveScans] = useState<Scan[]>([])

  useEffect(() => {
    // Load stats and assets from API
    fetchData()
    const interval = window.setInterval(fetchData, 2000)
    return () => window.clearInterval(interval)
  }, [])

  async function fetchData() {
    try {
      // Fetch assets from API
      const assetsResponse = await fetch(getApiEndpoint('/api/v1/assets'))
      let assetsData: Asset[] = []
      if (assetsResponse.ok) {
        assetsData = await assetsResponse.json()
        setAssets(assetsData)
      }

      // Fetch stats from API
      const [scansResponse, vulnResponse] = await Promise.all([
        fetch(getApiEndpoint('/api/v1/scans')),
        fetch(getApiEndpoint('/api/v1/vulnerabilities'))
      ])

      // Using underscore prefix to indicate unused variable
      let scansData: Scan[] = []
      if (scansResponse.ok) {
        scansData = await scansResponse.json()
        setActiveScans(scansData.filter((scan) =>
          scan.status === 'pending' || scan.status === 'running'
        ))
      } else {
        setActiveScans([])
      }

      let vulnData: { severity?: string }[] = []
      if (vulnResponse.ok) {
        vulnData = await vulnResponse.json()
      }

      // Calculate stats
      setStats({
        totalDevices: assetsData.length,
        activeDevices: assetsData.filter((a: Asset) => a.ip_address).length,
        vulnerabilities: vulnData.length,
        kevFindings: vulnData.filter((v: { severity?: string }) => v.severity === 'critical' || v.severity === 'high').length
      })
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
  }

  const handleScanNetwork = () => {
    navigate('/discovery')
  }

  const handleExportReport = () => {
    alert('Export report functionality coming soon!')
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-slate-400 mt-1">Network Overview</p>
      </div>

      {activeScans.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Active Scans ({activeScans.length})</CardTitle>
            <CardDescription>Scans currently queued or running</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeScans.map((scan) => (
              <button
                key={scan.id}
                type="button"
                className="w-full text-left bg-slate-800/50 p-4 rounded-lg border border-slate-700 hover:border-blue-500/50"
                onClick={() => navigate('/history')}
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-blue-400">{scan.name}</span>
                  <span className="text-xs text-slate-400">{scan.status}</span>
                </div>
                <div className="text-xs text-slate-500 mb-2">
                  {scan.scan_type} · {scan.target_cidr}
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>Progress</span>
                    <span>{scan.progress ?? 0}%</span>
                  </div>
                  <div
                    className="h-2 bg-slate-700 rounded-full overflow-hidden"
                    role="progressbar"
                    aria-label={`Scan progress: ${scan.progress ?? 0}%`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={scan.progress ?? 0}
                  >
                    <div
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${Math.max(0, Math.min(100, scan.progress ?? 0))}%` }}
                    />
                  </div>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card onClick={() => navigate('/assets')} className="cursor-pointer hover:border-emerald-500/50 transition-colors">
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-slate-400">Total Devices</div>
            <div className="text-3xl font-bold">{stats.totalDevices}</div>
          </CardContent>
        </Card>

        <Card onClick={() => navigate('/assets')} className="cursor-pointer hover:border-emerald-500/50 transition-colors">
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-slate-400">Active Devices</div>
            <div className="text-3xl font-bold text-emerald-400">{stats.activeDevices}</div>
          </CardContent>
        </Card>

        <Card onClick={() => navigate('/vulnerabilities')} className="cursor-pointer hover:border-red-500/50 transition-colors">
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-slate-400">Vulnerabilities</div>
            <div className="text-3xl font-bold text-red-400">{stats.vulnerabilities}</div>
          </CardContent>
        </Card>

        <Card onClick={() => navigate('/vulnerabilities')} className="cursor-pointer hover:border-orange-500/50 transition-colors">
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-slate-400">KEV Findings</div>
            <div className="text-3xl font-bold text-orange-500">{stats.kevFindings}</div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common operations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button variant="outline" className="w-full justify-start" onClick={handleScanNetwork}>
              Scan Network
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/vulnerabilities')}>
              Update Vulnerabilities
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={handleExportReport}>
              Export Report
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Discoveries</CardTitle>
            <CardDescription>Last 24 hours</CardDescription>
          </CardHeader>
          <CardContent>
            {assets.length === 0 ? (
              <p className="text-slate-500">No recent discoveries</p>
            ) : (
              <div className="space-y-2">
                {assets.slice(0, 5).map((asset) => (
                  <div 
                    key={asset.id} 
                    className="flex justify-between text-sm hover:bg-slate-800 p-1 rounded cursor-pointer"
                    onClick={() => navigate('/assets')}
                  >
                    <span>{asset.ip_address}</span>
                    <span className="text-emerald-400">New</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardPage
