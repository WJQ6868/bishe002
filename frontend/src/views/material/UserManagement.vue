<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'

// --- 1. 类型定义 ---
interface User {
  id: number
  account: string
  name: string
  role: 'student' | 'teacher' | 'admin'
  dept: string // 专业或部门
  grade?: string // 年级 (学生特有)
  entryTime?: string // 入职时间 (教师特有)
  status: boolean // true: 启用, false: 禁用
  createTime: string
}

interface UserForm {
  id?: number
  account: string
  name: string
  role: 'student' | 'teacher' | 'admin'
  dept: string
  grade?: string
  entryTime?: string
  status: boolean
}

// --- 2. 选项 ---
const roles = ['student', 'teacher', 'admin']
const depts = ['计算机科学与技术', '软件工程', '人工智能', '教务处', '学生处']

// --- 3. 状态管理 ---
const loading = ref(false)
const tableData = ref<User[]>([])
const searchQuery = reactive({
  keyword: '',
  role: null as string | null
})
const selectedRows = ref<number[]>([])
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const formRef = ref()
const formData = reactive<UserForm>({
  account: '',
  name: '',
  role: 'student',
  dept: '',
  grade: '',
  entryTime: '',
  status: true
})

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const confirmDialog = reactive({
  show: false,
  title: '',
  text: '',
  loading: false,
  onConfirm: async () => {}
})

// Rules
const rules = {
  required: (v: any) => !!v || '此项为必填项',
}

// --- 4. 核心逻辑 ---
const showMessage = (text: string, color: 'success' | 'warning' | 'info' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

const showConfirm = (title: string, text: string, onConfirm: () => Promise<void> | void) => {
  confirmDialog.title = title
  confirmDialog.text = text
  confirmDialog.onConfirm = onConfirm
  confirmDialog.loading = false
  confirmDialog.show = true
}

const handleConfirmAction = async () => {
  try {
    confirmDialog.loading = true
    await confirmDialog.onConfirm()
  } finally {
    confirmDialog.loading = false
    confirmDialog.show = false
  }
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/user/list', {
      params: {
        role: searchQuery.role || undefined,
        keyword: searchQuery.keyword || undefined
      },
      headers: getAuthHeaders()
    })
    tableData.value = res.data
    selectedRows.value = []
  } catch (e) {
    showMessage('获取用户列表失败', 'warning')
    tableData.value = []
  } finally {
    loading.value = false
  }
}

const getRoleName = (role: string) => {
  const map: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
  return map[role] || role
}

const getRoleColor = (role: string) => {
  const map: Record<string, string> = { student: 'primary', teacher: 'success', admin: 'warning' }
  return map[role] || 'grey'
}

const handleAdd = () => {
  dialogType.value = 'add'
  Object.assign(formData, {
    id: undefined,
    account: '',
    name: '',
    role: 'student',
    dept: '',
    grade: '',
    entryTime: '',
    status: true
  })
  dialogVisible.value = true
}

const handleEdit = (row: User) => {
  dialogType.value = 'edit'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  try {
    if (dialogType.value === 'add') {
      await axios.post('/api/user/create', {
        account: formData.account,
        name: formData.name,
        password: '123456',
        role: formData.role,
        dept: formData.dept,
        grade: formData.grade,
        entry_time: formData.entryTime
      }, {
        headers: getAuthHeaders()
      })
      showMessage('用户添加成功')
    } else if (formData.id) {
      await axios.put(`/api/user/${formData.id}`, {
        name: formData.name,
        dept: formData.dept,
        grade: formData.grade,
        entry_time: formData.entryTime,
        status: formData.status
      }, {
        headers: getAuthHeaders()
      })
      showMessage('用户信息更新成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    showMessage(detail || '操作失败', 'warning')
  }
}

const handleDelete = (row: User) => {
  showConfirm('删除警告', `确定要删除用户 "${row.name}" 吗?`, async () => {
    try {
      await axios.delete(`/api/user/${row.id}`, {
        headers: getAuthHeaders()
      })
      showMessage('删除成功')
      await loadData()
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      showMessage(detail || '删除失败', 'warning')
    }
  })
}

const handleBatchDelete = () => {
  if (selectedRows.value.length === 0) return
  showConfirm('批量删除', `确定要删除选中的 ${selectedRows.value.length} 个用户吗?`, async () => {
    try {
      await Promise.all(selectedRows.value.map(id => axios.delete(`/api/user/${id}`, {
        headers: getAuthHeaders()
      })))
      selectedRows.value = []
      showMessage('批量删除成功')
      await loadData()
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      showMessage(detail || '批量删除失败', 'warning')
    }
  })
}

const handleResetPwd = (row: User) => {
  showConfirm('重置密码', `确定要重置用户 "${row.name}" 的密码为 123456 吗?`, async () => {
    try {
      await axios.post(`/api/user/${row.id}/reset-password`, null, {
        headers: getAuthHeaders()
      })
      showMessage('密码已重置为 123456', 'info')
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      showMessage(detail || '重置密码失败', 'warning')
    }
  })
}

const handleImport = () => {
  showMessage('导入功能建设中，敬请期待', 'info')
}

const handleExport = () => {
  showMessage('导出功能建设中，敬请期待', 'info')
}

const headers = [
  { title: 'ID', key: 'id', align: 'start' },
  { title: '账号', key: 'account' },
  { title: '姓名', key: 'name' },
  { title: '角色', key: 'role' },
  { title: '专业/部门', key: 'deptInfo' },
  { title: '状态', key: 'status' },
  { title: '创建时间', key: 'createTime' },
  { title: '操作', key: 'actions', sortable: false, align: 'end', width: '180px' },
]

onMounted(() => {
  loadData()
})

const rowProps = (data: { item: User }) => {
  return {
    class: data.item.status ? '' : 'bg-grey-lighten-4 text-grey'
  }
}

</script>

<template>
  <div class="user-manage-container">
    <!-- 顶部操作栏 -->
    <v-card class="mb-4 pa-4">
      <div class="d-flex flex-wrap align-center justify-space-between gap-4">
        <div class="d-flex gap-2">
          <v-btn color="warning" prepend-icon="mdi-plus" @click="handleAdd">新增用户</v-btn>
          <v-btn color="error" variant="outlined" prepend-icon="mdi-delete" :disabled="selectedRows.length === 0" @click="handleBatchDelete">批量删除</v-btn>
          <v-btn variant="text" prepend-icon="mdi-upload" @click="handleImport">导入</v-btn>
          <v-btn variant="text" prepend-icon="mdi-download" @click="handleExport">导出</v-btn>
        </div>
        <div class="d-flex gap-2 align-center" style="min-width: 400px">
          <v-select
            v-model="searchQuery.role"
            :items="[{ title: '所有角色', value: null }, { title: '学生', value: 'student' }, { title: '教师', value: 'teacher' }, { title: '管理员', value: 'admin' }]"
            placeholder="角色"
            density="compact"
            hide-details
            clearable
            style="max-width: 140px"
            @update:model-value="loadData"
          ></v-select>
          <v-text-field
            v-model="searchQuery.keyword"
            placeholder="搜索账号/姓名/ID"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            hide-details
            style="max-width: 240px"
            @keyup.enter="loadData"
            @click:append-inner="loadData"
          ></v-text-field>
        </div>
      </div>
    </v-card>

    <!-- 用户列表 -->
    <v-card>
      <v-data-table
        v-model="selectedRows"
        :headers="headers"
        :items="tableData"
        :loading="loading"
        item-value="id"
        show-select
        hover
      >
        <template #item.role="{ item }">
          <v-chip :color="getRoleColor(item.role)" size="small" label>
            {{ getRoleName(item.role) }}
          </v-chip>
        </template>

        <template #item.deptInfo="{ item }">
          {{ item.dept }}
          <span v-if="item.role === 'student'" class="text-caption text-grey ms-1">({{ item.grade }})</span>
          <span v-if="item.role === 'teacher'" class="text-caption text-grey ms-1">(入职: {{ item.entryTime }})</span>
        </template>

        <template #item.status="{ item }">
          <v-switch
            v-model="item.status"
            color="success"
            hide-details
            density="compact"
            disabled
          ></v-switch>
        </template>

        <template #item.actions="{ item }">
          <v-btn icon size="small" variant="text" color="primary" :disabled="!item.status" @click="handleEdit(item)">
            <v-icon>mdi-pencil</v-icon>
            <v-tooltip activator="parent" location="top">编辑</v-tooltip>
          </v-btn>
          <v-btn icon size="small" variant="text" color="warning" @click="handleResetPwd(item)">
            <v-icon>mdi-refresh</v-icon>
            <v-tooltip activator="parent" location="top">重置密码</v-tooltip>
          </v-btn>
          <v-btn icon size="small" variant="text" color="error" @click="handleDelete(item)">
            <v-icon>mdi-delete</v-icon>
            <v-tooltip activator="parent" location="top">删除</v-tooltip>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- 新增/编辑弹窗 -->
    <v-dialog v-model="dialogVisible" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ dialogType === 'add' ? '新增用户' : '编辑用户' }}</span>
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-text-field
              v-model="formData.account"
              label="账号"
              placeholder="请输入学号/工号"
              :disabled="dialogType === 'edit'"
              :rules="[rules.required]"
              required
            ></v-text-field>
            <v-text-field
              v-model="formData.name"
              label="姓名"
              placeholder="请输入姓名"
              :rules="[rules.required]"
              required
            ></v-text-field>
            <v-select
              v-model="formData.role"
              :items="[{ title: '学生', value: 'student' }, { title: '教师', value: 'teacher' }, { title: '管理员', value: 'admin' }]"
              label="角色"
              :rules="[rules.required]"
              required
            ></v-select>

            <template v-if="formData.role === 'student'">
              <v-text-field
                v-model="formData.dept"
                label="专业"
                placeholder="请输入专业"
                :rules="[rules.required]"
              ></v-text-field>
              <v-text-field
                v-model="formData.grade"
                label="年级"
                placeholder="例如：2023级"
              ></v-text-field>
            </template>

            <template v-else>
              <v-text-field
                v-model="formData.dept"
                label="部门"
                placeholder="请输入所属部门"
                :rules="[rules.required]"
              ></v-text-field>
              <v-text-field
                v-if="formData.role === 'teacher'"
                v-model="formData.entryTime"
                type="date"
                label="入职时间"
              ></v-text-field>
            </template>

            <v-radio-group v-model="formData.status" inline label="状态">
              <v-radio :value="true" label="启用" color="success"></v-radio>
              <v-radio :value="false" label="禁用" color="error"></v-radio>
            </v-radio-group>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="dialogVisible = false">取消</v-btn>
          <v-btn color="warning" variant="text" @click="handleSubmit">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 全局提示组件 -->
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
          <v-btn
            color="grey"
            variant="text"
            :disabled="confirmDialog.loading"
            @click="confirmDialog.show = false"
          >取消</v-btn>
          <v-btn
            color="primary"
            variant="text"
            :loading="confirmDialog.loading"
            :disabled="confirmDialog.loading"
            @click="handleConfirmAction"
          >确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.gap-2 { gap: 8px; }
.gap-4 { gap: 16px; }
</style>
