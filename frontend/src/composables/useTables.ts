import { onMounted, ref } from 'vue'
import { useTableStore } from '@/stores/tableStore'

export const useTables = (requiredTables: string[]) => {
  const tableStore = useTableStore()
  const loading = ref(false)
  const error = ref<string | null>(null)

  const load = async (force = false) => {
    loading.value = true
    try {
      await tableStore.ensureTables(requiredTables, force)
      error.value = null
    } catch (err: any) {
      error.value = err?.response?.data?.detail || err?.message || '¼ÓÔØÊý¾ÝÊ§°Ü'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    load()
  })

  return {
    tableStore,
    loading,
    error,
    reloadTables: load,
    rows: <T = any>(name: string) => tableStore.getRows<T>(name),
  }
}
