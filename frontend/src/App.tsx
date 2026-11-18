import { Routes, Route } from 'react-router-dom'
import { SidebarLayout } from './components/layout/SidebarLayout'
import { DashboardPage } from './pages/DashboardPage'

// Import all page components
import DiscoveryPage from './pages/DiscoveryPage'
import AssetInventoryPage from './pages/AssetInventoryPage'
import PortScannerPage from './pages/PortScannerPage'
import VulnerabilitiesPage from './pages/VulnerabilitiesPage'
import ScansPage from './pages/ScansPage'
import ScanResultsPage from './pages/ScanResultsPage'
import HostAnalysisPage from './pages/HostAnalysisPage'
import RiskAnalysisPage from './pages/RiskAnalysisPage'
import TopologyPage from './pages/TopologyPage'
import ScanHistoryPage from './pages/ScanHistoryPage'
import SettingsPage from './pages/SettingsPage'

// Import ErrorBoundary
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <SidebarLayout>
        <Routes>
          {/* Dashboard routes */}
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />

          {/* Discovery routes */}
          <Route path="/discovery" element={<DiscoveryPage />} />

          {/* Asset Inventory routes */}
          <Route path="/assets" element={<AssetInventoryPage />} />

          {/* Scanning routes */}
          <Route path="/scanning" element={<PortScannerPage />} />

          {/* Vulnerabilities routes */}
          <Route path="/vulnerabilities" element={<VulnerabilitiesPage />} />

          {/* Scans routes */}
          <Route path="/scans" element={<ScansPage />} />
          <Route path="/scans/:scanId" element={<ScanResultsPage />} />

          {/* Host Analysis routes */}
          <Route path="/analysis" element={<HostAnalysisPage />} />

          {/* Risk Analysis routes */}
          <Route path="/risk" element={<RiskAnalysisPage />} />

          {/* Topology routes */}
          <Route path="/topology" element={<TopologyPage />} />

          {/* Scan History routes */}
          <Route path="/history" element={<ScanHistoryPage />} />

          {/* Settings routes */}
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </SidebarLayout>
    </ErrorBoundary>
  )
}

export default App
