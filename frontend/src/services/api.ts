import { io, Socket } from 'socket.io-client'

interface ImportMetaEnv {
  VITE_API_URL?: string
}

declare const importMeta: { env: ImportMetaEnv }

const API_BASE_URL = importMeta.env.VITE_API_URL || 'http://localhost:3000'

export class ApiClient {
  private socket: Socket | null = null

  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`)
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return response.json() as Promise<T>
  }

  async post<T>(path: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return response.json() as Promise<T>
  }

  connectWebSocket(): Socket {
    if (!this.socket) {
      this.socket = io(API_BASE_URL, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5
      })
    }
    
    return this.socket
  }

  disconnectWebSocket() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }
}

export const apiClient = new ApiClient()
