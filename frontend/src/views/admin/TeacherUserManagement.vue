<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, RefreshLeft, Search } from '@element-plus/icons-vue'

interface Teacher {
  id: number
  teacher_no: string
  name: string
  gender: number
  age?: number
  mobile?: string
  email?: string
  dept_id: number
  post_type: number
  subject?: string
  title?: number
  entry_time?: string
  leave_status: number
  teach_years?: number
  role?: string
  permissions?: Record<string, any>
  status: number
  create_time: string
  update_time: string
}

interface TeacherForm {
  teacher_no: string
  name: string
  gender: number | null
  age?: number | null
  mobile?: string
  email?: string
  dept_id: number | null
  post_type: number | null
  subject?: string
  title?: number | null
  entry_time?: string
  leave_status: number
  teach_years?: number | null
  role?: string
  permissions?: Record<string, any>
  status: number
}

const loading = ref(false)
const tableData = ref<Teacher[]>([])
const editingId = ref<number | null>(null)
const searchForm = reactive({
  keyword: '',
  dept_id: '' as string | number,
  status: '' as string | number,
  post_type: '' as string | number,
})

const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const formRef = ref()
const formData = reactive<TeacherForm>({
  teacher_no: '',
  name: '',
  gender: 1,
  age: null,
  mobile: '',
  email: '',
  dept_id: null,
  post_type: null,
  subject: '',
  title: null,
  entry_time: '',
  leave_status: 1,
  teach_years: null,
  role: 'teacher',
  permissions: {},
  status: 1,
})

const rules = {
  teacher_no: [],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  dept_id: [{ required: true, message: '请输入/选择部门ID', trigger: 'blur' }],
  post_type: [{ required: true, message: '请选择岗位类型', trigger: 'change' }],
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await axios.get('admin/teacher/list', {
      params: {
        keyword: searchForm.keyword || undefined,
        dept_id: searchForm.dept_id || undefined,
        post_type: searchForm.post_type || undefined,
        status: searchForm.status || undefined,
      },
      headers: getAuthHeaders(),
    })
    tableData.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取教职工列表失败')
    tableData.value = []
  } finally {
    loading.value = false
  }
}

const openAdd = () => {
  dialogType.value = 'add'
  editingId.value = null
  Object.assign(formData, {
    teacher_no: '',
    name: '',
    gender: 1,
    age: null,
    mobile: '',
    email: '',
    dept_id: null,
    post_type: null,
    subject: '',
    title: null,
    entry_time: '',
    leave_status: 1,
    teach_years: null,
    role: 'teacher',
    permissions: {},
    status: 1,
  })
  dialogVisible.value = true
}

const openEdit = (row: Teacher) => {
  dialogType.value = 'edit'
  editingId.value = row.id
  Object.assign(formData, {
    teacher_no: row.teacher_no,
    name: row.name,
    gender: row.gender,
    age: row.age ?? null,
    mobile: row.mobile || '',
    email: row.email || '',
    dept_id: row.dept_id,
    post_type: row.post_type,
    subject: row.subject || '',
    title: row.title ?? null,
    entry_time: row.entry_time ? row.entry_time.slice(0, 10) : '',
    leave_status: row.leave_status,
    teach_years: row.teach_years ?? null,
    role: row.role || 'teacher',
    permissions: row.permissions || {},
    status: row.status,
  })
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    try {
      if (dialogType.value === 'add') {
        await axios.post('admin/teacher/add', {
          ...formData,
          entry_time: formData.entry_time || null,
        }, { headers: getAuthHeaders() })
        ElMessage.success('新增成功')
      } else {
        if (!editingId.value) {
          ElMessage.error('缺少教职工ID，无法更新')
          return
        }
        await axios.put(`admin/teacher/${editingId.value}`, {
          name: formData.name,
          gender: formData.gender,
          age: formData.age,
          mobile: formData.mobile,
          email: formData.email,
          dept_id: formData.dept_id,
          post_type: formData.post_type,
          subject: formData.subject,
          title: formData.title,
          entry_time: formData.entry_time || null,
          leave_status: formData.leave_status,
          teach_years: formData.teach_years,
          role: formData.role,
          permissions: formData.permissions,
          status: formData.status,
        }, { headers: getAuthHeaders() })
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
      fetchList()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  })
}

const handleDelete = (row: Teacher) => {
  ElMessageBox.confirm(`确定删除教职工 ${row.name} 吗?`, '提示', {
    type: 'warning',
  }).then(async () => {
    try {
      await axios.delete(`admin/teacher/${row.id}`, { headers: getAuthHeaders() })
      ElMessage.success('删除成功')
      fetchList()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '删除失败')
    }
  })
}

const handleResetPassword = (row: Teacher) => {
  ElMessageBox.prompt(`为教职工 ${row.name} 设置新密码`, '重置密码', {
    inputType: 'password',
    inputPlaceholder: '默认 123456',
    inputValue: '123456',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  }).then(async ({ value }) => {
    try {
      await axios.put(`admin/teacher/${row.id}/password`, { password: value || '123456' }, { headers: getAuthHeaders() })
      ElMessage.success('密码已更新')
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '重置失败')
    }
  }).catch(() => {})
}

const genderName = (val: number) => val === 1 ? '男' : val === 2 ? '女' : '未知'
const statusName = (val: number) => val === 1 ? '启用' : '停用'
const leaveName = (val: number) => val === 1 ? '在职' : val === 2 ? '离职' : '其他'

onMounted(() => {
  fetchList()
})
</script>

<template>
  <div class="page-wrap">
    <el-card class="mb-3">
      <div class="filter-bar">
        <el-input v-model="searchForm.keyword" placeholder="工号/姓名关键词" style="width: 220px" clearable @keyup.enter="fetchList">
          <template #append>
            <el-button :icon="Search" @click="fetchList" />
          </template>
        </el-input>
        <el-input v-model="searchForm.dept_id" placeholder="部门ID" style="width: 140px" clearable @keyup.enter="fetchList" />
        <el-select v-model="searchForm.post_type" placeholder="岗位" style="width: 120px" clearable @change="fetchList">
          <el-option label="专任" :value="1" />
          <el-option label="兼任" :value="2" />
          <el-option label="外聘" :value="3" />
        </el-select>
        <el-select v-model="searchForm.status" placeholder="状态" style="width: 120px" clearable @change="fetchList">
          <el-option label="启用" :value="1" />
          <el-option label="停用" :value="2" />
        </el-select>
        <el-button type="primary" :icon="Plus" color="#FAAD14" style="color: white" @click="openAdd">新增教职工</el-button>
      </div>
    </el-card>

    <el-card>
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="teacher_no" label="工号" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="gender" label="性别" width="80">
          <template #default="{ row }">{{ genderName(row.gender) }}</template>
        </el-table-column>
        <el-table-column prop="mobile" label="手机号" width="140" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="dept_id" label="部门ID" width="100" />
        <el-table-column prop="post_type" label="岗位" width="90" />
        <el-table-column prop="title" label="职称" width="90" />
        <el-table-column prop="subject" label="学科" width="120" />
        <el-table-column prop="entry_time" label="入职时间" width="140" />
        <el-table-column prop="leave_status" label="任职状态" width="100">
          <template #default="{ row }">{{ leaveName(row.leave_status) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ statusName(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="300">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" :icon="RefreshLeft" @click="handleResetPassword(row)">重置密码</el-button>
            <el-button link type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增教职工' : '编辑教职工'" width="620px">
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="120px">
        <el-form-item label="工号" prop="teacher_no">
            <el-input v-model="formData.teacher_no" :disabled="dialogType === 'edit'" placeholder="不填则自动生成 100001 起" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-select v-model="formData.gender" placeholder="请选择">
            <el-option label="男" :value="1" />
            <el-option label="女" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="formData.mobile" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="formData.email" />
        </el-form-item>
        <el-form-item label="部门ID" prop="dept_id">
          <el-input v-model.number="formData.dept_id" />
        </el-form-item>
        <el-form-item label="岗位" prop="post_type">
          <el-select v-model="formData.post_type" placeholder="请选择">
            <el-option label="专任" :value="1" />
            <el-option label="兼任" :value="2" />
            <el-option label="外聘" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="职称">
          <el-input-number v-model="formData.title" :min="0" :max="10" controls-position="right" />
        </el-form-item>
        <el-form-item label="学科/方向">
          <el-input v-model="formData.subject" />
        </el-form-item>
        <el-form-item label="入职日期">
          <el-date-picker v-model="formData.entry_time" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="任职状态">
          <el-select v-model="formData.leave_status">
            <el-option label="在职" :value="1" />
            <el-option label="离职" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="教龄(年)">
          <el-input-number v-model="formData.teach_years" :min="0" :max="60" controls-position="right" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="formData.status" :active-value="1" :inactive-value="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.mb-3 {
  margin-bottom: 12px;
}
</style>
