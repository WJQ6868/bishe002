<template>
  <div class="service-config" v-loading="loading">
    <div class="page-header">
      <div>
        <h2>申请功能维护</h2>
        <p class="subtitle">统一管理学生/教师端「我的申请」的类型、规则与前端展示</p>
      </div>
      <div class="actions">
        <el-button type="primary" @click="openEditor()">新增申请类型</el-button>
        <el-button @click="fetchList">刷新</el-button>
      </div>
    </div>

    <el-alert
      title="变更后实时生效，前端无需发版；请注意审批流与时长规则的合理性"
      type="info"
      show-icon
      :closable="false"
      class="mb-3"
    />

    <el-table :data="items" border style="width: 100%">
      <el-table-column prop="name" label="申请类型" min-width="160" />
      <el-table-column prop="category" label="分类" width="140" />
      <el-table-column label="适用角色" width="120">
        <template #default="{ row }">
          <el-tag>{{ renderRole(row.config?.role_scope) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="排序" width="90" prop="config.display_order" />
      <el-table-column label="入口位置" min-width="160">
        <template #default="{ row }">
          <el-space wrap>
            <el-tag v-for="pos in row.config?.entry_positions || []" :key="pos" type="info" size="small">{{ renderEntry(pos) }}</el-tag>
          </el-space>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'available' ? 'success' : 'info'">{{ row.status === 'available' ? '启用' : '暂停' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="未读提醒" width="110">
        <template #default="{ row }">
          <el-tag :type="row.config?.unread_badge ? 'warning' : 'info'">{{ row.config?.unread_badge ? '开启' : '关闭' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditor(row)">编辑</el-button>
          <el-popconfirm title="确认删除该申请类型？" @confirm="remove(row.id)">
            <template #reference>
              <el-button type="danger" link>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawerVisible" :title="editorTitle" size="70%" destroy-on-close>
      <div class="drawer-body">
        <el-form :model="form" label-width="110px" :rules="rules" ref="formRef">
          <el-divider content-position="left">基础信息</el-divider>
          <el-form-item label="申请名称" prop="name">
            <el-input v-model="form.name" placeholder="例如 学生请假" />
          </el-form-item>
          <el-form-item label="所属分类" prop="category">
            <el-select v-model="form.category" placeholder="选择分类">
              <el-option label="学籍管理" value="学籍管理" />
              <el-option label="课程管理" value="课程管理" />
              <el-option label="成绩管理" value="成绩管理" />
              <el-option label="证书办理" value="证书办理" />
              <el-option label="其他服务" value="其他服务" />
            </el-select>
          </el-form-item>
          <el-form-item label="适用角色" prop="role_scope">
            <el-radio-group v-model="form.role_scope">
              <el-radio label="all">学生与教师</el-radio>
              <el-radio label="student">仅学生</el-radio>
              <el-radio label="teacher">仅教师</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="显示状态" prop="status">
            <el-select v-model="form.status">
              <el-option label="启用" value="available" />
              <el-option label="暂停" value="paused" />
            </el-select>
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="form.display_order" :min="0" />
          </el-form-item>
          <el-form-item label="入口位置">
            <el-checkbox-group v-model="form.entry_positions">
              <el-checkbox label="service_hall">办事大厅</el-checkbox>
              <el-checkbox label="dashboard">首页快捷入口</el-checkbox>
              <el-checkbox label="personal_center">个人中心</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="未读提醒">
            <el-switch v-model="form.unread_badge" />
          </el-form-item>
          <el-form-item label="图标">
            <el-input v-model="form.icon" placeholder="Element Plus 图标名，可选" />
          </el-form-item>
          <el-form-item label="办理时长" prop="processing_time">
            <el-input v-model="form.processing_time" placeholder="例如 3个工作日" />
          </el-form-item>
          <el-form-item label="办事指南">
            <el-input type="textarea" :rows="3" v-model="form.guide" placeholder="富文本/Markdown，支持简单 HTML" />
          </el-form-item>
          <el-form-item label="申请条件">
            <el-input type="textarea" :rows="2" v-model="form.apply_conditions" />
          </el-form-item>

          <el-divider content-position="left">表单字段</el-divider>
          <el-alert title="字段配置将直接用于学生/教师端动态表单" type="success" :closable="false" class="mb-2" />
          <div class="card-grid">
            <el-card v-for="(field, idx) in form.apply_fields" :key="idx" shadow="hover" class="field-card">
              <div class="field-header">
                <strong>{{ field.name || '未命名字段' }}</strong>
                <el-space>
                  <el-tag size="small">{{ renderFieldType(field.type) }}</el-tag>
                  <el-switch v-model="field.required" active-text="必填" size="small" />
                  <el-button text type="danger" size="small" @click="removeField(idx)">删除</el-button>
                </el-space>
              </div>
              <el-input v-model="field.name" placeholder="字段显示名" class="mb-2" />
              <el-select v-model="field.type" placeholder="字段类型" class="mb-2">
                <el-option label="单行文本" value="input" />
                <el-option label="多行文本" value="textarea" />
                <el-option label="下拉选择" value="select" />
                <el-option label="日期时间" value="datetime" />
                <el-option label="数字" value="number" />
              </el-select>
              <el-input
                v-if="field.type === 'select'"
                type="textarea"
                :rows="2"
                v-model="field.optionsText"
                placeholder="选项，换行分隔"
                @change="syncOptions(field)"
              />
            </el-card>
          </div>
          <el-button type="primary" link @click="addField">+ 添加字段</el-button>

          <el-divider content-position="left">材料要求</el-divider>
          <el-alert title="配置上传或文本材料，前端‘材料上传’区域将据此生成" type="info" :closable="false" class="mb-2" />
          <div class="card-grid">
            <el-card v-for="(mat, idx) in form.required_materials" :key="idx" shadow="hover" class="field-card">
              <div class="field-header">
                <strong>{{ mat.name || '未命名材料' }}</strong>
                <el-space>
                  <el-switch v-model="mat.required" active-text="必填" size="small" />
                  <el-button text type="danger" size="small" @click="removeMaterial(idx)">删除</el-button>
                </el-space>
              </div>
              <el-input v-model="mat.name" placeholder="材料名称，例如 证明材料" class="mb-2" />
              <el-select v-model="mat.type" placeholder="材料类型" class="mb-2">
                <el-option label="文件上传" value="file" />
                <el-option label="文本填写" value="text" />
              </el-select>
              <el-input
                v-model="mat.placeholder"
                type="textarea"
                :rows="2"
                placeholder="占位提示（可选）"
              />
            </el-card>
          </div>
          <el-button type="primary" link @click="addMaterial">+ 添加材料</el-button>

          <el-divider content-position="left">审批流程</el-divider>
          <el-card v-for="(node, idx) in form.approval_flow" :key="idx" class="mb-2">
            <div class="field-header">
              <div>节点 {{ idx + 1 }}</div>
              <el-button text type="danger" size="small" @click="removeNode(idx)">删除</el-button>
            </div>
            <el-input v-model="node.name" placeholder="节点名称，如 班主任审核" class="mb-2" />
            <el-select v-model="node.role" placeholder="审批人范围" class="mb-2">
              <el-option label="班主任" value="head_teacher" />
              <el-option label="年级主任" value="grade_director" />
              <el-option label="教研组长" value="teaching_research" />
              <el-option label="教务处" value="academic_office" />
              <el-option label="管理员" value="admin" />
            </el-select>
            <el-switch v-model="node.allow_batch" active-text="允许批量" />
          </el-card>
          <el-button type="primary" link @click="addNode">+ 添加节点</el-button>

          <el-divider content-position="left">时长与超时规则</el-divider>
          <el-form-item label="提交有效期(小时)">
            <el-input-number v-model="form.submit_expire_hours" :min="1" :max="720" :step="1" />
          </el-form-item>
          <el-form-item label="审核时长上限(小时)">
            <el-input-number v-model="form.review_timeout_hours" :min="1" :max="720" :step="1" />
          </el-form-item>
          <el-form-item label="超时策略">
            <el-select v-model="form.timeout_strategy" placeholder="选择策略">
              <el-option label="仅提醒" value="notify" />
              <el-option label="自动驳回" value="auto_reject" />
              <el-option label="自动通过" value="auto_approve" />
            </el-select>
          </el-form-item>
          <el-form-item label="超时提醒渠道">
            <el-checkbox-group v-model="form.timeout_channels">
              <el-checkbox label="message">系统消息</el-checkbox>
              <el-checkbox label="popup">前端弹窗</el-checkbox>
              <el-checkbox label="email">邮件</el-checkbox>
              <el-checkbox label="sms">短信</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-divider content-position="left">通知规则</el-divider>
          <el-form-item label="事件渠道">
            <el-table :data="notificationRows" border size="small" style="width: 100%">
              <el-table-column prop="label" label="事件" width="140" />
              <el-table-column label="渠道">
                <template #default="{ row }">
                  <el-checkbox-group v-model="row.channels">
                    <el-checkbox label="message">系统消息</el-checkbox>
                    <el-checkbox label="popup">前端弹窗</el-checkbox>
                    <el-checkbox label="email">邮件</el-checkbox>
                    <el-checkbox label="sms">短信</el-checkbox>
                  </el-checkbox-group>
                </template>
              </el-table-column>
            </el-table>
          </el-form-item>

          <el-divider content-position="left">状态配置</el-divider>
          <el-table :data="statusRows" border size="small" style="width: 100%" class="mb-3">
            <el-table-column prop="key" label="状态键" width="140" />
            <el-table-column label="展示文案" width="200">
              <template #default="{ row }">
                <el-input v-model="row.label" />
              </template>
            </el-table-column>
            <el-table-column label="颜色">
              <template #default="{ row }">
                <el-select v-model="row.color" style="width: 140px">
                  <el-option label="primary" value="primary" />
                  <el-option label="success" value="success" />
                  <el-option label="warning" value="warning" />
                  <el-option label="danger" value="danger" />
                  <el-option label="info" value="info" />
                </el-select>
              </template>
            </el-table-column>
          </el-table>

          <div class="drawer-footer">
            <el-button @click="drawerVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

interface ServiceItemRow {
  id: number
  name: string
  category: string
  status: string
  icon?: string
  processing_time: string
  config?: any
  apply_fields?: any[]
  guide?: string
  apply_conditions?: string
  required_materials?: any[]
  process?: any[]
}

const loading = ref(false)
const saving = ref(false)
const items = ref<ServiceItemRow[]>([])
const drawerVisible = ref(false)
const formRef = ref()
const editorTitle = computed(() => (editingId.value ? '编辑申请类型' : '新增申请类型'))
const editingId = ref<number | null>(null)

const defaultStatusMeta = {
  pending: { label: '待审核', color: 'warning' },
  processing: { label: '办理中', color: 'primary' },
  approved: { label: '已通过', color: 'success' },
  rejected: { label: '已驳回', color: 'danger' },
  timeout: { label: '已超时', color: 'info' },
  withdrawn: { label: '已撤回', color: 'info' },
}

const form = reactive<any>({
  name: '',
  category: '',
  role_scope: 'all',
  status: 'available',
  display_order: 0,
  entry_positions: ['service_hall'],
  unread_badge: false,
  icon: '',
  processing_time: '',
  guide: '',
  apply_conditions: '',
  apply_fields: [],
  required_materials: [],
  approval_flow: [],
  submit_expire_hours: null,
  review_timeout_hours: null,
  timeout_strategy: 'notify',
  timeout_channels: ['message'],
  notification_rules: {
    submit: ['message'],
    approved: ['message'],
    rejected: ['message'],
    timeout: ['message'],
  },
  status_meta: { ...defaultStatusMeta },
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  role_scope: [{ required: true, message: '请选择角色', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  processing_time: [{ required: true, message: '请输入办理时长', trigger: 'blur' }],
}

const notificationRows = computed(() => [
  { key: 'submit', label: '提交', channels: form.notification_rules.submit },
  { key: 'approved', label: '通过', channels: form.notification_rules.approved },
  { key: 'rejected', label: '驳回', channels: form.notification_rules.rejected },
  { key: 'timeout', label: '超时', channels: form.notification_rules.timeout },
])

const statusRows = computed(() => Object.keys(form.status_meta).map(key => ({
  key,
  label: form.status_meta[key]?.label || key,
  color: form.status_meta[key]?.color || 'info',
})))

const renderRole = (role?: string) => {
  if (role === 'student') return '学生'
  if (role === 'teacher') return '教师'
  return '学生/教师'
}

const renderEntry = (pos: string) => {
  const map: Record<string, string> = {
    service_hall: '办事大厅',
    dashboard: '首页快捷入口',
    personal_center: '个人中心',
  }
  return map[pos] || pos
}

const renderFieldType = (type: string) => {
  const map: Record<string, string> = {
    input: '单行文本',
    textarea: '多行文本',
    select: '下拉',
    datetime: '日期时间',
    number: '数字',
  }
  return map[type] || type
}

const resetForm = () => {
  editingId.value = null
  Object.assign(form, {
    name: '',
    category: '',
    role_scope: 'all',
    status: 'available',
    display_order: 0,
    entry_positions: ['service_hall'],
    unread_badge: false,
    icon: '',
    processing_time: '',
    guide: '',
    apply_conditions: '',
    required_materials: form.required_materials.map((m: any) => ({
      name: m.name,
      type: m.type || 'file',
      required: m.required !== false,
      placeholder: m.placeholder || ''
    })),
    apply_fields: [],
    approval_flow: [{ name: '班主任审核', role: 'head_teacher', allow_batch: false }],
    submit_expire_hours: null,
    review_timeout_hours: null,
    timeout_strategy: 'notify',
    timeout_channels: ['message'],
    notification_rules: {
      submit: ['message'],
      approved: ['message'],
      rejected: ['message'],
      timeout: ['message'],
    },
    status_meta: { ...defaultStatusMeta },
  })
}

const openEditor = (row?: any) => {
  if (!row) {
    resetForm()
    drawerVisible.value = true
    return
  }
  editingId.value = row.id
  const cfg = row.config || {}
  Object.assign(form, {
    name: row.name,
    category: row.category,
    role_scope: cfg.role_scope || 'all',
    status: row.status,
    display_order: cfg.display_order ?? 0,
    entry_positions: cfg.entry_positions?.length ? cfg.entry_positions : ['service_hall'],
    unread_badge: cfg.unread_badge ?? false,
    icon: row.icon,
    processing_time: row.processing_time,
    guide: row.guide || '',
    apply_conditions: row.apply_conditions || '',
    apply_fields: (row.apply_fields || []).map((f: any) => ({ ...f, optionsText: (f.options || []).join('\n') })),
    required_materials: (row.required_materials || []).map((m: any) => ({
      name: m.name,
      type: m.type || 'file',
      required: m.required !== false,
      placeholder: m.placeholder || '',
    })),
    approval_flow: cfg.approval_flow?.length ? cfg.approval_flow : [{ name: '班主任审核', role: 'head_teacher', allow_batch: false }],
    submit_expire_hours: cfg.duration_rules?.submit_expire_hours ?? null,
    review_timeout_hours: cfg.duration_rules?.review_timeout_hours ?? null,
    timeout_strategy: cfg.duration_rules?.timeout_strategy || 'notify',
    timeout_channels: cfg.duration_rules?.timeout_channels || ['message'],
    notification_rules: cfg.notification_rules?.submit ? cfg.notification_rules : {
      submit: ['message'],
      approved: ['message'],
      rejected: ['message'],
      timeout: ['message'],
    },
    status_meta: Object.keys(cfg.status_meta || {}).length ? cfg.status_meta : { ...defaultStatusMeta },
  })
  drawerVisible.value = true
}

const syncOptions = (field: any) => {
  if (field.optionsText) {
    field.options = field.optionsText.split('\n').map((t: string) => t.trim()).filter(Boolean)
  } else {
    field.options = []
  }
}

const addField = () => {
  form.apply_fields.push({ name: '字段', type: 'input', required: true, options: [], optionsText: '' })
}

const removeField = (idx: number) => {
  form.apply_fields.splice(idx, 1)
}

const addMaterial = () => {
  form.required_materials.push({ name: '材料', type: 'file', required: true, placeholder: '' })
}

const removeMaterial = (idx: number) => {
  form.required_materials.splice(idx, 1)
}

const addNode = () => {
  form.approval_flow.push({ name: '新节点', role: 'admin', allow_batch: false })
}

const removeNode = (idx: number) => {
  form.approval_flow.splice(idx, 1)
}

const syncNotificationRules = () => {
  form.notification_rules = notificationRows.value.reduce((acc: any, cur) => {
    acc[cur.key] = cur.channels || []
    return acc
  }, {})
}

const syncStatusMeta = () => {
  form.status_meta = statusRows.value.reduce((acc: any, cur) => {
    acc[cur.key] = { label: cur.label, color: cur.color }
    return acc
  }, {})
}

const buildPayload = () => {
  syncNotificationRules()
  syncStatusMeta()

  return {
    id: editingId.value || undefined,
    name: form.name,
    category: form.category,
    icon: form.icon || undefined,
    processing_time: form.processing_time,
    status: form.status,
    guide: form.guide || '',
    apply_conditions: form.apply_conditions || '',
    required_materials: [],
    process: [],
    apply_fields: form.apply_fields.map((f: any) => ({ name: f.name, type: f.type, required: !!f.required, options: f.options || [] })),
    config: {
      role_scope: form.role_scope,
      display_order: form.display_order,
      entry_positions: form.entry_positions,
      unread_badge: form.unread_badge,
      duration_rules: {
        submit_expire_hours: form.submit_expire_hours,
        review_timeout_hours: form.review_timeout_hours,
        timeout_strategy: form.timeout_strategy,
        timeout_channels: form.timeout_channels,
      },
      approval_flow: form.approval_flow,
      notification_rules: form.notification_rules,
      status_meta: form.status_meta,
    },
  }
}

const save = async () => {
  syncNotificationRules()
  syncStatusMeta()
  await formRef.value?.validate()
  saving.value = true
  try {
    const payload = buildPayload()
    await axios.post('/api/service/admin/config/type', payload)
    ElMessage.success('保存成功')
    drawerVisible.value = false
    fetchList()
  } catch (error: any) {
    console.error('保存失败', error)
    ElMessage.error(error?.response?.data?.detail || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const fetchList = async () => {
  loading.value = true
  try {
    const { data } = await axios.get('/api/service/admin/config/types')
    items.value = data || []
  } catch (error) {
    console.error('获取配置失败', error)
    ElMessage.error('获取配置失败')
  } finally {
    loading.value = false
  }
}

const remove = async (id: number) => {
  try {
    await axios.delete(`/api/service/admin/config/type/${id}`)
    ElMessage.success('删除成功')
    fetchList()
  } catch (error) {
    console.error('删除失败', error)
    ElMessage.error('删除失败')
  }
}

fetchList()
</script>

<style scoped>
.service-config {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.subtitle {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
}

.actions {
  display: flex;
  gap: 10px;
}

.drawer-body {
  padding-right: 12px;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
}

.drawer-footer {
  margin-top: 16px;
  text-align: right;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  margin-bottom: 10px;
}

.field-card {
  border: 1px solid var(--el-border-color-lighter);
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
</style>
