import { create } from 'zustand'

interface Asset {
  id: number
  ip_address: string
  mac_address?: string
  hostname?: string
  device_type?: string
  operating_system?: string
  open_port_count: number
  vulnerability_count: number
}

interface AssetsState {
  assets: Asset[]
  loading: boolean
  error?: string

  fetchAssets: () => Promise<void>
  addAsset: (asset: Asset) => void
  updateAsset: (id: number, updates: Partial<Asset>) => void
  removeAsset: (id: number) => void
}

export const useAssetsStore = create<AssetsState>((set) => ({
  assets: [],
  loading: false,

  fetchAssets: async () => {
    set({ loading: true })
    try {
      const response = await fetch('/api/assets')
      if (response.ok) {
        const data = await response.json()
        set({ assets: data, loading: false })
      }
    } catch (error) {
      set({ error: String(error), loading: false })
    }
  },

  addAsset: (asset) =>
    set((state) => ({
      assets: [...state.assets, asset]
    })),

  updateAsset: (id, updates) =>
    set((state) => ({
      assets: state.assets.map((a) =>
        a.id === id ? { ...a, ...updates } : a
      )
    })),

  removeAsset: (id) =>
    set((state) => ({
      assets: state.assets.filter((a) => a.id !== id)
    }))
}))
