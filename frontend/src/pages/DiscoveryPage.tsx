import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { getApiEndpoint } from '@/config'

interface Asset {
  id: number
  ip_address: string
  mac_address?: string
  hostname?: string
  device_type?: string
  operating_system?: string
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

// Scan history component to show completed scans
function ScanHistory({ scans }: { scans: Scan[] }) {
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

  // Filter completed and failed scans for history
  const completedScans = useMemo(
    () => scans.filter((s) => s.status === 'completed' || s.status === 'failed'),
    [scans]
  )

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
        <ScanHistory scans={completedScans} />
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Discovered Assets ({assets.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-slate-500">
              Loading assets...
            </div>
          ) : assets.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No assets discovered yet. Run a discovery scan to find devices.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-slate-800 text-slate-400">
                  <tr>
                    <th className="px-6 py-3">IP Address</th>
                    <th className="px-6 py-3">MAC Address</th>
                    <th className="px-6 py-3">Hostname</th>
                    <th className="px-6 py-3">Device Type</th>
                    <th className="px-6 py-3">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {assets.map((asset) => (
                    <tr
                      key={asset.id}
                      className="border-b border-slate-800 hover:bg-emerald-900/20 transition-colors cursor-pointer"
                      onClick={() => {
                        localStorage.setItem('selectedAsset', JSON.stringify(asset))
                      }}
                    >
                      <td className="px-6 py-4 font-medium">
                        {asset.ip_address}
                      </td>
                      <td className="px-6 py-4">{asset.mac_address || '-'}</td>
                      <td className="px-6 py-4">{asset.hostname || '-'}</td>
                      <td className="px-6 py-4">{asset.device_type || '-'}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            asset.confidence_level === 'high'
                              ? 'bg-emerald-900 text-emerald-200'
                              : asset.confidence_level === 'medium'
                                ? 'bg-yellow-900 text-yellow-200'
                                : 'bg-slate-700 text-slate-300'
                          }`}
                        >
                          {asset.confidence_level}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Quick Actions</CardTitle>
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
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Scanning in progress...
              </span>
            ) : (
              'Run Discovery Scan'
            )}
          </button>
        </CardContent>
      </Card>
    </div>
  )
}

export default DiscoveryPage
