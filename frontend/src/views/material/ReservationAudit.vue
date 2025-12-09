<script setup lang="ts">
import { ref, reactive, computed } from 'vue'

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

// --- 2. 模拟数据 ---
const mockReservations: ReservationAudit[] = []

const initMockData = () => {
  // 待审核：8条
  for (let i = 1; i <= 8; i++) {
    mockReservations.push({
      id: i,
      resourceName: i % 2 === 0 ? `多媒体教室 10${i}` : `计算机实验室 20${i}`,
      type: i % 2 === 0 ? 'classroom' : 'lab',
      applicant: `教师${String.fromCharCode(65 + i)}`,
      phone: '1380013800' + i,
      date: '2024-05-2' + (i % 9),
      timeSlots: ['08:00-09:40', '10:00-11:40'],
      purpose: '补课/实验',
      submitTime: '2024-05-18 09:00',
      status: 'pending'
    })
  }

  // 已审核：20条
  for (let i = 1; i <= 20; i++) {
    const isApproved = i <= 15
    mockReservations.push({
      id: i + 100,
      resourceName: i % 3 === 0 ? `普通教室 30${i}` : `物理实验室 40${i}`,
      type: i % 3 === 0 ? 'classroom' : 'lab',
      applicant: `教师${String.fromCharCode(70 + i)}`,
      phone: '1390013900' + i,
      date: '2024-05-1' + (i % 9),
      timeSlots: ['14:00-15:40'],
      purpose: '社团活动',
      submitTime: '2024-05-10 10:00',
      status: isApproved ? 'approved' : 'rejected',
      auditor: '管理员Admin',
      auditTime: '2024-05-10 14:00',
      rejectReason: isApproved ? undefined : '该时段已被占用'
    })
  }
}

initMockData()

// --- 3. 状态管理 ---
const activeTab = ref<'pending' | 'processed'>('pending')
const searchQuery = reactive({
  keyword: '', // 资源类型/申请人
  date: null as any,
  status: '' // 仅用于已审核列表筛选通过/拒绝
})
const dialogVisible = ref(false)
const currentReservation = ref<ReservationAudit | null>(null)
const rejectReason = ref('')
const selectedRows = ref<ReservationAudit[]>([])

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const showMessage = (text: string, color: 'success' | 'error' | 'warning' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

// --- 4. 计算属性 ---

// 列表数据
const tableData = computed(() => {
  let data = mockReservations.filter(item => {
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
  // Vuetify date picker usually returns string or date obj. Simple string match for now.
  // If date is object/array, handle accordingly. Assuming standard YYYY-MM-DD string input.
  if (searchQuery.date) {
     // For simplicity, exact match
     data = data.filter(item => item.date === searchQuery.date)
  }
  if (activeTab.value === 'processed' && searchQuery.status) {
    data = data.filter(item => item.status === searchQuery.status)
  }

  return data
})

// 统计数据
const statistics = computed(() => {
  const pending = mockReservations.filter(i => i.status === 'pending').length
  const approvedToday = mockReservations.filter(i => i.status === 'approved').length 
  const rejectedToday = mockReservations.filter(i => i.status === 'rejected').length
  const totalMonth = mockReservations.length

  return { pending, approvedToday, rejectedToday, totalMonth }
})

// 利用率TOP5
const topUtilization = computed<ResourceUtilization[]>(() => {
  const map = new Map<string, { count: number, type: ResourceType }>()
  
  mockReservations.forEach(res => {
    if (!map.has(res.resourceName)) {
      map.set(res.resourceName, { count: 0, type: res.type })
    }
    const item = map.get(res.resourceName)!
    item.count++
  })

  const list: ResourceUtilization[] = []
  map.forEach((val, key) => {
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
const submitAudit = (result: 'approved' | 'rejected') => {
  if (result === 'rejected' && !rejectReason.value.trim()) {
    showMessage('请输入拒绝原因', 'warning')
    return
  }

  const process = (res: ReservationAudit) => {
    res.status = result
    res.auditor = '管理员Admin'
    res.auditTime = new Date().toLocaleString()
    if (result === 'rejected') {
      res.rejectReason = rejectReason.value
    }
  }

  if (currentReservation.value) {
    process(currentReservation.value)
    showMessage(result === 'approved' ? '审核通过' : '已拒绝申请', 'success')
  } else if (selectedRows.value.length > 0) {
    selectedRows.value.forEach(process)
    showMessage(`批量${result === 'approved' ? '通过' : '拒绝'}成功`, 'success')
  }

  dialogVisible.value = false
  currentReservation.value = null
  selectedRows.value = []
}

// 批量审核
const handleBatchAudit = () => {
  if (selectedRows.value.length === 0) {
    showMessage('请先选择预约申请', 'warning')
    return
  }
  currentReservation.value = null // 标记为批量
  rejectReason.value = ''
  dialogVisible.value = true
}

// 状态标签颜色
const getStatusColor = (status: AuditStatus) => {
  const map = {
    pending: 'primary',
    approved: 'success',
    rejected: 'error'
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

const headers = [
  { title: 'ID', key: 'id', width: '80px' },
  { title: '资源名称', key: 'resourceName' },
  { title: '申请人', key: 'applicant' },
  { title: '预约日期', key: 'date', sortable: true },
  { title: '状态', key: 'status', align: 'center' },
  { title: '操作', key: 'actions', sortable: false, align: 'end' },
]

const expanded = ref([])

</script>

<template>
  <div class="audit-container pa-4">
    <!-- 顶部统计 -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card
          class="stat-card cursor-pointer"
          color="blue-lighten-1"
          theme="dark"
          @click="filterByStatus('pending')"
        >
          <v-card-text class="d-flex align-center">
            <v-icon size="40" class="mr-4">mdi-timer-sand</v-icon>
            <div>
              <div class="text-subtitle-2 opacity-80">待审核申请</div>
              <div class="text-h4 font-weight-bold">{{ statistics.pending }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card
          class="stat-card cursor-pointer"
          color="green-lighten-1"
          theme="dark"
          @click="filterByStatus('approved')"
        >
          <v-card-text class="d-flex align-center">
            <v-icon size="40" class="mr-4">mdi-check-circle-outline</v-icon>
            <div>
              <div class="text-subtitle-2 opacity-80">今日通过</div>
              <div class="text-h4 font-weight-bold">{{ statistics.approvedToday }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card
          class="stat-card cursor-pointer"
          color="red-lighten-1"
          theme="dark"
          @click="filterByStatus('rejected')"
        >
          <v-card-text class="d-flex align-center">
            <v-icon size="40" class="mr-4">mdi-close-circle-outline</v-icon>
            <div>
              <div class="text-subtitle-2 opacity-80">今日拒绝</div>
              <div class="text-h4 font-weight-bold">{{ statistics.rejectedToday }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card
          class="stat-card"
          color="grey-lighten-1"
          theme="dark"
        >
          <v-card-text class="d-flex align-center">
            <v-icon size="40" class="mr-4">mdi-chart-line</v-icon>
            <div>
              <div class="text-subtitle-2 opacity-80">本月预约总数</div>
              <div class="text-h4 font-weight-bold">{{ statistics.totalMonth }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 主内容区 -->
    <v-row>
      <v-col cols="12" md="9">
        <v-card elevation="2">
          <v-tabs v-model="activeTab" bg-color="primary">
            <v-tab value="pending">待审核</v-tab>
            <v-tab value="processed">已审核</v-tab>
          </v-tabs>
          
          <v-card-text>
            <v-row class="mb-2 align-center">
              <v-col cols="12" sm="4">
                <v-text-field
                  v-model="searchQuery.keyword"
                  label="搜索资源/申请人"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  density="compact"
                  hide-details
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="4">
                 <!-- Simple date input for now as Vuetify 3 date picker is complex to embed inline without v-menu -->
                 <v-text-field
                    v-model="searchQuery.date"
                    type="date"
                    label="预约日期"
                    variant="outlined"
                    density="compact"
                    hide-details
                 ></v-text-field>
              </v-col>
              <v-col cols="12" sm="4" class="text-right">
                <v-btn
                  v-if="activeTab === 'pending'"
                  color="primary"
                  @click="handleBatchAudit"
                  prepend-icon="mdi-checkbox-multiple-marked-outline"
                >批量审核</v-btn>
              </v-col>
            </v-row>

            <v-data-table
              v-model:expanded="expanded"
              :headers="headers"
              :items="tableData"
              :items-per-page="10"
              show-select
              show-expand
              v-model="selectedRows"
              item-value="id"
              class="elevation-1"
            >
              <template #item.status="{ item }">
                <v-chip :color="getStatusColor(item.status)" size="small">
                  {{ getStatusLabel(item.status) }}
                </v-chip>
              </template>
              
              <template #item.actions="{ item }">
                <v-btn
                  v-if="activeTab === 'pending'"
                  size="small"
                  color="primary"
                  variant="text"
                  @click="handleAudit(item)"
                >审核</v-btn>
              </template>

              <template #expanded-row="{ columns, item }">
                <tr>
                  <td :colspan="columns.length" class="pa-4 bg-grey-lighten-5">
                    <v-row>
                      <v-col cols="12" sm="4">
                        <div class="text-caption text-grey">资源类型</div>
                        <div>{{ item.type === 'classroom' ? '教室' : '实验室' }}</div>
                      </v-col>
                      <v-col cols="12" sm="4">
                        <div class="text-caption text-grey">联系电话</div>
                        <div>{{ item.phone }}</div>
                      </v-col>
                      <v-col cols="12" sm="4">
                        <div class="text-caption text-grey">提交时间</div>
                        <div>{{ item.submitTime }}</div>
                      </v-col>
                      <v-col cols="12">
                        <div class="text-caption text-grey">预约时段</div>
                        <div class="d-flex gap-2 mt-1">
                           <v-chip v-for="slot in item.timeSlots" :key="slot" size="small">{{ slot }}</v-chip>
                        </div>
                      </v-col>
                      <v-col cols="12">
                        <div class="text-caption text-grey">预约用途</div>
                        <div>{{ item.purpose }}</div>
                      </v-col>
                      <v-col cols="12" v-if="item.status !== 'pending'">
                         <v-divider class="my-2"></v-divider>
                         <div class="d-flex justify-space-between">
                            <div>
                               <span class="text-caption text-grey mr-2">审核人:</span>
                               <span>{{ item.auditor }}</span>
                            </div>
                            <div>
                               <span class="text-caption text-grey mr-2">审核时间:</span>
                               <span>{{ item.auditTime }}</span>
                            </div>
                         </div>
                         <div v-if="item.status === 'rejected'" class="mt-2 text-error">
                            <span class="text-caption mr-2">拒绝原因:</span>
                            <span class="font-weight-bold">{{ item.rejectReason }}</span>
                         </div>
                      </v-col>
                    </v-row>
                  </td>
                </tr>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧TOP5 -->
      <v-col cols="12" md="3">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            <v-icon start color="primary">mdi-chart-bar</v-icon>
            资源利用率 TOP5
          </v-card-title>
          <v-card-text>
            <div v-for="(item, index) in topUtilization" :key="index" class="mb-4">
              <div class="d-flex justify-space-between mb-1 text-body-2">
                <div class="d-flex align-center" style="width: 80%; overflow: hidden;">
                  <v-avatar
                    size="20"
                    :color="index < 3 ? (index === 0 ? 'red' : index === 1 ? 'orange' : 'blue') : 'grey'"
                    class="text-caption text-white mr-2"
                  >
                    {{ index + 1 }}
                  </v-avatar>
                  <span class="text-truncate">{{ item.resourceName }}</span>
                </div>
                <span class="text-grey text-caption">{{ item.reservationCount }}次</span>
              </div>
              <v-progress-linear
                :model-value="item.utilizationRate"
                :color="index < 3 ? 'primary' : 'info'"
                height="6"
                rounded
              ></v-progress-linear>
            </div>
            <div class="text-caption text-center text-grey mt-4">
              注：资源利用率 = 月预约次数 / 月可预约时段总数 × 100%
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 审核弹窗 -->
    <v-dialog v-model="dialogVisible" max-width="500px">
      <v-card>
        <v-card-title>预约审核</v-card-title>
        <v-card-text>
          <div v-if="currentReservation" class="bg-grey-lighten-4 pa-3 rounded mb-4">
            <div class="text-body-2 mb-1"><strong>申请资源：</strong>{{ currentReservation.resourceName }}</div>
            <div class="text-body-2 mb-1"><strong>申请人：</strong>{{ currentReservation.applicant }}</div>
            <div class="text-body-2 mb-1"><strong>预约时间：</strong>{{ currentReservation.date }} {{ currentReservation.timeSlots.join(', ') }}</div>
            <div class="text-body-2"><strong>用途：</strong>{{ currentReservation.purpose }}</div>
          </div>
          <div v-else class="bg-grey-lighten-4 pa-3 rounded mb-4">
             <div class="text-body-2"><strong>批量审核：</strong>已选择 {{ selectedRows.length }} 条申请</div>
          </div>

          <v-textarea
            v-model="rejectReason"
            label="拒绝原因 (若拒绝则必填)"
            rows="3"
            variant="outlined"
            auto-grow
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="dialogVisible = false">取消</v-btn>
          <v-btn color="error" variant="flat" @click="submitAudit('rejected')">拒绝</v-btn>
          <v-btn color="success" variant="flat" @click="submitAudit('approved')">通过</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="top"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<style scoped>
.audit-container {
  /* height: 100%; */
}
.cursor-pointer {
  cursor: pointer;
}
</style>
