import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Link } from 'react-router-dom'
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

export function DiscoveryPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAssets()
  }, [])

  async function fetchAssets() {
    try {
      const response = await fetch(getApiEndpoint('/api/v1/assets'))
      if (response.ok) {
        const data = await response.json()
        setAssets(data)
      }
    } catch (error) {
      console.error('Failed to fetch assets:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Network Discovery</h2>
        <p className="text-slate-400">
          Discover and monitor devices on your network
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Discovered Assets</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-slate-500">
              Scanning network...
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
                        <Link to="/scanning" onClick={() => {
                          localStorage.setItem('selectedAsset', JSON.stringify(asset))
                        }}>
                          {asset.ip_address}
                        </Link>
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
            onClick={fetchAssets}
            className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
          >
            Run Discovery Scan
          </button>
        </CardContent>
      </Card>
    </div>
  )
}

export default DiscoveryPage
