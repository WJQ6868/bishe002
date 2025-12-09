<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'

// --- 1. 类型定义 ---
type ResourceType = 'classroom' | 'lab' | 'equipment'
type ResourceStatus = 'in_use' | 'idle' | 'maintenance' | 'scrapped' | 'normal'

interface BaseResource {
  id: number
  code: string
  name: string
  status: ResourceStatus
  remark?: string
}

interface Classroom extends BaseResource {
  capacity: number
  location: string
  devices: string[]
}

interface Lab extends BaseResource {
  type: string
  capacity: number
  manager: string
  safetyRequirements?: string
}

interface Equipment extends BaseResource {
  type: string
  resourceId?: number
  resourceName?: string
  purchaseTime: string
  spec?: string
}

interface Reservation {
  date: string
  applicant: string
  purpose: string
}

// --- 2. 数据源 ---
const classrooms = ref<Classroom[]>([])
const labs = ref<Lab[]>([])
const equipment = ref<Equipment[]>([])

// 去除演示数据，使用后端接口

// --- 3. 状态管理 ---
const activeTab = ref<ResourceType>('classroom')
const searchQuery = reactive({
  keyword: '',
  status: null as string | null
})
const loading = ref(false)
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const reservationDialogVisible = ref(false)
const currentReservations = ref<Reservation[]>([])

// Snackbar & Dialogs
const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})
const confirmDialog = reactive({
  show: false,
  title: '',
  text: '',
  onConfirm: () => {}
})
const promptDialog = reactive({
  show: false,
  title: '',
  label: '',
  value: '',
  onConfirm: (val: string) => {}
})

// Form
const form = reactive<any>({
  id: 0,
  code: '',
  name: '',
  capacity: 0,
  location: '',
  devices: [],
  type: '',
  manager: '',
  safetyRequirements: '',
  resourceName: '',
  purchaseTime: '',
  spec: '',
  status: 'idle',
  remark: ''
})

const formRef = ref()
const rules = {
  required: (v: any) => !!v || '此项为必填项',
}

// --- 4. 计算属性 ---
const tableData = computed(() => {
  let data: any[] = []
  if (activeTab.value === 'classroom') data = classrooms.value
  else if (activeTab.value === 'lab') data = labs.value
  else data = equipment.value

  return data.filter(item => {
    const matchKeyword = !searchQuery.keyword || 
      item.name.includes(searchQuery.keyword) || 
      item.code.includes(searchQuery.keyword) ||
      (item as any).location?.includes(searchQuery.keyword)
    
    const matchStatus = !searchQuery.status || item.status === searchQuery.status
    
    return matchKeyword && matchStatus
  })
})

const statistics = computed(() => {
  const data = tableData.value
  const total = data.length
  const inUse = data.filter(i => i.status === 'in_use' || i.status === 'normal').length
  const idle = data.filter(i => i.status === 'idle').length
  const maintenance = data.filter(i => i.status === 'maintenance').length
  const scrapped = data.filter(i => i.status === 'scrapped').length
  const utilization = total > 0 ? Math.round((inUse / total) * 100) : 0

  return { total, inUse, idle, maintenance, scrapped, utilization }
})

const headers = computed(() => {
  const baseHeaders = [
    { title: '编号', key: 'code', fixed: true, width: '120px' },
    { title: '名称', key: 'name', minWidth: '150px' },
  ]
  
  if (activeTab.value === 'classroom') {
    return [
      ...baseHeaders,
      { title: '容量', key: 'capacity', align: 'center' },
      { title: '位置', key: 'location' },
      { title: '设备配置', key: 'devices', sortable: false },
      { title: '状态', key: 'status', align: 'center' },
      { title: '操作', key: 'actions', align: 'end', sortable: false, width: '220px' }
    ]
  } else if (activeTab.value === 'lab') {
    return [
      ...baseHeaders,
      { title: '类型', key: 'type' },
      { title: '容纳人数', key: 'capacity', align: 'center' },
      { title: '负责人', key: 'manager' },
      { title: '状态', key: 'status', align: 'center' },
      { title: '操作', key: 'actions', align: 'end', sortable: false, width: '220px' }
    ]
  } else {
    return [
      ...baseHeaders,
      { title: '类型', key: 'type' },
      { title: '所属资源', key: 'resourceName' },
      { title: '采购时间', key: 'purchaseTime' },
      { title: '状态', key: 'status', align: 'center' },
      { title: '操作', key: 'actions', align: 'end', sortable: false, width: '220px' }
    ]
  }
})

// --- 5. 核心逻辑 ---
const showMessage = (text: string, color: 'success' | 'warning' | 'error' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

const getStatusColor = (status: ResourceStatus) => {
  const map: Record<string, string> = {
    in_use: 'success',
    idle: 'info',
    maintenance: 'warning',
    scrapped: 'error',
    normal: 'success'
  }
  return map[status] || 'grey'
}

const getStatusLabel = (status: ResourceStatus) => {
  const map: Record<string, string> = {
    in_use: '在用',
    idle: '空闲',
    maintenance: '维修',
    scrapped: '报废',
    normal: '正常'
  }
  return map[status] || status
}

const handleRefresh = async () => {
  await fetchClassrooms()
  showMessage('已刷新', 'success')
}

const fetchClassrooms = async () => {
  loading.value = true
  try {
    const res = await axios.get('http://localhost:8000/api/classroom/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    classrooms.value = res.data.map((c: any) => ({
      id: c.id,
      code: `CLS-${c.id}`,
      name: c.name,
      capacity: c.capacity,
      location: '',
      devices: c.is_multimedia ? ['多媒体'] : [],
      status: 'normal',
      remark: ''
    }))
  } catch (e) {
    showMessage('获取教室列表失败', 'error')
    classrooms.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchClassrooms()
})

const handleAdd = () => {
  dialogType.value = 'add'
  const prefix = activeTab.value === 'classroom' ? 'J-' : activeTab.value === 'lab' ? 'S-' : 'E-'
  const random = Math.floor(Math.random() * 1000)
  
  // Reset form
  Object.keys(form).forEach(key => form[key] = '')
  form.id = 0
  form.code = `${prefix}${Date.now().toString().slice(-4)}${random}`
  form.status = activeTab.value === 'equipment' ? 'normal' : 'idle'
  form.devices = []
  form.capacity = 0
  
  dialogVisible.value = true
}

const handleEdit = (row: any) => {
  dialogType.value = 'edit'
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleSave = async () => {
  const { valid } = await formRef.value.validate()
  if (valid) {
    showMessage(dialogType.value === 'add' ? '添加成功' : '修改成功')
    dialogVisible.value = false
    handleRefresh()
  }
}

const handleDelete = (row: any) => {
  confirmDialog.title = '删除确认'
  confirmDialog.text = '确定要删除该资源吗？'
  confirmDialog.onConfirm = () => {
    showMessage('删除成功')
    handleRefresh()
  }
  confirmDialog.show = true
}

const handleConfirmDialog = () => {
  confirmDialog.onConfirm()
  confirmDialog.show = false
}

const handlePromptConfirm = () => {
  if (!promptDialog.value) {
    showMessage('请输入原因', 'warning')
    return
  }
  promptDialog.onConfirm(promptDialog.value)
  promptDialog.show = false
}

const handleStatusChange = (row: any, newStatus: ResourceStatus) => {
  if (newStatus === 'maintenance' || newStatus === 'scrapped') {
    promptDialog.title = '请输入原因'
    promptDialog.label = '原因'
    promptDialog.value = ''
    promptDialog.onConfirm = (val) => {
      row.status = newStatus
      row.remark = `${row.remark ? row.remark + '; ' : ''}${val}`
      showMessage('状态更新成功')
    }
    promptDialog.show = true
  } else {
    confirmDialog.title = '状态变更'
    confirmDialog.text = `确定将状态变更为${getStatusLabel(newStatus)}吗？`
    confirmDialog.onConfirm = () => {
      row.status = newStatus
      showMessage('状态更新成功')
    }
    confirmDialog.show = true
  }
}

const handleViewReservations = (row: any) => {
  currentReservations.value = [
    { date: '2024-05-20 08:00-10:00', applicant: '张老师', purpose: '授课' },
    { date: '2024-05-21 14:00-16:00', applicant: '李同学', purpose: '社团活动' },
    { date: '2024-05-22 09:00-11:00', applicant: '王教授', purpose: '实验' }
  ]
  reservationDialogVisible.value = true
}

const handleImport = () => showMessage('模拟导入成功')
const handleExport = () => showMessage('模拟导出成功')

</script>

<template>
  <div class="resource-management-container">
    <!-- 顶部 Tabs 和 操作栏 -->
    <v-card class="mb-4">
      <v-tabs v-model="activeTab" color="primary" align-tabs="start">
        <v-tab value="classroom">教室管理</v-tab>
        <v-tab value="lab">实验室管理</v-tab>
        <v-tab value="equipment">设备管理</v-tab>
      </v-tabs>
      
      <v-divider></v-divider>
      
      <div class="d-flex flex-wrap align-center justify-space-between pa-4 gap-4">
        <div class="d-flex gap-2">
          <v-btn color="primary" prepend-icon="mdi-plus" @click="handleAdd">新增资源</v-btn>
          <v-btn color="error" variant="outlined" prepend-icon="mdi-delete" disabled>批量删除</v-btn>
          <v-btn variant="text" prepend-icon="mdi-upload" @click="handleImport">导入</v-btn>
          <v-btn variant="text" prepend-icon="mdi-download" @click="handleExport">导出</v-btn>
          <v-btn icon size="small" variant="text" @click="handleRefresh"><v-icon>mdi-refresh</v-icon></v-btn>
        </div>
        
        <div class="d-flex gap-2 align-center" style="min-width: 400px">
          <v-select
            v-model="searchQuery.status"
            :items="[
              { title: '在用/正常', value: 'in_use' },
              { title: '空闲', value: 'idle' },
              { title: '维修', value: 'maintenance' },
              { title: '报废', value: 'scrapped' }
            ]"
            placeholder="状态"
            density="compact"
            hide-details
            clearable
            style="max-width: 140px"
          ></v-select>
          <v-text-field
            v-model="searchQuery.keyword"
            placeholder="名称/编号/位置"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            hide-details
            style="max-width: 200px"
          ></v-text-field>
        </div>
      </div>
    </v-card>

    <!-- 统计卡片 -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="2">
        <v-card class="text-center pa-3" elevation="1">
          <div class="text-caption text-grey">总资源</div>
          <div class="text-h5 font-weight-bold">{{ statistics.total }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-card class="text-center pa-3 text-success" elevation="1">
          <div class="text-caption text-grey">在用/正常</div>
          <div class="text-h5 font-weight-bold">{{ statistics.inUse }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-card class="text-center pa-3 text-info" elevation="1">
          <div class="text-caption text-grey">空闲</div>
          <div class="text-h5 font-weight-bold">{{ statistics.idle }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-card class="text-center pa-3 text-warning" elevation="1">
          <div class="text-caption text-grey">维修</div>
          <div class="text-h5 font-weight-bold">{{ statistics.maintenance }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-card class="text-center pa-3 text-error" elevation="1">
          <div class="text-caption text-grey">报废</div>
          <div class="text-h5 font-weight-bold">{{ statistics.scrapped }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2" v-if="activeTab === 'classroom'">
        <v-card class="text-center pa-3 text-primary" elevation="1">
          <div class="text-caption text-grey">利用率</div>
          <div class="text-h5 font-weight-bold">{{ statistics.utilization }}%</div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 资源列表 -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="tableData"
        :loading="loading"
        item-value="id"
        hover
      >
        <template #item.devices="{ item }">
          <div v-if="activeTab === 'classroom'">
            <v-chip v-for="dev in (item as any).devices" :key="dev" size="x-small" class="mr-1" variant="outlined">
              {{ dev }}
            </v-chip>
          </div>
        </template>

        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small" label>
            {{ getStatusLabel(item.status) }}
          </v-chip>
        </template>

        <template #item.actions="{ item }">
          <v-btn icon size="small" variant="text" color="primary" @click="handleEdit(item)">
            <v-icon>mdi-pencil</v-icon>
            <v-tooltip activator="parent" location="top">编辑</v-tooltip>
          </v-btn>
          <v-btn icon size="small" variant="text" color="info" @click="handleViewReservations(item)">
            <v-icon>mdi-eye</v-icon>
            <v-tooltip activator="parent" location="top">查看预约</v-tooltip>
          </v-btn>
          
          <v-menu>
            <template #activator="{ props }">
              <v-btn icon size="small" variant="text" color="warning" v-bind="props">
                <v-icon>mdi-cog</v-icon>
                <v-tooltip activator="parent" location="top">状态管理</v-tooltip>
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item v-if="activeTab !== 'equipment'" @click="handleStatusChange(item, 'in_use')">
                <v-list-item-title>设为在用</v-list-item-title>
              </v-list-item>
              <v-list-item v-if="activeTab !== 'equipment'" @click="handleStatusChange(item, 'idle')">
                <v-list-item-title>设为空闲</v-list-item-title>
              </v-list-item>
              <v-list-item v-if="activeTab === 'equipment'" @click="handleStatusChange(item, 'normal')">
                <v-list-item-title>设为正常</v-list-item-title>
              </v-list-item>
              <v-divider></v-divider>
              <v-list-item @click="handleStatusChange(item, 'maintenance')">
                <v-list-item-title>报修/维护</v-list-item-title>
              </v-list-item>
              <v-list-item v-if="activeTab === 'equipment'" @click="handleStatusChange(item, 'scrapped')">
                <v-list-item-title>报废</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </template>
      </v-data-table>
    </v-card>

    <!-- 新增/编辑弹窗 -->
    <v-dialog v-model="dialogVisible" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ dialogType === 'add' ? '新增资源' : '编辑资源' }}</span>
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-text-field v-model="form.code" label="编号" :rules="[rules.required]" required></v-text-field>
            <v-text-field v-model="form.name" label="名称" :rules="[rules.required]" required></v-text-field>

            <!-- 教室字段 -->
            <template v-if="activeTab === 'classroom'">
              <v-text-field v-model.number="form.capacity" label="容量" type="number" min="1"></v-text-field>
              <v-text-field v-model="form.location" label="位置"></v-text-field>
              <div class="text-caption mb-2">设备配置</div>
              <div class="d-flex flex-wrap gap-2">
                <v-checkbox v-model="form.devices" label="多媒体" value="多媒体" density="compact" hide-details></v-checkbox>
                <v-checkbox v-model="form.devices" label="空调" value="空调" density="compact" hide-details></v-checkbox>
                <v-checkbox v-model="form.devices" label="投影仪" value="投影仪" density="compact" hide-details></v-checkbox>
                <v-checkbox v-model="form.devices" label="音响" value="音响" density="compact" hide-details></v-checkbox>
              </div>
            </template>

            <!-- 实验室字段 -->
            <template v-if="activeTab === 'lab'">
              <v-select v-model="form.type" :items="['计算机', '物理', '化学']" label="类型"></v-select>
              <v-text-field v-model.number="form.capacity" label="容纳人数" type="number" min="1"></v-text-field>
              <v-select v-model="form.manager" :items="['张老师', '李老师']" label="负责人"></v-select>
              <v-textarea v-model="form.safetyRequirements" label="安全要求" rows="2"></v-textarea>
            </template>

            <!-- 设备字段 -->
            <template v-if="activeTab === 'equipment'">
              <v-select v-model="form.type" :items="['投影仪', '电脑', '实验仪器']" label="类型"></v-select>
              <v-text-field v-model="form.resourceName" label="所属资源" placeholder="关联教室/实验室"></v-text-field>
              <v-text-field v-model="form.purchaseTime" label="采购时间" type="date"></v-text-field>
              <v-textarea v-model="form.spec" label="规格参数" rows="2"></v-textarea>
            </template>

            <v-textarea v-model="form.remark" label="备注" rows="2" class="mt-2"></v-textarea>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="dialogVisible = false">取消</v-btn>
          <v-btn color="primary" variant="text" @click="handleSave">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 预约记录弹窗 -->
    <v-dialog v-model="reservationDialogVisible" max-width="600px">
      <v-card>
        <v-card-title>近期预约记录</v-card-title>
        <v-card-text>
          <v-table>
            <thead>
              <tr>
                <th>时间段</th>
                <th>申请人</th>
                <th>用途</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(res, i) in currentReservations" :key="i">
                <td>{{ res.date }}</td>
                <td>{{ res.applicant }}</td>
                <td>{{ res.purpose }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="reservationDialogVisible = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Global Snackbars & Dialogs -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.text }}
      <template #actions>
        <v-btn color="white" variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>

    <v-dialog v-model="confirmDialog.show" max-width="400">
      <v-card>
        <v-card-title>{{ confirmDialog.title }}</v-card-title>
        <v-card-text>{{ confirmDialog.text }}</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="confirmDialog.show = false">取消</v-btn>
          <v-btn color="primary" variant="text" @click="handleConfirmDialog">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="promptDialog.show" max-width="400">
      <v-card>
        <v-card-title>{{ promptDialog.title }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="promptDialog.value" :label="promptDialog.label" autofocus></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="promptDialog.show = false">取消</v-btn>
          <v-btn color="primary" variant="text" @click="handlePromptConfirm">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.gap-2 { gap: 8px; }
.gap-4 { gap: 16px; }
</style>
