<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Delete, Upload, Download, Edit, RefreshLeft } from '@element-plus/icons-vue'

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
  role: ''
})
const selectedRows = ref<User[]>([])
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

// 表单校验规则
const rules = {
  account: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  dept: [{ required: true, message: '请输入专业/部门', trigger: 'blur' }]
}

// --- 4. 核心逻辑 ---

// 加载数据 (后端接口)
const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/admin/user/list', {
      params: {
        role: searchQuery.role || undefined,
        keyword: searchQuery.keyword || undefined
      },
      headers: getAuthHeaders()
    })
    tableData.value = res.data
  } catch (e) {
    ElMessage.error('获取用户列表失败')
    tableData.value = []
  } finally {
    loading.value = false
  }
}

// 状态切换
const handleStatusChange = async (row: User) => {
  try {
    await axios.put('/api/admin/user/status', {
      user_id: row.id,
      status: row.status
    }, {
      headers: getAuthHeaders()
    })
    ElMessage.success('状态更新成功')
  } catch (e: any) {
    row.status = !row.status // 恢复原状
    ElMessage.error(e.response?.data?.detail || '状态更新失败')
  }
}

// 角色名称映射
const getRoleName = (role: string) => {
  const map: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
  return map[role] || role
}

// 角色标签颜色
const getRoleTagType = (role: string) => {
  const map: Record<string, string> = { student: 'primary', teacher: 'success', admin: 'warning' }
  return map[role] as any
}

// 打开新增弹窗
const handleAdd = () => {
  dialogType.value = 'add'
  formData.id = undefined
  formData.account = ''
  formData.name = ''
  formData.role = 'student'
  formData.dept = ''
  formData.grade = ''
  formData.entryTime = ''
  formData.status = true
  dialogVisible.value = true
}

// 打开编辑弹窗
const handleEdit = (row: User) => {
  dialogType.value = 'edit'
  formData.id = row.id
  formData.account = row.account
  formData.name = row.name
  formData.role = row.role
  formData.dept = row.dept
  formData.grade = row.grade
  formData.entryTime = row.entryTime
  formData.status = row.status
  dialogVisible.value = true
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      try {
        if (dialogType.value === 'add') {
          // 调用创建用户 API
          await axios.post('/api/admin/user/add', {
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
          ElMessage.success('用户添加成功')
        } else {
          // 调用更新用户 API
          await axios.put(`/api/admin/user/edit`, {
            name: formData.name,
            dept: formData.dept,
            grade: formData.grade,
            entry_time: formData.entryTime,
            status: formData.status
          }, {
            params: { user_id: formData.id },
            headers: getAuthHeaders()
          })
          ElMessage.success('用户信息更新成功')
        }
        dialogVisible.value = false
        loadData() // 重新加载数据
      } catch (e: any) {
        ElMessage.error(e.response?.data?.detail || '操作失败')
      }
    }
  })
}

// 删除用户
const handleDelete = (row: User) => {
  ElMessageBox.confirm(`确定要删除用户 "${row.name}" 吗?`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await axios.delete(`/api/admin/user/delete`, { 
        params: { user_id: row.id },
        headers: getAuthHeaders()
      })
      ElMessage.success('删除成功')
      loadData() // 重新加载数据
    } catch (e: any) {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  })
}

// 批量删除
const handleBatchDelete = () => {
  if (selectedRows.value.length === 0) return
  ElMessageBox.confirm(`确定要删除选中的 ${selectedRows.value.length} 个用户吗?`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      // 批量删除
      await Promise.all(
        selectedRows.value.map(u => 
          axios.delete(`/api/admin/user/delete`, { 
            params: { user_id: u.id },
            headers: getAuthHeaders()
          })
        )
      )
      selectedRows.value = [] // 清空选中
      ElMessage.success('批量删除成功')
      loadData() // 重新加载数据
    } catch (e: any) {
      ElMessage.error(e.response?.data?.detail || '批量删除失败')
    }
  })
}

// 重置密码
const handleResetPwd = (row: User) => {
  ElMessageBox.confirm(`确定要重置用户 "${row.name}" 的密码为 123456 吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(async () => {
    try {
      await axios.post(`/api/admin/user/reset-password`, { user_id: row.id }, {
        headers: getAuthHeaders()
      })
      ElMessage.success('密码已重置为 123456')
    } catch (e: any) {
      ElMessage.error(e.response?.data?.detail || '重置密码失败')
    }
  })
}

// 模拟导入
const handleImport = () => {
  ElMessage.success({
    message: '模拟导入成功！新增用户 5 人，失败 0 人',
    duration: 3000
  })
  // 模拟插入数据
  for(let i=0; i<5; i++) {
    tableData.value.unshift({
      id: Date.now() + i,
      account: `NEW${2024000 + i}`,
      name: `导入用户${i+1}`,
      role: 'student',
      dept: '导入测试专业',
      grade: '2024级',
      status: true,
      createTime: new Date().toISOString().split('T')[0]
    })
  }
}

// 模拟导出
const handleExport = () => {
  ElMessage.success('正在导出 Excel 文件... (模拟)')
  setTimeout(() => {
    // 创建一个虚拟的下载链接 (仅演示)
    const link = document.createElement('a')
    link.download = `用户列表_${new Date().getTime()}.xlsx`
    link.href = '#'
    link.click()
    ElMessage.success('导出成功！')
  }, 1000)
}

// 表格选中变化
const handleSelectionChange = (val: User[]) => {
  selectedRows.value = val
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="user-manage-container">
    <!-- 顶部操作栏 -->
    <el-card class="operation-card">
      <div class="operation-bar">
        <div class="left-actions">
          <el-button type="primary" :icon="Plus" @click="handleAdd" color="#FAAD14" style="color: white">新增用户</el-button>
          <el-button type="danger" :icon="Delete" :disabled="selectedRows.length === 0" @click="handleBatchDelete">批量删除</el-button>
          <el-button :icon="Upload" @click="handleImport">导入 Excel</el-button>
          <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
        </div>
        <div class="right-search">
          <el-select v-model="searchQuery.role" placeholder="所有角色" style="width: 120px; margin-right: 10px" clearable @change="loadData">
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
          <el-input
            v-model="searchQuery.keyword"
            placeholder="搜索账号/姓名/ID"
            style="width: 250px"
            clearable
            @clear="loadData"
            @keyup.enter="loadData"
          >
            <template #append>
              <el-button :icon="Search" @click="loadData" />
            </template>
          </el-input>
        </div>
      </div>
    </el-card>

    <!-- 用户列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="tableData"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        :row-class-name="({ row }) => row.status ? '' : 'disabled-row'"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" sortable />
        <el-table-column prop="account" label="账号" width="120" sortable />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">{{ getRoleName(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="专业/部门" min-width="150">
          <template #default="{ row }">
            {{ row.dept }}
            <span v-if="row.role === 'student'" class="sub-info">({{ row.grade }})</span>
            <span v-if="row.role === 'teacher'" class="sub-info">(入职: {{ row.entryTime }})</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.status" active-color="#13ce66" inactive-color="#ff4949" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="120" sortable />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" :disabled="!row.status" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="warning" :icon="RefreshLeft" @click="handleResetPwd(row)">重置密码</el-button>
            <el-button link type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增用户' : '编辑用户'"
      width="500px"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="账号" prop="account">
          <el-input v-model="formData.account" placeholder="请输入学号/工号" :disabled="dialogType === 'edit'" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" placeholder="请选择角色">
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        
        <!-- 角色联动字段 -->
        <el-form-item label="专业" prop="dept" v-if="formData.role === 'student'">
          <el-input v-model="formData.dept" placeholder="请输入专业" />
        </el-form-item>
        <el-form-item label="年级" prop="grade" v-if="formData.role === 'student'">
          <el-input v-model="formData.grade" placeholder="例如：2023级" />
        </el-form-item>
        
        <el-form-item label="部门" prop="dept" v-if="formData.role !== 'student'">
          <el-input v-model="formData.dept" placeholder="请输入所属部门" />
        </el-form-item>
        <el-form-item label="入职时间" prop="entryTime" v-if="formData.role === 'teacher'">
          <el-date-picker v-model="formData.entryTime" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio :label="true">启用</el-radio>
            <el-radio :label="false">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" color="#FAAD14" style="color: white">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-manage-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.table-card {
  flex: 1;
  overflow: hidden;
}
.sub-info {
  font-size: 12px;
  color: #909399;
  margin-left: 5px;
}
/* 禁用行样式 */
:deep(.el-table .disabled-row) {
  background: #f5f7fa;
  color: #c0c4cc;
}
/* Hover 效果 */
:deep(.el-table__body tr:hover > td) {
  background-color: #FFF7E6 !important;
}
</style>
