<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Upload, Download, Refresh, Search, View, Edit, Tools } from '@element-plus/icons-vue'
import { classroomApi, type ClassroomResponse, type ClassroomPayload, type ResourceStatus } from '@/api/classroom'

type ResourceType = 'classroom' | 'lab' | 'equipment'

interface BaseResource {
  id: number
  code: string
  name: string
  status: ResourceStatus
  remark?: string
}

interface ClassroomForm {
  id: number
  code: string
  name: string
  capacity: number
  location: string
  devices: string[]
  status: ResourceStatus
  remark: string
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

const classrooms = ref<ClassroomResponse[]>([])
const labs = ref<Lab[]>([])
const equipment = ref<Equipment[]>([])

const activeTab = ref<ResourceType>('classroom')
const searchQuery = reactive({
  keyword: '',
  status: '' as '' | ResourceStatus
})
const loading = ref(false)
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const reservationDialogVisible = ref(false)
const currentReservations = ref<Reservation[]>([])
const isClassroomTab = computed(() => activeTab.value === 'classroom')

const emptyForm = (): ClassroomForm => ({
  id: 0,
  code: '',
  name: '',
  capacity: 40,
  location: '',
  devices: [],
  status: 'idle',
  remark: ''
})
const form = reactive<ClassroomForm>(emptyForm())

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

const getStatusTag = (status: ResourceStatus) => {
  const map: Record<string, { label: string, type: string }> = {
    in_use: { label: '在用', type: 'success' },
    idle: { label: '空闲', type: 'info' },
    maintenance: { label: '维护', type: 'warning' },
    scrapped: { label: '报废', type: 'danger' },
    normal: { label: '正常', type: 'success' }
  }
  return map[status] || { label: status, type: 'info' }
}

const loadClassrooms = async () => {
  loading.value = true
  try {
    classrooms.value = await classroomApi.list()
  } catch (error: any) {
    const detail = error?.response?.data?.detail || '加载教室数据失败'
    ElMessage.error(detail)
    classrooms.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadClassrooms()
})

const requireClassroomTab = (action: string) => {
  if (!isClassroomTab.value) {
    ElMessage.info(`当前仅支持教室资源${action}`)
    return false
  }
  return true
}

const handleRefresh = async () => {
  await loadClassrooms()
  ElMessage.success('数据已刷新')
}

const handleAdd = () => {
  if (!requireClassroomTab('操作')) return
  dialogType.value = 'add'
  Object.assign(form, emptyForm())
  const random = Math.floor(Math.random() * 1000)
  form.code = `CLS-${Date.now().toString().slice(-4)}${random}`
  form.status = 'idle'
  form.devices = []
  dialogVisible.value = true
}

const handleEdit = (row: ClassroomResponse) => {
  if (!requireClassroomTab('操作')) return
  dialogType.value = 'edit'
  Object.assign(form, {
    id: row.id,
    code: row.code,
    name: row.name,
    capacity: row.capacity,
    location: row.location || '',
    devices: [...(row.devices || [])],
    status: row.status,
    remark: row.remark || ''
  })
  dialogVisible.value = true
}

const buildPayload = (): ClassroomPayload => {
  const trimmedName = form.name.trim()
  if (!trimmedName) {
    throw new Error('请填写教室名称')
  }
  const capacity = Number(form.capacity)
  if (!capacity || capacity <= 0) {
    throw new Error('教室容量必须大于 0')
  }
  return {
    name: trimmedName,
    capacity,
    is_multimedia: form.devices.includes('多媒体'),
    code: form.code.trim() || undefined,
    location: form.location.trim() || undefined,
    devices: [...form.devices],
    status: form.status,
    remark: form.remark.trim() || undefined
  }
}

const handleSave = async () => {
  if (!requireClassroomTab('操作')) return
  try {
    const payload = buildPayload()
    if (dialogType.value === 'add') {
      await classroomApi.create(payload)
      ElMessage.success('教室新增成功')
    } else {
      await classroomApi.update(form.id, payload)
      ElMessage.success('教室更新成功')
    }
    dialogVisible.value = false
    await loadClassrooms()
  } catch (error: any) {
    const detail = error?.message || error?.response?.data?.detail || '保存失败'
    ElMessage.error(detail)
  }
}

const handleDelete = (row: ClassroomResponse) => {
  if (!requireClassroomTab('删除')) return
  ElMessageBox.confirm('确定要删除该教室吗？', '提示', { type: 'warning' })
    .then(async () => {
      await classroomApi.remove(row.id)
      ElMessage.success('删除成功')
      await loadClassrooms()
    })
    .catch(() => {})
}

const handleStatusChange = (row: ClassroomResponse, newStatus: ResourceStatus) => {
  if (!requireClassroomTab('操作')) return
  const persist = async (remark?: string) => {
    try {
      await classroomApi.update(row.id, { status: newStatus, remark })
      ElMessage.success('状态更新成功')
      await loadClassrooms()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || '状态更新失败'
      ElMessage.error(detail)
    }
  }

  if (newStatus === 'maintenance' || newStatus === 'scrapped') {
    ElMessageBox.prompt('请输入原因', '提示', {
      inputPattern: /\S+/,
      inputErrorMessage: '原因不能为空'
    }).then(({ value }) => {
      persist(`${row.remark ? `${row.remark}; ` : ''}${value}`)
    })
  } else {
    ElMessageBox.confirm(`确认将状态变更为 ${getStatusTag(newStatus).label} 吗？`, '提示')
      .then(() => persist(row.remark))
      .catch(() => {})
  }
}

const handleViewReservations = () => {
  currentReservations.value = [
    { date: '2024-05-20 08:00-10:00', applicant: '李老师', purpose: '课程教学' },
    { date: '2024-05-21 14:00-16:00', applicant: '软件工程 2201 班', purpose: '社团活动' },
    { date: '2024-05-22 09:00-11:00', applicant: '实验中心', purpose: '实验调试' }
  ]
  reservationDialogVisible.value = true
}

const handleImport = () => {
  ElMessage.info('请通过模板导入后端接口，当前操作仅为演示')
}

const handleExport = () => {
  ElMessage.info('后端导出接口尚未接入，当前操作仅为演示')
}
</script>

<template>
  <div class="resource-management-container">
    <!-- 顶部 Tabs 和 操作栏 -->
    <div class="top-bar">
      <el-tabs v-model="activeTab" class="resource-tabs">
        <el-tab-pane label="教室管理" name="classroom" />
        <el-tab-pane label="实验室管理" name="lab" />
        <el-tab-pane label="设备管理" name="equipment" />
      </el-tabs>
      <div class="action-group">
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增资源</el-button>
        <el-button type="danger" :icon="Delete" plain>批量删除</el-button>
        <el-button :icon="Upload" @click="handleImport">导入Excel</el-button>
        <el-button :icon="Download" @click="handleExport">导出Excel</el-button>
        <el-button :icon="Refresh" circle @click="handleRefresh" />
      </div>
    </div>

    <!-- 搜索和统计 -->
    <div class="search-stat-section">
      <el-card class="search-card" shadow="never">
        <el-form :inline="true" :model="searchQuery">
          <el-form-item label="关键词">
            <el-input v-model="searchQuery.keyword" placeholder="名称/编号/位置" :prefix-icon="Search" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="searchQuery.status" placeholder="全部状态" clearable style="width: 120px">
              <el-option label="在用/正常" value="in_use" />
              <el-option label="空闲" value="idle" />
              <el-option label="维修" value="maintenance" />
              <el-option label="报废" value="scrapped" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="stat-card" shadow="hover">
        <div class="stat-items">
          <div class="stat-item">
            <div class="label">总资源</div>
            <div class="value">{{ statistics.total }}</div>
          </div>
          <div class="stat-item success">
            <div class="label">在用/正常</div>
            <div class="value">{{ statistics.inUse }}</div>
          </div>
          <div class="stat-item info">
            <div class="label">空闲</div>
            <div class="value">{{ statistics.idle }}</div>
          </div>
          <div class="stat-item warning">
            <div class="label">维修</div>
            <div class="value">{{ statistics.maintenance }}</div>
          </div>
          <div class="stat-item danger">
            <div class="label">报废</div>
            <div class="value">{{ statistics.scrapped }}</div>
          </div>
          <div class="stat-item primary" v-if="activeTab === 'classroom'">
            <div class="label">利用率</div>
            <div class="value">{{ statistics.utilization }}%</div>
            <!-- 教室利用率=在用数量/总数量×100% -->
          </div>
        </div>
      </el-card>
    </div>

    <!-- 资源列表 -->
    <el-card class="table-card" shadow="never">
      <el-table :data="tableData" v-loading="loading || tableLoading" style="width: 100%" height="100%">
        <el-table-column prop="code" label="编号" width="120" fixed />
        <el-table-column prop="name" label="名称" min-width="150" show-overflow-tooltip />
        
        <!-- 教室特有字段 -->
        <el-table-column v-if="activeTab === 'classroom'" prop="capacity" label="容量" width="80" align="center" />
        <el-table-column v-if="activeTab === 'classroom'" prop="location" label="位置" width="150" />
        <el-table-column v-if="activeTab === 'classroom'" label="设备配置" min-width="150">
          <template #default="{ row }">
            <el-tag v-for="dev in row.devices" :key="dev" size="small" style="margin-right: 5px">{{ dev }}</el-tag>
          </template>
        </el-table-column>

        <!-- 实验室特有字段 -->
        <el-table-column v-if="activeTab === 'lab'" prop="type" label="类型" width="100" />
        <el-table-column v-if="activeTab === 'lab'" prop="capacity" label="容纳人数" width="100" align="center" />
        <el-table-column v-if="activeTab === 'lab'" prop="manager" label="负责人" width="100" />
        
        <!-- 设备特有字段 -->
        <el-table-column v-if="activeTab === 'equipment'" prop="type" label="类型" width="100" />
        <el-table-column v-if="activeTab === 'equipment'" prop="resourceName" label="所属资源" width="120" />
        <el-table-column v-if="activeTab === 'equipment'" prop="purchaseTime" label="采购时间" width="120" />

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status).type">{{ getStatusTag(row.status).label }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="primary" :icon="View" @click="handleViewReservations(row)">查看预约</el-button>
            
            <el-dropdown style="margin-left: 10px" @command="(cmd: any) => handleStatusChange(row, cmd)">
              <el-button link type="warning" :icon="Tools">状态管理</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="in_use" v-if="activeTab !== 'equipment'">设为在用</el-dropdown-item>
                  <el-dropdown-item command="idle" v-if="activeTab !== 'equipment'">设为空闲</el-dropdown-item>
                  <el-dropdown-item command="normal" v-if="activeTab === 'equipment'">设为正常</el-dropdown-item>
                  <el-dropdown-item command="maintenance" divided>报修/维护</el-dropdown-item>
                  <el-dropdown-item command="scrapped" v-if="activeTab === 'equipment'">报废</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增资源' : '编辑资源'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="编号" required>
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        
        <!-- 教室字段 -->
        <template v-if="activeTab === 'classroom'">
          <el-form-item label="容量">
            <el-input-number v-model="form.capacity" :min="1" />
          </el-form-item>
          <el-form-item label="位置">
            <el-input v-model="form.location" />
          </el-form-item>
          <el-form-item label="设备配置">
            <el-checkbox-group v-model="form.devices">
              <el-checkbox label="多媒体" />
              <el-checkbox label="空调" />
              <el-checkbox label="投影仪" />
              <el-checkbox label="音响" />
            </el-checkbox-group>
          </el-form-item>
        </template>

        <!-- 实验室字段 -->
        <template v-if="activeTab === 'lab'">
          <el-form-item label="类型">
            <el-select v-model="form.type">
              <el-option label="计算机" value="计算机" />
              <el-option label="物理" value="物理" />
              <el-option label="化学" value="化学" />
            </el-select>
          </el-form-item>
          <el-form-item label="容纳人数">
            <el-input-number v-model="form.capacity" :min="1" />
          </el-form-item>
          <el-form-item label="负责人">
            <el-select v-model="form.manager">
              <el-option label="张老师" value="张老师" />
              <el-option label="李老师" value="李老师" />
            </el-select>
          </el-form-item>
          <el-form-item label="安全要求">
            <el-input v-model="form.safetyRequirements" type="textarea" />
          </el-form-item>
        </template>

        <!-- 设备字段 -->
        <template v-if="activeTab === 'equipment'">
          <el-form-item label="类型">
            <el-select v-model="form.type">
              <el-option label="投影仪" value="投影仪" />
              <el-option label="电脑" value="电脑" />
              <el-option label="实验仪器" value="实验仪器" />
            </el-select>
          </el-form-item>
          <el-form-item label="所属资源">
            <el-input v-model="form.resourceName" placeholder="关联教室/实验室" />
          </el-form-item>
          <el-form-item label="采购时间">
            <el-date-picker v-model="form.purchaseTime" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="规格参数">
            <el-input v-model="form.spec" type="textarea" />
          </el-form-item>
        </template>

        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 预约记录弹窗 -->
    <el-dialog v-model="reservationDialogVisible" title="近期预约记录" width="600px">
      <el-table :data="currentReservations" border>
        <el-table-column prop="date" label="时间段" width="200" />
        <el-table-column prop="applicant" label="申请人" width="100" />
        <el-table-column prop="purpose" label="用途" />
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.resource-management-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 10px 20px;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.resource-tabs {
  flex: 1;
}
:deep(.el-tabs__header) {
  margin: 0;
}
.search-stat-section {
  display: flex;
  gap: 15px;
}
.search-card {
  flex: 1;
}
.stat-card {
  flex: 1.5;
}
.stat-items {
  display: flex;
  justify-content: space-around;
  align-items: center;
}
.stat-item {
  text-align: center;
}
.stat-item .label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}
.stat-item .value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
.stat-item.success .value { color: #67C23A; }
.stat-item.info .value { color: #909399; }
.stat-item.warning .value { color: #E6A23C; }
.stat-item.danger .value { color: #F56C6C; }
.stat-item.primary .value { color: #409EFF; }

.table-card {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
:deep(.el-card__body) {
  height: 100%;
  padding: 0;
}
/* 表格hover行背景 */
:deep(.el-table__body tr:hover > td) {
  background-color: #FFF7E6 !important;
}
</style>
