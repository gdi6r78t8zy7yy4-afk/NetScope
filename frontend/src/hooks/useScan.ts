import { useState, useCallback } from 'react'
import { apiClient } from '@/services/api'

export function useScan() {
  const [scanning, setScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)
  const [scanStatus, setScanStatus] = useState('idle')

  const startScan = useCallback(async (target: string, type: 'discovery' | 'port') => {
    setScanning(true)
    setScanProgress(0)
    setScanStatus('starting')

    try {
      const response = await apiClient.post('/scans', {
        target,
        scan_type: type
      })

      // In real implementation, would establish WebSocket connection
      return response
    } catch (error) {
      setScanStatus('failed')
      throw error
    }
  }, [])

  const cancelScan = useCallback(async (scanId: number) => {
    try {
      await apiClient.post(`/scans/${scanId}/cancel`)
      setScanStatus('cancelled')
    } catch (error) {
      console.error('Failed to cancel scan:', error)
    }
  }, [])

  return {
    scanning,
    scanProgress,
    scanStatus,
    startScan,
    cancelScan
  }
}
