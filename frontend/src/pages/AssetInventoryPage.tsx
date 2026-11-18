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
  vendor?: string
}

export function AssetInventoryPage() {
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
        <h2 className="text-3xl font-bold tracking-tight">Asset Inventory</h2>
        <p className="text-slate-400">
          Complete inventory of all discovered network assets
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Asset List</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-slate-500">
              Loading assets...
            </div>
          ) : assets.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No assets in inventory. Run discovery to populate.
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
                    <th className="px-6 py-3">OS</th>
                    <th className="px-6 py-3">Vendor</th>
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
                        <Link to="/analysis" onClick={() => {
                          localStorage.setItem('selectedAsset', JSON.stringify(asset))
                        }}>
                          {asset.ip_address}
                        </Link>
                      </td>
                      <td className="px-6 py-4">{asset.mac_address || '-'}</td>
                      <td className="px-6 py-4">{asset.hostname || '-'}</td>
                      <td className="px-6 py-4">{asset.device_type || '-'}</td>
                      <td className="px-6 py-4">{asset.operating_system || '-'}</td>
                      <td className="px-6 py-4">{asset.vendor || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-slate-400">Total Assets</div>
            <div className="text-3xl font-bold text-white">{assets.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-slate-400">Devices Online</div>
            <div className="text-3xl font-bold text-emerald-400">
              {assets.filter((a) => a.hostname).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-slate-400">Known Vendors</div>
            <div className="text-3xl font-bold text-emerald-400">
              {new Set(assets.map((a) => a.vendor).filter(Boolean)).size}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default AssetInventoryPage
