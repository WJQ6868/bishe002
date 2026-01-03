import { defineStore } from 'pinia'
import axios from 'axios'

interface TableState {
  data: Record<string, any[]>
  loaded: Record<string, boolean>
  loading: boolean
  lastError: string | null
}

export const useTableStore = defineStore('tableStore', {
  state: (): TableState => ({
    data: {},
    loaded: {},
    loading: false,
    lastError: null,
  }),
  actions: {
    async ensureTables(names: string[], force = false) {
      const pending = names.filter((name) => force || !this.loaded[name])
      if (!pending.length) {
        return
      }
      this.loading = true
      try {
        const res = await axios.get('/data/tables', {
          params: { names: pending.join(',') }
        })
        const tables = res.data?.tables || {}
        Object.entries(tables).forEach(([name, rows]) => {
          this.data[name] = Array.isArray(rows) ? rows : []
          this.loaded[name] = true
        })
        this.lastError = null
      } catch (error: any) {
        this.lastError = error?.response?.data?.detail || error?.message || '加载数据失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    getRows<T = any>(name: string): T[] {
      return (this.data[name] as T[]) || []
    },
    invalidate(name?: string) {
      if (name) {
        delete this.loaded[name]
        delete this.data[name]
      } else {
        this.loaded = {}
        this.data = {}
      }
    }
  }
})

