// Scan-related Type Definitions

export interface ScanOptions {
  target: string
  scanType: 'discovery' | 'portScan' | 'vulnerability'
  rateLimit?: string
  ports?: number[]
}

export interface ScanProgress {
  scanId: number
  progress: number
  status: string
  message?: string
}

export interface ScanResult {
  scanId: number
  status: 'completed' | 'failed' | 'cancelled'
  findings?: any[]
}
