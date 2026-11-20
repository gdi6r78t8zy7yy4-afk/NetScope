import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { getApiEndpoint } from '@/config'

interface Asset {
  id: number
  ip_address: string
  hostname?: string
}

export function PortScannerPage() {
  const [target, setTarget] = useState('')
  const [scanType, setScanType] = useState('common')
  const [rateLimit, setRateLimit] = useState('medium')
  const [assets, setAssets] = useState<Asset[]>([])
  const [loadingAssets, setLoadingAssets] = useState(true)

  useEffect(() => {
    // Check if an asset was selected from Discovery page
    const savedAsset = localStorage.getItem('selectedAsset')
    
    if (savedAsset) {
      try {
        const asset = JSON.parse(savedAsset)
        
        // If it's an existing asset ID, fetch its scan results
        if (asset.id) {
          fetchAssetScanResults(asset.id)
        }
        
        setTarget(asset.ip_address || '')
        localStorage.removeItem('selectedAsset')
      } catch (e) {
        console.error('Failed to parse saved asset:', e)
      }
    }
    
    fetchAssets()
  }, [])

  // Fetch port results when target changes
  useEffect(() => {
    if (target) {
      fetchPortResults()
    }
  }, [target])

  async function fetchAssetScanResults(assetId: number) {
    try {
      // Fetch ports for this asset
      const response = await fetch(getApiEndpoint(`/api/v1/assets/${assetId}/ports`))
      if (response.ok) {
        const data = await response.json()
        console.log('Port scan results:', data)
      }
    } catch (error) {
      console.error('Failed to fetch port scan results:', error)
    }
  }

  async function fetchAssets() {
    try {
      const response = await fetch(getApiEndpoint('/api/v1/assets'))
      if (response.ok) {
        const data = await response.json()
        // Filter out network addresses (.0) and broadcast addresses (.255)
        const discoveredAssets = data.filter((asset: Asset) => {
          const ipParts = asset.ip_address.split('.')
          if (ipParts.length === 4) {
            const lastOctet = parseInt(ipParts[3], 10)
            // Exclude network address (x.x.x.0) and broadcast (x.x.x.255)
            return lastOctet !== 0 && lastOctet !== 255
          }
          return true // Include non-IPv4 addresses as-is
        })
        setAssets(discoveredAssets)
      }
    } catch (error) {
      console.error('Failed to fetch assets:', error)
    } finally {
      setLoadingAssets(false)
    }
  }

  async function fetchPortResults() {
    if (!target) return
    
    try {
      // First, try to get the asset by IP
      const assetResponse = await fetch(getApiEndpoint(`/api/v1/assets/${target}`))
      if (assetResponse.ok) {
        const assetData = await assetResponse.json()
        
        // If we found the asset, try to get its ports
        if (assetData.id) {
          const portsResponse = await fetch(getApiEndpoint(`/api/v1/assets/${assetData.id}/ports`))
          if (portsResponse.ok) {
            const portsData = await portsResponse.json()
            setPortResults(portsData)
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch port results:', error)
    }
  }

  const [portResults, setPortResults] = useState<Record<string, any>[]>([])

  async function startScan() {
    if (!target) {
      alert('Please enter a target IP address or CIDR')
      return
    }

    try {
      const response = await fetch(getApiEndpoint('/api/v1/scans'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `Scan of ${target}`,
          target_cidr: target,
          scan_type: scanType,
          rate_limit: rateLimit
        })
      })

      if (response.ok) {
        const data = await response.json()
        alert(`Scan created with ID: ${data.id}`)
      }
    } catch (error) {
      console.error('Failed to create scan:', error)
      alert('Failed to start scan')
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Port Scanner</h2>
        <p className="text-slate-400">
          Scan network hosts for open ports and services
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Configure Scan</CardTitle>
          <CardDescription>
            Set your scan parameters and start scanning
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium">Target (IP or CIDR)</label>
            <Input
              type="text"
              placeholder="192.168.1.0/24 or 10.0.0.1"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Scan Type</label>
              <select
                value={scanType}
                onChange={(e) => setScanType(e.target.value)}
                className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50 text-slate-100"
              >
                <option value="common">Common Ports</option>
                <option value="full">Full Port Scan (1-65535)</option>
                <option value="top100">Top 100 Ports</option>
                <option value="top1000">Top 1000 Ports</option>
                <option value="custom">Custom Ports</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Rate Limit</label>
              <select
                value={rateLimit}
                onChange={(e) => setRateLimit(e.target.value)}
                className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50 text-slate-100"
              >
                <option value="fastest">Fastest</option>
                <option value="fast">Fast</option>
                <option value="medium">Medium (Default)</option>
                <option value="slow">Slow</option>
                <option value="slower">Slower</option>
              </select>
            </div>
          </div>

          <Button className="w-full" onClick={startScan}>
            Start Scan
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Quick Targets</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchAssets}
                disabled={loadingAssets}
              >
                {loadingAssets ? 'Loading...' : 'Refresh'}
              </Button>
            </div>
            <div className="space-y-2">
              {loadingAssets ? (
                <p className="text-sm text-slate-500">Loading assets...</p>
              ) : assets.length === 0 ? (
                <p className="text-sm text-slate-500">No assets found. Run discovery to populate.</p>
              ) : (
                assets.map((asset) => (
                  <Button
                    key={asset.id}
                    variant="outline"
                    className="w-full justify-start text-xs"
                    onClick={() => setTarget(asset.ip_address)}
                  >
                    {asset.ip_address}
                    {asset.hostname && <span className="ml-2 text-slate-500">({asset.hostname})</span>}
                  </Button>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Port Results */}
        {portResults.length > 0 && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Port Results for {target}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4 mb-6">
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-400">Open Ports</div>
                    <div className="text-2xl font-bold text-emerald-400">
                      {portResults.filter((p: any) => p.state === 'open').length}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-400">Closed Ports</div>
                    <div className="text-2xl font-bold text-red-400">
                      {portResults.filter((p: any) => p.state === 'closed').length}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6">
                    <div className="text-sm text-slate-400">Filtered Ports</div>
                    <div className="text-2xl font-bold text-yellow-400">
                      {portResults.filter((p: any) => p.state === 'filtered').length}
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
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {portResults.map((result: any) => (
                      <tr key={result.id} className="hover:bg-slate-800/50">
                        <td className="px-6 py-4 font-mono">{result.port}</td>
                        <td className="px-6 py-4">{result.protocol}</td>
                        <td className="px-6 py-4">
                          {result.state === 'open' ? (
                            <span className="text-emerald-400">Open</span>
                          ) : result.state === 'closed' ? (
                            <span className="text-red-400">Closed</span>
                          ) : (
                            <span className="text-yellow-400">Filtered</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          {result.service_name || '-'}
                          {result.product && <span className="text-slate-500"> ({result.product})</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default PortScannerPage
