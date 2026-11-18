// API Type Definitions

export interface Asset {
  id: number
  ip_address: string
  mac_address?: string
  hostname?: string
  device_type?: string
  operating_system?: string
  os_version?: string
  vendor?: string
  confidence_level: number
}

export interface Scan {
  id: number
  name?: string
  scan_type: string
  status: 'pending' | 'running' | 'completed' | 'cancelled'
  progress: number
  target_cidr: string
}

export interface Vulnerability {
  cve_id: string
  description: string
  cvss_score?: number
  severity?: string
}

export interface RiskFinding {
  cve_id: string
  ip_address: string
  risk_score: number
  priority: 'critical' | 'high' | 'medium' | 'low'
}

export interface DiscoveryResult {
  discovery_method: string
  hosts_found: number
  hosts: Asset[]
}
