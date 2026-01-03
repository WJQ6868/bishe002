<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'
import axios from 'axios'

interface AdjustRecord {
  id: number
  teacher_id: number
  teacher_name: string
  course_id: number
  course_name: string
  old_time: string
  new_time: string
  old_classroom?: string
  new_classroom?: string
  reason: string
  status: string
  create_time: string
}

const records = ref<AdjustRecord[]>([])
const loading = ref(false)
const activeTab = ref<'pending' | 'all'>('pending')

const STATUS_TEXT = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}

const statusParams = () =>
  activeTab.value === 'pending' ? { status: STATUS_TEXT.pending } : undefined

const loadRecords = async () => {
  loading.value = true
  try {
    const res = await axios.get<AdjustRecord[]>('/work/adjust/list', {
      params: statusParams()
    })
    records.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(loadRecords)
watch(activeTab, loadRecords)

const handleApprove = (record: AdjustRecord, result: 'approved' | 'rejected') => {
  const actionText = result === 'approved' ? '通过' : '驳回'
  ElMessageBox.confirm(`确认要${actionText}该条调课申请吗？`, '提示', {
    type: result === 'approved' ? 'success' : 'warning'
  }).then(async () => {
    try {
      await axios.post('/work/adjust/approve', null, {
        params: { adjust_id: record.id, result }
      })
      ElMessage.success('审批成功')
      await loadRecords()
    } catch (error: any) {
      const msg = error?.response?.data?.detail || '审批失败'
      ElMessage.error(msg)
    }
  })
}

const formatTime = (iso: string) =>
  new Date(iso).toLocaleString('zh-CN', { hour12: false })

const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    [STATUS_TEXT.pending]: 'warning',
    [STATUS_TEXT.approved]: 'success',
    [STATUS_TEXT.rejected]: 'danger'
  }
  return map[status] || 'info'
}
</script>

<template>
  <div class="adjust-container">
    <div class="header-bar">
      <h3>调课审批管理</h3>
      <el-radio-group v-model="activeTab">
        <el-radio-button label="pending">待审核</el-radio-button>
        <el-radio-button label="all">全部记录</el-radio-button>
      </el-radio-group>
    </div>

    <el-table :data="records" v-loading="loading" style="width: 100%">
      <el-table-column prop="teacher_name" label="申请教师" width="120" />
      <el-table-column prop="course_name" label="课程名称" width="150" />
      <el-table-column label="原定时间/地点" width="240">
        <template #default="{ row }">
          <div>{{ formatTime(row.old_time) }}</div>
          <small>{{ row.old_classroom || '未指定' }}</small>
        </template>
      </el-table-column>
      <el-table-column label="拟改时间/地点" width="240">
        <template #default="{ row }">
          <div style="color: #409EFF">{{ formatTime(row.new_time) }}</div>
          <small>{{ row.new_classroom || '未指定' }}</small>
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="调课理由" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="getStatusTag(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <div v-if="row.status === STATUS_TEXT.pending">
            <el-button
              type="success"
              :icon="Check"
              circle
              size="small"
              @click="handleApprove(row, 'approved')"
            />
            <el-button
              type="danger"
              :icon="Close"
              circle
              size="small"
              @click="handleApprove(row, 'rejected')"
            />
          </div>
          <span v-else class="done-text">已处理</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.adjust-container {
  padding: 20px;
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.header-bar h3 {
  margin: 0;
  color: var(--el-text-color-primary);
}

.done-text {
  color: #909399;
  font-size: 12px;
}
</style>
