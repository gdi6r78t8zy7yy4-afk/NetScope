import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export function TopologyPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Network Topology</h2>
        <p className="text-slate-400">
          Visualize your network architecture and connections
        </p>
      </div>

      <Card className="min-h-[400px]">
        <CardContent className="pt-6 flex items-center justify-center h-[400px]">
          <div className="text-center space-y-4">
            <svg
              className="w-20 h-20 mx-auto text-slate-700"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <div className="text-lg font-medium">Network Topology Map</div>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              Visual representation of your network infrastructure and device connections
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Devices', value: 0 },
          { label: 'Networks', value: 0 },
          { label: 'Connections', value: 0 },
          { label: 'Subnets', value: 0 }
        ].map((item, i) => (
          <Card key={i}>
            <CardContent className="pt-6">
              <div className="text-sm text-slate-400">{item.label}</div>
              <div className="text-3xl font-bold text-white">{item.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default TopologyPage
