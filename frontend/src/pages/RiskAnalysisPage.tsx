import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export function RiskAnalysisPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Risk Analysis</h2>
        <p className="text-slate-400">
          Assess and analyze security risks in your network
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-12 text-slate-500">
            Risk analysis features coming soon
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6 space-y-4">
            <h3 className="text-lg font-semibold">Risk Score Distribution</h3>
            <div className="space-y-2">
              {[
                { label: 'Critical', value: 0, color: 'bg-red-500' },
                { label: 'High', value: 0, color: 'bg-orange-500' },
                { label: 'Medium', value: 0, color: 'bg-yellow-500' },
                { label: 'Low', value: 0, color: 'bg-blue-500' }
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  <span className="w-16 text-sm">{item.label}</span>
                  <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item.color}`}
                      style={{ width: `${(item.value / 10) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm text-slate-400">{item.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 space-y-4">
            <h3 className="text-lg font-semibold">Top Risks</h3>
            <div className="space-y-2 text-sm">
              {[
                'No known vulnerabilities detected',
                'All assets are up to date',
                'Network is properly segmented'
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default RiskAnalysisPage
