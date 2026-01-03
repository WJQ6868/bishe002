<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Check, Close, Timer, DataLine, User, Calendar } from '@element-plus/icons-vue'
import { useTables } from '@/composables/useTables'
import axios from 'axios'

// --- 1. 类型定义 ---
type AuditStatus = 'pending' | 'approved' | 'rejected'
type ResourceType = 'classroom' | 'lab'

interface Reservation {
  id: number
  resourceName: string
  type: ResourceType
  applicant: string
  phone: string
  date: string
  timeSlots: string[]
  purpose: string
  submitTime: string
  status: AuditStatus
}

interface ReservationAudit extends Reservation {
  auditor?: string
  auditTime?: string
  rejectReason?: string
}

interface ResourceUtilization {
  resourceName: string
  type: ResourceType
  reservationCount: number
  utilizationRate: number
}

// --- 2. 数据源 ---
const { rows, loading: tableLoading, error: tableError, reloadTables } = useTables([
  'service_apply',
  'service_item',
  'sys_users',
  'user_profiles'
])

const serviceItemMap = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  rows('service_item').forEach((item: any) => {
    map[item.id] = item
  })
  return map
})

const sysUserMap = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  rows('sys_users').forEach((user: any) => {
    map[user.id] = user
  })
  return map
})

const profileMap = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  rows('user_profiles').forEach((profile: any) => {
    map[profile.user_id] = profile
  })
  return map
})

const parseFormData = (raw: any) => {
  if (typeof raw === 'object' && raw !== null) return raw
  if (!raw) return {}
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

const normalizeStatus = (status: string): AuditStatus => {
  if (status === 'approved' || status === 'completed') return 'approved'
  if (status === 'rejected') return 'rejected'
  return 'pending'
}

const reservations = computed<ReservationAudit[]>(() => {
  return rows('service_apply').map((apply: any) => {
    const formData = parseFormData(apply.form_data)
    const serviceItem = serviceItemMap.value[apply.item_id]
    const applicantProfile = profileMap.value[apply.applicant_id]
    const applicantUser = sysUserMap.value[apply.applicant_id]
    const auditorProfile = apply.approver_id ? profileMap.value[apply.approver_id] : null
    const auditorUser = apply.approver_id ? sysUserMap.value[apply.approver_id] : null

    const derivedDate = formData.date || formData.schedule || (apply.submit_time?.split(' ')?.[0] ?? '')
    const timeSlots = Array.isArray(formData.timeSlots)
      ? formData.timeSlots
      : formData.time_slot
        ? [formData.time_slot]
        : []

    return {
      id: apply.id,
      resourceName: serviceItem?.name || `服务 ${apply.item_id}`,
      type: serviceItem?.category?.includes('实验') ? 'lab' : 'classroom',
      applicant: applicantProfile?.name || applicantUser?.username || `用户${apply.applicant_id}`,
      phone: formData.phone || formData.contact || '',
      date: derivedDate,
      timeSlots,
      purpose: formData.purpose || formData.reason || serviceItem?.category || '',
      submitTime: apply.submit_time,
      status: normalizeStatus(apply.status || 'pending'),
      auditor: auditorProfile?.name || auditorUser?.username,
      auditTime: apply.approve_time,
      rejectReason: apply.opinion || undefined
    }
  })
})

// --- 3. 状态管理 ---
const activeTab = ref<'pending' | 'processed'>('pending')
const searchQuery = reactive({
  keyword: '', // 资源类型/申请人
  date: '',
  status: '' // 仅用于已审核列表筛选通过/拒绝
})
const dialogVisible = ref(false)
const currentReservation = ref<ReservationAudit | null>(null)
const rejectReason = ref('')
const selectedRows = ref<ReservationAudit[]>([])
const approving = ref(false)

// --- 4. 计算属性 ---

// 列表数据
const tableData = computed(() => {
  let data = reservations.value.filter(item => {
    if (activeTab.value === 'pending') return item.status === 'pending'
    return item.status !== 'pending'
  })

  // 筛选
  if (searchQuery.keyword) {
    const kw = searchQuery.keyword.toLowerCase()
    data = data.filter(item => 
      item.resourceName.includes(kw) || 
      item.applicant.includes(kw) ||
      (item.type === 'classroom' ? '教室' : '实验室').includes(kw)
    )
  }
  if (searchQuery.date) {
    data = data.filter(item => item.date === searchQuery.date)
  }
  if (activeTab.value === 'processed' && searchQuery.status) {
    data = data.filter(item => item.status === searchQuery.status)
  }

  return data
})

// 统计数据
const statistics = computed(() => {
  const pending = reservations.value.filter(i => i.status === 'pending').length
  const approvedToday = reservations.value.filter(i => i.status === 'approved').length 
  const rejectedToday = reservations.value.filter(i => i.status === 'rejected').length
  const totalMonth = reservations.value.length

  return { pending, approvedToday, rejectedToday, totalMonth }
})

// 利用率TOP5
const topUtilization = computed<ResourceUtilization[]>(() => {
  const map = new Map<string, { count: number, type: ResourceType }>()
  
  reservations.value.forEach(res => {
    if (!map.has(res.resourceName)) {
      map.set(res.resourceName, { count: 0, type: res.type })
    }
    const item = map.get(res.resourceName)!
    item.count++
  })

  const list: ResourceUtilization[] = []
  map.forEach((val, key) => {
    // 资源利用率=月预约次数/月可预约时段总数(假设30天*5时段=150)×100%
    const rate = Math.round((val.count / 150) * 100)
    list.push({
      resourceName: key,
      type: val.type,
      reservationCount: val.count,
      utilizationRate: rate
    })
  })

  return list.sort((a, b) => b.reservationCount - a.reservationCount).slice(0, 5)
})

// --- 5. 核心逻辑 ---

// 审核操作
const handleAudit = (row: ReservationAudit) => {
  currentReservation.value = row
  rejectReason.value = ''
  dialogVisible.value = true
}

// 提交审核
const submitAudit = async (result: 'approved' | 'rejected') => {
  if (result === 'rejected' && !rejectReason.value.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }

  const targets = currentReservation.value
    ? [currentReservation.value.id]
    : selectedRows.value.map((item) => item.id)

  if (!targets.length) {
    ElMessage.warning('请选择需要审核的记录')
    return
  }

  approving.value = true
  try {
    await Promise.all(
      targets.map((id) =>
        axios.put('/service/apply/approve', {
          id,
          result,
          opinion: result === 'rejected' ? rejectReason.value : undefined
        })
      )
    )
    ElMessage.success(result === 'approved' ? '审核通过' : '已拒绝申请')
    await reloadTables(true)
  } catch (err) {
    console.error(err)
    ElMessage.error('审核失败，请稍后重试')
  } finally {
    approving.value = false
    dialogVisible.value = false
    currentReservation.value = null
    selectedRows.value = []
  }
}

// 批量审核
const handleBatchAudit = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择预约申请')
    return
  }
  currentReservation.value = null // 标记为批量
  rejectReason.value = ''
  dialogVisible.value = true
}

// 表格选择
const handleSelectionChange = (val: ReservationAudit[]) => {
  selectedRows.value = val
}

// 状态标签
const getStatusTag = (status: AuditStatus) => {
  const map = {
    pending: 'primary',
    approved: 'success',
    rejected: 'danger'
  }
  return map[status]
}

const getStatusLabel = (status: AuditStatus) => {
  const map = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝'
  }
  return map[status]
}

// 跳转筛选
const filterByStatus = (status: string) => {
  if (status === 'pending') {
    activeTab.value = 'pending'
  } else {
    activeTab.value = 'processed'
    searchQuery.status = status === 'approved' ? 'approved' : 'rejected'
  }
}
</script>

<template>
  <div class="audit-container">
    <!-- 顶部统计 -->
    <div class="stat-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-card pending" @click="filterByStatus('pending')">
            <div class="stat-icon"><el-icon><Timer /></el-icon></div>
            <div class="stat-info">
              <div class="label">待审核申请</div>
              <div class="value">{{ statistics.pending }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card approved" @click="filterByStatus('approved')">
            <div class="stat-icon"><el-icon><Check /></el-icon></div>
            <div class="stat-info">
              <div class="label">今日通过</div>
              <div class="value">{{ statistics.approvedToday }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card rejected" @click="filterByStatus('rejected')">
            <div class="stat-icon"><el-icon><Close /></el-icon></div>
            <div class="stat-info">
              <div class="label">今日拒绝</div>
              <div class="value">{{ statistics.rejectedToday }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card total">
            <div class="stat-icon"><el-icon><DataLine /></el-icon></div>
            <div class="stat-info">
              <div class="label">本月预约总数</div>
              <div class="value">{{ statistics.totalMonth }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <div class="left-panel">
        <el-card shadow="never" class="list-card">
          <template #header>
            <div class="card-header">
              <el-tabs v-model="activeTab" class="audit-tabs">
                <el-tab-pane label="待审核" name="pending" />
                <el-tab-pane label="已审核" name="processed" />
              </el-tabs>
              <div class="header-actions">
                <el-input 
                  v-model="searchQuery.keyword" 
                  placeholder="资源/申请人" 
                  :prefix-icon="Search" 
                  style="width: 200px; margin-right: 10px" 
                />
                <el-date-picker
                  v-model="searchQuery.date"
                  type="date"
                  placeholder="预约日期"
                  value-format="YYYY-MM-DD"
                  style="width: 150px; margin-right: 10px"
                />
                <el-button 
                  v-if="activeTab === 'pending'" 
                  type="primary" 
                  @click="handleBatchAudit"
                >批量审核</el-button>
              </div>
            </div>
          </template>

          <el-table 
            :data="tableData" 
            style="width: 100%" 
            v-loading="tableLoading"
            @selection-change="handleSelectionChange"
            :row-class-name="({ row }) => row.status === 'pending' ? 'pending-row' : ''"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column type="expand">
              <template #default="{ row }">
                <el-descriptions title="预约详情" :column="3" border size="small" style="padding: 10px 20px">
                  <el-descriptions-item label="资源类型">{{ row.type === 'classroom' ? '教室' : '实验室' }}</el-descriptions-item>
                  <el-descriptions-item label="联系电话">{{ row.phone }}</el-descriptions-item>
                  <el-descriptions-item label="提交时间">{{ row.submitTime }}</el-descriptions-item>
                  <el-descriptions-item label="预约时段" :span="3">
                    <el-tag v-for="slot in row.timeSlots" :key="slot" size="small" style="margin-right: 5px">{{ slot }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="预约用途" :span="3">{{ row.purpose }}</el-descriptions-item>
                  <template v-if="row.status !== 'pending'">
                    <el-descriptions-item label="审核人">{{ row.auditor }}</el-descriptions-item>
                    <el-descriptions-item label="审核时间">{{ row.auditTime }}</el-descriptions-item>
                    <el-descriptions-item label="拒绝原因" v-if="row.status === 'rejected'" :span="3">
                      <span style="color: #F56C6C">{{ row.rejectReason }}</span>
                    </el-descriptions-item>
                  </template>
                </el-descriptions>
              </template>
            </el-table-column>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="resourceName" label="资源名称" min-width="150" />
            <el-table-column prop="applicant" label="申请人" width="100" />
            <el-table-column prop="date" label="预约日期" width="120" sortable />
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusTag(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right" v-if="activeTab === 'pending'">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleAudit(row)">审核</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- 右侧TOP5 -->
      <div class="right-panel">
        <el-card shadow="hover" class="top-card">
          <template #header>
            <div class="card-title">
              <el-icon><DataLine /></el-icon>
              <span>资源利用率 TOP5</span>
            </div>
          </template>
          <div class="top-list">
            <div v-for="(item, index) in topUtilization" :key="index" class="top-item">
              <div class="top-info">
                <span class="rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</span>
                <span class="name">{{ item.resourceName }}</span>
                <span class="count">{{ item.reservationCount }}次</span>
              </div>
              <el-progress 
                :percentage="item.utilizationRate" 
                :color="index < 3 ? '#F56C6C' : '#409EFF'"
                :stroke-width="8"
              />
            </div>
          </div>
          <div class="chart-tip">
            注：资源利用率 = 月预约次数 / 月可预约时段总数 × 100%
          </div>
        </el-card>
      </div>
    </div>

    <!-- 审核弹窗 -->
    <el-dialog v-model="dialogVisible" title="预约审核" width="500px">
      <div v-if="currentReservation" class="audit-detail">
        <p><strong>申请资源：</strong>{{ currentReservation.resourceName }}</p>
        <p><strong>申请人：</strong>{{ currentReservation.applicant }}</p>
        <p><strong>预约时间：</strong>{{ currentReservation.date }} {{ currentReservation.timeSlots.join(', ') }}</p>
        <p><strong>用途：</strong>{{ currentReservation.purpose }}</p>
      </div>
      <div v-else class="audit-detail">
        <p><strong>批量审核：</strong>已选择 {{ selectedRows.length }} 条申请</p>
      </div>
      
      <el-divider content-position="left">审核意见</el-divider>
      
      <el-form label-width="80px">
        <el-form-item label="拒绝原因">
          <el-input 
            v-model="rejectReason" 
            type="textarea" 
            placeholder="若拒绝，请填写原因（必填）"
            :rows="3"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="approving" @click="submitAudit('rejected')">拒绝</el-button>
        <el-button type="success" :loading="approving" @click="submitAudit('approved')">通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.audit-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 统计卡片 */
.stat-card {
  height: 100px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  color: #fff;
  cursor: pointer;
  transition: transform 0.3s;
}
.stat-card:hover {
  transform: translateY(-2px);
}
.stat-card.pending { background: linear-gradient(135deg, #409EFF, #79bbff); }
.stat-card.approved { background: linear-gradient(135deg, #67C23A, #95d475); }
.stat-card.rejected { background: linear-gradient(135deg, #F56C6C, #fab6b6); }
.stat-card.total { background: linear-gradient(135deg, #909399, #c8c9cc); cursor: default; }

.stat-icon {
  font-size: 40px;
  opacity: 0.8;
  margin-right: 15px;
}
.stat-info .label { font-size: 14px; opacity: 0.9; }
.stat-info .value { font-size: 28px; font-weight: bold; }

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  gap: 15px;
  overflow: hidden;
}
.left-panel {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.right-panel {
  width: 300px;
}

.list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
:deep(.el-card__body) {
  flex: 1;
  overflow: auto;
  padding: 0;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.audit-tabs {
  flex: 1;
}
:deep(.el-tabs__header) {
  margin: 0;
}
.header-actions {
  display: flex;
  align-items: center;
}

/* 待审核行背景 */
:deep(.el-table .pending-row) {
  background: #FFF7E6;
}

/* TOP5 样式 */
.top-card {
  height: 100%;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
}
.top-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 10px 0;
}
.top-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.top-info {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}
.rank {
  width: 20px;
  height: 20px;
  background: #f0f2f5;
  border-radius: 50%;
  text-align: center;
  line-height: 20px;
  font-size: 12px;
  color: #909399;
  margin-right: 5px;
}
.rank-1 { background: #F56C6C; color: #fff; }
.rank-2 { background: #E6A23C; color: #fff; }
.rank-3 { background: #409EFF; color: #fff; }
.name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.count { color: #909399; font-size: 12px; }
.chart-tip {
  margin-top: 20px;
  font-size: 12px;
  color: #909399;
  text-align: center;
}

.audit-detail {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}
.audit-detail p {
  margin: 5px 0;
  color: #606266;
}
</style>
