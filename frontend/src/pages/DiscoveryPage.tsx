import { useState, useEffect, useMemo } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { getApiEndpoint } from '@/config'

interface Asset {
  id: number
  ip_address: string
  mac_address?: string
  hostname?: string
  device_type?: string
  operating_system?: string
  os_version?: string
  vendor?: string
  confidence_level: string
}

interface Scan {
  id: number
  name: string
  scan_type: string
  status: 'pending' | 'running' | 'completed' | 'cancelled' | 'failed'
  progress: number
  target_cidr: string
  created_at?: string
  started_at?: string
  completed_at?: string
  hosts_found?: number
  ports_found?: number
}

// Host Details Panel Component
function HostDetails({ asset }: { asset: Asset }) {
  // Calculate port statistics from real API
  const [stats, setStats] = useState({
    openPorts: 0,
    closedPorts: 0,
    filteredPorts: 0,
    services: 0
  })
  
  const [loadingStats, setLoadingStats] = useState(false)
  
  useEffect(() => {
    const fetchAssetStats = async () => {
      if (!asset.id) return
      
      setLoadingStats(true)
      try {
        const response = await fetch(getApiEndpoint(`/api/v1/assets/${asset.id}/stats`))
        if (response.ok) {
          const data = await response.json()
          setStats({
            openPorts: data.open_ports || 0,
            closedPorts: data.closed_ports || 0,
            filteredPorts: data.filtered_ports || 0,
            services: data.unique_services || 0
          })
        }
      } catch (error) {
        console.error('Failed to fetch asset stats:', error)
      } finally {
        setLoadingStats(false)
      }
    }
    
    fetchAssetStats()
  }, [asset.id])

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold text-slate-100">{asset.ip_address}</h2>
              {asset.hostname && (
                <p className="text-sm text-slate-400 mt-1">Hostname: {asset.hostname}</p>
              )}
            </div>
            <Badge
              variant="outline"
              className={`px-3 py-1 text-sm ${
                asset.confidence_level === 'high'
                  ? 'border-emerald-500 text-emerald-400 bg-emerald-900/20'
                  : asset.confidence_level === 'medium'
                    ? 'border-yellow-500 text-yellow-400 bg-yellow-900/20'
                    : 'border-slate-500 text-slate-400 bg-slate-700/30'
              }`}
            >
              {asset.confidence_level} Confidence
            </Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4">
            <StatCard label="Device Type" value={asset.device_type || 'Unknown'} />
            <StatCard label="OS Detection" value={asset.operating_system || 'N/A'} />
            <StatCard label="Vendor" value={asset.vendor || 'Unknown'} />
            <StatCard
              label="Open Ports"
              value={stats.openPorts > 0 ? `${stats.openPorts} ⚠️` : '0'}
              highlight={stats.openPorts > 0}
            />
          </div>
        </CardContent>
      </Card>

      {/* Stats Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Open Ports"
          value={stats.openPorts.toString()}
          color="emerald"
        />
        <StatCard
          label="Closed Ports"
          value={stats.closedPorts.toString()}
          color="red"
        />
        <StatCard
          label="Filtered Ports"
          value={stats.filteredPorts.toString()}
          color="yellow"
        />
      </div>

      {/* Host Details */}
      <Card>
        <CardHeader>
          <CardTitle>Host Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {asset.mac_address && (
            <div className="flex justify-between py-3 border-b border-slate-800">
              <span className="text-sm text-slate-400">MAC Address</span>
              <span className="font-mono text-sm">{asset.mac_address}</span>
            </div>
          )}
          {asset.operating_system && (
            <div className="flex justify-between py-3 border-b border-slate-800">
              <span className="text-sm text-slate-400">Operating System</span>
              <span className="text-sm">{asset.operating_system}</span>
            </div>
          )}
          {asset.os_version && (
            <div className="flex justify-between py-3 border-b border-slate-800">
              <span className="text-sm text-slate-400">OS Version</span>
              <span className="text-sm">{asset.os_version}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Vulnerabilities Section */}
      <Card>
        <CardHeader>
          <CardTitle>Vulnerabilities</CardTitle>
          <CardDescription>Security assessment results</CardDescription>
        </CardHeader>
        <CardContent>
          {asset.id > 0 ? (
            <div className="text-center py-8">
              <p className="text-slate-500">Vulnerability scan results will appear here</p>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-slate-500">Select a host to view vulnerabilities</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function StatCard({ label, value, color = 'slate', highlight = false }: { label: string; value: string | number; color?: string; highlight?: boolean }) {
  const colorMap: Record<string, string> = {
    emerald: 'text-emerald-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    blue: 'text-blue-400',
    slate: 'text-slate-200'
  }

  const getBorderClass = () => {
    if (!highlight) return ''
    switch (color) {
      case 'emerald':
        return 'bg-emerald-900/20 border-emerald-500'
      case 'red':
        return 'bg-red-900/20 border-red-500'
      case 'yellow':
        return 'bg-yellow-900/20 border-yellow-500'
      default:
        return ''
    }
  }

  return (
    <div className={`p-4 rounded-lg border ${getBorderClass()} bg-slate-800/30`}>
      <div className="text-sm text-slate-400 mb-1">{label}</div>
      <div className={`text-xl font-bold ${colorMap[color] || colorMap.slate}`}>{value}</div>
    </div>
  )
}

// Scan history component to show completed scans
function ScanHistory({ scans, onSelectAsset }: { scans: Scan[], onSelectAsset?: (assetId: number) => void }) {
  console.log('=== ScanHistory Component Render ===', 'scans:', scans.length);
  
  if (scans.length === 0) {
    console.log('=== ScanHistory: No scans to display ===');
    return null
  }

  const getScanDuration = (scan: Scan): string | null => {
    if (!scan.started_at || !scan.completed_at) return null
    const start = new Date(scan.started_at).getTime()
    const end = new Date(scan.completed_at).getTime()
    const durationMs = end - start
    if (durationMs < 1000) return `${Math.round(durationMs)}ms`
    const durationSec = (durationMs / 1000).toFixed(1)
    return `${durationSec}s`
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Scan History ({scans.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs uppercase bg-slate-800 text-slate-400">
              <tr>
                <th className="px-6 py-3">Scan Name</th>
                <th className="px-6 py-3">Type</th>
                <th className="px-6 py-3">Target</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Hosts Found</th>
                <th className="px-6 py-3">Duration</th>
              </tr>
            </thead>
            <tbody>
              {scans.map((scan) => (
                <tr
                  key={scan.id}
                  className="border-b border-slate-800 hover:bg-emerald-900/20 transition-colors"
                >
                  <td className="px-6 py-4 font-medium">{scan.name || 'Unnamed Scan'}</td>
                  <td className="px-6 py-4 capitalize">{scan.scan_type.replace('_', ' ')}</td>
                  <td className="px-6 py-4 font-mono">{scan.target_cidr}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        scan.status === 'completed'
                          ? 'bg-emerald-900 text-emerald-200'
                          : scan.status === 'running'
                            ? 'bg-blue-900 text-blue-200'
                            : scan.status === 'failed'
                              ? 'bg-red-900 text-red-200'
                              : scan.status === 'cancelled'
                                ? 'bg-yellow-900 text-yellow-200'
                                : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {scan.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {scan.hosts_found !== undefined && scan.hosts_found > 0
                      ? <span className="font-semibold text-emerald-400">{scan.hosts_found}</span>
                      : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {scan.started_at && scan.completed_at
                      ? getScanDuration(scan)
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export function DiscoveryPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [scanInProgress, setScanInProgress] = useState(false)
  const [activeScans, setActiveScans] = useState<Scan[]>([])
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  // Filter completed and failed scans for history
  const completedScans = useMemo(
    () => scans.filter((s) => s.status === 'completed' || s.status === 'failed'),
    [scans]
  )

  // Get selected asset
  const selectedAsset = useMemo(
    () => assets.find((a) => a.id === selectedAssetId),
    [assets, selectedAssetId]
  )

  // Filter assets by search term
  const filteredAssets = useMemo(() => {
    if (!searchTerm) return assets
    const lowerSearch = searchTerm.toLowerCase()
    return assets.filter(
      (a) =>
        a.ip_address.toLowerCase().includes(lowerSearch) ||
        (a.hostname && a.hostname.toLowerCase().includes(lowerSearch)) ||
        (a.device_type && a.device_type.toLowerCase().includes(lowerSearch))
    )
  }, [assets, searchTerm])

  useEffect(() => {
    console.log('=== Component Mounted - Loading Data ===')
    fetchAssets()
    fetchAllScans()
  }, [])

  async function fetchAssets() {
    console.log('=== Fetching Assets ===');
    try {
      const response = await fetch(getApiEndpoint('/api/v1/assets'))
      console.log('Fetch assets response status:', response.status);
      
      if (response.ok) {
        const data = await response.json()
        console.log('Assets received:', data.length, 'assets');
        setAssets(data)
      } else {
        console.error('Failed to fetch assets: HTTP', response.status);
      }
    } catch (error) {
      console.error('Failed to fetch assets:', error)
    } finally {
      setLoading(false)
    }
  }

  async function fetchAllScans() {
    console.log('=== Fetching All Scans ===');
    try {
      const response = await fetch(getApiEndpoint('/api/v1/scans'))
      console.log('Fetch scans response status:', response.status);
      
      if (response.ok) {
        const allScans = await response.json()
        console.log('All scans received:', allScans.length, 'scans');
        
        // Store all scans for history (create new array reference to force re-render)
        setScans([...allScans])
        
        // Filter for running or pending scans for active scans section
        const active = allScans.filter((s: Scan) => s.status === 'running' || s.status === 'pending')
        console.log('Active scans (running/pending):', active.length, 'scans');
        
        setActiveScans(active)
        
        // If any scan is still running, keep checking for updates
        if (active.some(s => s.status === 'running')) {
          console.log('Scans are running, setting up polling...')
          setTimeout(fetchAllScans, 2000)
        } else {
          console.log('No scans running, not polling further')
        }
      } else {
        console.error('Failed to fetch scans: HTTP', response.status);
      }
    } catch (error) {
      console.error('Failed to fetch scans:', error)
    }
  }

  async function runDiscoveryScan() {
    console.log('=== Discovery Scan Button Clicked ===');
    setScanInProgress(true)
    try {
      console.log('Step 1: Creating discovery scan...')
      // Create a new scan
      const scanPayload = {
        name: `Discovery Scan ${new Date().toISOString()}`,
        scan_type: 'discovery',
        target_cidr: '192.168.1.0/24',
        rate_limit: 'medium'
      };
      console.log('Scan payload:', scanPayload);
      
      const response = await fetch(getApiEndpoint('/api/v1/scans'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scanPayload)
      });
      
      console.log('Step 1 - Create scan response status:', response.status);
      
      if (response.ok) {
        const scan = await response.json();
        console.log('Step 1 - Discovery scan created:', scan);
        console.log('Scan ID:', scan.id, 'Status:', scan.status);
        
        // Run the newly created scan
        console.log('Step 2: Running scan ID', scan.id, '...')
        const runResponse = await fetch(getApiEndpoint(`/api/v1/scans/${scan.id}/run`), {
          method: 'POST',
        });
        
        console.log('Step 2 - Run scan response status:', runResponse.status);
        
        if (runResponse.ok) {
          const runResult = await runResponse.json();
          console.log('Step 2 - Discovery scan started:', runResult);
          
          // Check if the scan was created with running status or completed
          console.log('Final scan status:', runResult.status);
          
          // Refresh all scans to update both active and history
          await fetchAllScans();
          
          // Also refresh assets since discovery scans create new assets
          setTimeout(() => {
            fetchAssets();
          }, 1000);
        } else {
          const error = await runResponse.json();
          console.error('Step 2 - Failed to start scan:', error);
        }
      } else {
        const error = await response.json();
        console.error('Step 1 - Failed to create scan:', error);
      }
    } catch (error) {
      console.error('Error creating discovery scan:', error);
    } finally {
      console.log('=== Discovery Scan Function Completed ===');
      setScanInProgress(false)
    }
  }

  // Add useEffect to log scan status changes
  useEffect(() => {
    console.log('Active scans updated:', activeScans.length, 'scans');
    activeScans.forEach((scan) => {
      console.log(`  - Scan ${scan.id}: ${scan.name} (${scan.status})`);
    });
  }, [activeScans]);

  // Log scan history updates
  useEffect(() => {
    console.log('Completed scans updated:', completedScans.length, 'scans');
    if (completedScans.length > 0) {
      completedScans.forEach((scan) => {
        console.log(`  - Scan ${scan.id}: ${scan.name} (${scan.status}, hosts: ${scan.hosts_found})`);
      });
    }
  }, [completedScans]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Network Discovery</h2>
        <p className="text-slate-400">
          Discover and monitor devices on your network
        </p>
      </div>

      {/* Active Scans Section */}
      {activeScans.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Active Scans ({activeScans.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeScans.map((scan) => (
              <div key={scan.id} className="bg-slate-800/50 p-4 rounded-lg">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-emerald-400">{scan.name}</span>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    scan.status === 'running' ? 'bg-blue-900 text-blue-200' : 'bg-yellow-900 text-yellow-200'
                  }`}>
                    {scan.status}
                  </span>
                </div>
                
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span>Target: {scan.target_cidr}</span>
                  <span>{scan.progress}%</span>
                </div>
                
                {scan.status === 'running' && (
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${scan.progress}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Scan History Section */}
      {completedScans.length > 0 && (
        <ScanHistory scans={completedScans} onSelectAsset={(assetId) => setSelectedAssetId(assetId)} />
      )}

      {/* Sidebar Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Host List */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="h-[calc(100vh-250px)] lg:h-auto flex flex-col">
            <CardHeader className="pb-3 border-b border-slate-800">
              <CardTitle>Hosts ({filteredAssets.length})</CardTitle>
              <CardDescription>All discovered devices</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto max-h-[600px] lg:max-h-none pr-2 scrollbar-thin">
              {/* Search */}
              <div className="mb-4 space-y-2">
                <Input
                  type="text"
                  placeholder="Search hosts..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="bg-slate-900 border-slate-700 text-slate-100"
                />
              </div>

              {loading ? (
                <div className="text-center py-8 text-slate-500">
                  Loading hosts...
                </div>
              ) : filteredAssets.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  {assets.length === 0
                    ? 'No hosts discovered yet.'
                    : 'No hosts match your search.'}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredAssets.map((asset) => (
                    <div
                      key={asset.id}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedAssetId === asset.id
                          ? 'bg-emerald-900/20 border-emerald-500'
                          : 'bg-slate-800/30 border-slate-700 hover:border-emerald-500'
                      }`}
                      onClick={() => setSelectedAssetId(asset.id)}
                    >
                      <div className="flex justify-between items-start">
                        <span className="font-mono text-sm font-medium text-slate-200">
                          {asset.ip_address}
                        </span>
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            asset.confidence_level === 'high'
                              ? 'border-emerald-500 text-emerald-400 bg-emerald-900/20'
                              : asset.confidence_level === 'medium'
                                ? 'border-yellow-500 text-yellow-400 bg-yellow-900/20'
                                : 'border-slate-500 text-slate-400 bg-slate-700/30'
                          }`}
                        >
                          {asset.confidence_level}
                        </Badge>
                      </div>
                      <div className="text-xs text-slate-400 mt-1 space-y-1">
                        {asset.hostname && <div>Hostname: {asset.hostname}</div>}
                        {asset.device_type && <div>Type: {asset.device_type}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <button
                onClick={(e) => {
                  console.log('=== BUTTON CLICKED EVENT ===', e)
                  runDiscoveryScan()
                }}
                disabled={scanInProgress}
                className={`w-full px-4 py-2 rounded-lg transition-colors ${
                  scanInProgress
                    ? 'bg-emerald-800 text-slate-400 cursor-not-allowed'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                }`}
              >
                {scanInProgress ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg
                      className="animate-spin h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Scanning...
                  </span>
                ) : (
                  'Run Discovery Scan'
                )}
              </button>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Host Details */}
        <div className="lg:col-span-3">
          {selectedAsset ? (
            <HostDetails asset={selectedAsset} />
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-slate-500">
                <div className="inline-block p-4 rounded-full bg-slate-800 mb-4">
                  <svg
                    className="w-12 h-12 text-slate-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-slate-400">Select a Host</h3>
                <p className="text-sm mt-2">Click on a host in the left sidebar to view details</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default DiscoveryPage
