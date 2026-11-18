import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export function SettingsPage() {
  const [rateLimit, setRateLimit] = useState('medium')

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        <p className="text-slate-400">
          Configure application preferences
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium">Default Rate Limit</label>
            <select
              value={rateLimit}
              onChange={(e) => setRateLimit(e.target.value)}
              className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50 text-slate-100"
            >
              <option value="fastest">Fastest</option>
              <option value="fast">Fast</option>
              <option value="medium" selected>Medium</option>
              <option value="slow">Slow</option>
              <option value="slower">Slower</option>
            </select>
          </div>

          <p className="text-sm text-slate-500">
            Default scan rate limit for new scans.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span>Dark Mode</span>
            <span className="text-emerald-400">Always On</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="text-lg font-semibold">NetScope v1.0.0</div>
          <p className="text-sm text-slate-500">
            Network Discovery & Vulnerability Intelligence
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsPage
