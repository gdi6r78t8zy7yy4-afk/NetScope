import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { getApiEndpoint } from '@/config'

type AssetData = Record<string, unknown>

export function HostAnalysisPage() {
  const [ipAddress, setIpAddress] = useState('')
  const [assetData, setAssetData] = useState<AssetData>({})

  useEffect(() => {
    // Check if an asset was selected from Asset List
    const savedAsset = localStorage.getItem('selectedAsset')
    
    if (savedAsset) {
      try {
        const asset = JSON.parse(savedAsset)
        
        // If it has an ID, fetch the full asset details from API
        if (asset.id) {
          fetchAssetDetails(asset.id)
        } else if (asset.ip_address) {
          // Otherwise, try fetching by IP
          fetchAssetByIp(asset.ip_address)
        }
        
        localStorage.removeItem('selectedAsset')
      } catch (e) {
        console.warn('Failed to parse saved asset:', e)
      }
    }
  }, [])

  async function fetchAssetDetails(assetId: number) {
    try {
      const response = await fetch(getApiEndpoint(`/api/v1/assets/${assetId}`))
      if (response.ok) {
        const data = await response.json()
        setIpAddress(data.ip_address)
        setAssetData(data)
        
        // Also fetch port scan results
        const portsResponse = await fetch(getApiEndpoint(`/api/v1/assets/${assetId}/ports`))
        if (portsResponse.ok) {
          const portsData = await portsResponse.json()
          console.warn('Port scan results:', portsData)
        }
        
        // Fetch vulnerability info
        const vulnResponse = await fetch(getApiEndpoint(`/api/v1/assets/${assetId}/vulnerabilities`))
        if (vulnResponse.ok) {
          const vulnData = await vulnResponse.json()
          setVulnerabilityData(vulnData)
        }
      }
    } catch (error) {
      console.error('Failed to fetch asset details:', error)
    }
  }

  const [vulnerabilityData, setVulnerabilityData] = useState<AssetData | null>(null)

  async function fetchAssetByIp(ipAddress: string) {
    try {
      const response = await fetch(getApiEndpoint(`/api/v1/assets/${ipAddress}`))
      if (response.ok) {
        const data = await response.json()
        setIpAddress(data.ip_address)
        setAssetData(data)
      }
    } catch (error) {
      console.error('Failed to fetch asset by IP:', error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Host Analysis</h2>
        <p className="text-slate-400">
          Analyze individual hosts for security issues
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Host Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {assetData.ip_address && (
            <div className="p-4 bg-emerald-900/20 rounded-lg border border-emerald-500/30">
              <div className="text-sm text-slate-400">Selected Host</div>
              <div className="font-mono text-lg">{assetData.ip_address}</div>
              {assetData.hostname && (
                <div className="text-sm text-slate-500">Hostname: {assetData.hostname}</div>
              )}
            </div>
          )}

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter IP address (e.g., 192.168.1.1)"
              className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50 text-slate-100"
              value={ipAddress}
              onChange={(e) => setIpAddress(e.target.value)}
            />
            <button className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors">
              Analyze
            </button>
          </div>

          <p className="text-sm text-slate-500">
            Analyze the selected host for security issues, open ports, and vulnerabilities.
          </p>
        </CardContent>
      </Card>

      {assetData.ip_address && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-slate-400">Device Type</div>
              <div className="text-lg font-bold text-white">{assetData.device_type || 'Unknown'}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-slate-400">Operating System</div>
              <div className="text-lg font-bold text-white">{assetData.operating_system || 'Unknown'}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-slate-400">Vendor</div>
              <div className="text-lg font-bold text-white">{assetData.vendor || 'Unknown'}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Port Scan Results */}
      {assetData.ip_address && (
        <Card>
          <CardHeader>
            <CardTitle>Port Scan Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-500">Open ports for {assetData.ip_address}</p>
            <div className="text-center py-8 text-slate-500">
              Port scan data is populated from the database when available
            </div>
          </CardContent>
        </Card>
      )}

      {/* Vulnerability Results */}
      {assetData.ip_address && (
        <Card>
          <CardHeader>
            <CardTitle>Vulnerability Analysis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-500">Security vulnerabilities for {assetData.ip_address}</p>
            
            {vulnerabilityData ? (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="text-sm text-slate-400">Total Vulnerabilities</div>
                      <div className="text-2xl font-bold text-red-400">
                        {vulnerabilityData.vulnerability_count || 0}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <div className="text-sm text-slate-400">Critical/High (KEV)</div>
                      <div className="text-2xl font-bold text-orange-400">
                        {vulnerabilityData.kev_count || 0}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {vulnerabilityData.vulnerability_count === 0 ? (
                  <p className="text-center py-4 text-emerald-400">No vulnerabilities found for this host</p>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    Vulnerability details available in the database
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                Loading vulnerability data...
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default HostAnalysisPage
