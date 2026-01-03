<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, Search, RefreshLeft } from '@element-plus/icons-vue'
import { fetchMajors, fetchClasses, type MajorItem, type ClassItem } from '@/api/academic'

interface Student {
  id: number
  student_no: string
  name: string
  gender: number
  age?: number
  mobile?: string
  parent_mobile?: string
  grade_id: number
  class_id: number
  major?: string
  enrollment_time?: string
  student_status: number
  role?: string
  permissions?: Record<string, any>
  status: number
  create_time: string
  update_time: string
}

interface StudentForm {
  student_no: string
  name: string
  gender: number | null
  age?: number | null
  mobile?: string
  parent_mobile: string
  grade_id: number | null
  class_id: number | null
  major?: string
  enrollment_time?: string
  student_status: number
  role?: string
  permissions?: Record<string, any>
  status: number
}

const loading = ref(false)
const tableData = ref<Student[]>([])
const editingId = ref<number | null>(null)
const majors = ref<MajorItem[]>([])
const classes = ref<ClassItem[]>([])
const selectedMajorId = ref<number | null>(null)

const searchForm = reactive({
  keyword: '',
  grade_id: '' as string | number,
  class_id: '' as string | number,
  status: '' as string | number,
  student_status: '' as string | number,
})

const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const formRef = ref()
const formData = reactive<StudentForm>({
  student_no: '',
  name: '',
  gender: 1,
  age: null,
  mobile: '',
  parent_mobile: '',
  grade_id: null,
  class_id: null,
  major: '',
  enrollment_time: '',
  student_status: 1,
  role: 'student',
  permissions: {},
  status: 1,
})

const rules = {
  student_no: [],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  parent_mobile: [{ required: true, message: '请输入家长手机号', trigger: 'blur' }],
  grade_id: [{ required: true, message: '请输入年级ID', trigger: 'blur' }],
  class_id: [{ required: true, message: '请输入班级ID', trigger: 'blur' }],
}

const loadMajors = async () => {
  try {
    majors.value = await fetchMajors()
    if (!selectedMajorId.value && majors.value.length) {
      selectedMajorId.value = majors.value[0].id
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取专业失败')
    majors.value = []
  }
}

const loadClasses = async (majorId: number | null) => {
  if (!majorId) {
    classes.value = []
    formData.class_id = null
    return
  }
  try {
    classes.value = await fetchClasses(majorId)
    const hit = classes.value.find((c) => c.id === formData.class_id)
    if (!hit) {
      formData.class_id = classes.value.length ? classes.value[0].id : null
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取班级失败')
    classes.value = []
    formData.class_id = null
  }
}

watch(selectedMajorId, (val) => {
  const m = majors.value.find((item) => item.id === val)
  formData.major = m?.name || ''
  loadClasses(val ?? null)
})

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await axios.get('admin/student/list', {
      params: {
        keyword: searchForm.keyword || undefined,
        grade_id: searchForm.grade_id || undefined,
        class_id: searchForm.class_id || undefined,
        status: searchForm.status || undefined,
        student_status: searchForm.student_status || undefined,
      },
      headers: getAuthHeaders(),
    })
    tableData.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取学生列表失败')
    tableData.value = []
  } finally {
    loading.value = false
  }
}

const openAdd = async () => {
  dialogType.value = 'add'
  editingId.value = null
  Object.assign(formData, {
    student_no: '',
    name: '',
    gender: 1,
    age: null,
    mobile: '',
    parent_mobile: '',
    grade_id: null,
    class_id: null,
    major: '',
    enrollment_time: '',
    student_status: 1,
    role: 'student',
    permissions: {},
    status: 1,
  })
  if (!majors.value.length) {
    await loadMajors()
  }
  if (majors.value.length) {
    selectedMajorId.value = majors.value[0].id
  }
  dialogVisible.value = true
}

const openEdit = async (row: Student) => {
  dialogType.value = 'edit'
  editingId.value = row.id
  Object.assign(formData, {
    student_no: row.student_no,
    name: row.name,
    gender: row.gender,
    age: row.age ?? null,
    mobile: row.mobile || '',
    parent_mobile: row.parent_mobile || '',
    grade_id: row.grade_id,
    class_id: row.class_id,
    major: row.major || '',
    enrollment_time: row.enrollment_time ? row.enrollment_time.slice(0, 10) : '',
    student_status: row.student_status,
    role: row.role || 'student',
    permissions: row.permissions || {},
    status: row.status,
  })
  // try to align major select by name
  if (!majors.value.length) {
    await loadMajors()
  }
  const matchedMajor = majors.value.find((m) => m.name === row.major)
  selectedMajorId.value = matchedMajor ? matchedMajor.id : majors.value[0]?.id || null
  await loadClasses(selectedMajorId.value)
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    try {
      if (dialogType.value === 'add') {
        await axios.post('admin/student/add', {
          ...formData,
          enrollment_time: formData.enrollment_time || null,
        }, { headers: getAuthHeaders() })
        ElMessage.success('新增成功')
      } else {
        if (!editingId.value) {
          ElMessage.error('缺少学生ID，无法更新')
          return
        }
        await axios.put(`admin/student/${editingId.value}`, {
          name: formData.name,
          gender: formData.gender,
          age: formData.age,
          mobile: formData.mobile,
          parent_mobile: formData.parent_mobile,
          grade_id: formData.grade_id,
          class_id: formData.class_id,
          major: formData.major,
          enrollment_time: formData.enrollment_time || null,
          student_status: formData.student_status,
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

const handleDelete = (row: Student) => {
  ElMessageBox.confirm(`确定删除学生 ${row.name} 吗?`, '提示', {
    type: 'warning',
  }).then(async () => {
    try {
      await axios.delete(`admin/student/${row.id}`, { headers: getAuthHeaders() })
      ElMessage.success('删除成功')
      fetchList()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '删除失败')
    }
  })
}

const handleResetPassword = (row: Student) => {
  ElMessageBox.prompt(`为学生 ${row.name} 设置新密码`, '重置密码', {
    inputType: 'password',
    inputPlaceholder: '默认 123456',
    inputValue: '123456',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  }).then(async ({ value }) => {
    try {
      await axios.put(`admin/student/${row.id}/password`, { password: value || '123456' }, { headers: getAuthHeaders() })
      ElMessage.success('密码已更新')
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '重置失败')
    }
  }).catch(() => {})
}

const genderName = (val: number) => val === 1 ? '男' : val === 2 ? '女' : '未知'
const statusName = (val: number) => val === 1 ? '启用' : '停用'
const studentStatusName = (val: number) => {
  if (val === 1) return '在读'
  if (val === 2) return '休学'
  if (val === 3) return '保留'
  if (val === 4) return '毕业'
  if (val === 5) return '退学'
  return '未知'
}

onMounted(() => {
  fetchList()
  loadMajors().then(() => loadClasses(selectedMajorId.value))
})
</script>

<template>
  <div class="page-wrap">
    <el-card class="mb-3">
      <div class="filter-bar">
        <el-input v-model="searchForm.keyword" placeholder="学号/姓名关键词" style="width: 220px" clearable @keyup.enter="fetchList">
          <template #append>
            <el-button :icon="Search" @click="fetchList" />
          </template>
        </el-input>
        <el-input v-model="searchForm.grade_id" placeholder="年级ID" style="width: 120px" clearable @keyup.enter="fetchList" />
        <el-input v-model="searchForm.class_id" placeholder="班级ID" style="width: 120px" clearable @keyup.enter="fetchList" />
        <el-select v-model="searchForm.student_status" placeholder="学籍状态" style="width: 140px" clearable @change="fetchList">
          <el-option label="在读" :value="1" />
          <el-option label="休学" :value="2" />
          <el-option label="保留" :value="3" />
          <el-option label="毕业" :value="4" />
          <el-option label="退学" :value="5" />
        </el-select>
        <el-select v-model="searchForm.status" placeholder="启用状态" style="width: 120px" clearable @change="fetchList">
          <el-option label="启用" :value="1" />
          <el-option label="停用" :value="2" />
        </el-select>
        <el-button type="primary" :icon="Plus" color="#409EFF" @click="openAdd">新增学生</el-button>
      </div>
    </el-card>

    <el-card>
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="gender" label="性别" width="80">
          <template #default="{ row }">{{ genderName(row.gender) }}</template>
        </el-table-column>
        <el-table-column prop="mobile" label="手机号" width="140" />
        <el-table-column prop="parent_mobile" label="家长电话" width="140" />
        <el-table-column prop="grade_id" label="年级ID" width="100" />
        <el-table-column prop="class_id" label="班级ID" width="100" />
        <el-table-column prop="major" label="专业" width="150" />
        <el-table-column prop="enrollment_time" label="入学时间" width="140" />
        <el-table-column prop="student_status" label="学籍" width="100">
          <template #default="{ row }">{{ studentStatusName(row.student_status) }}</template>
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

    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增学生' : '编辑学生'" width="620px">
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="120px">
        <el-form-item label="学号" prop="student_no">
          <el-input v-model="formData.student_no" :disabled="dialogType === 'edit'" placeholder="不填则自动生成，从 20230001 起" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-select v-model="formData.gender">
            <el-option label="男" :value="1" />
            <el-option label="女" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="formData.mobile" />
        </el-form-item>
        <el-form-item label="家长手机号" prop="parent_mobile">
          <el-input v-model="formData.parent_mobile" />
        </el-form-item>
        <el-form-item label="年级ID" prop="grade_id">
          <el-input v-model.number="formData.grade_id" />
        </el-form-item>
        <el-form-item label="专业">
          <el-select v-model="selectedMajorId" placeholder="选择专业">
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级" prop="class_id">
          <el-select v-model="formData.class_id" placeholder="选择班级">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="入学日期">
          <el-date-picker v-model="formData.enrollment_time" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="学籍状态">
          <el-select v-model="formData.student_status">
            <el-option label="在读" :value="1" />
            <el-option label="休学" :value="2" />
            <el-option label="保留" :value="3" />
            <el-option label="毕业" :value="4" />
            <el-option label="退学" :value="5" />
          </el-select>
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

:deep(.el-table) {
  background: transparent !important;
  color: #fff !important;
}

:deep(.el-table__body td) {
  background: transparent !important;
  color: #fff !important;
}

:deep(.el-table__row) {
  background: transparent !important;
}

:deep(.el-table__body tr:hover > td),
:deep(.el-table__body tr.el-table__row--striped:hover > td) {
  background: rgba(0, 242, 254, 0.08) !important;
  color: #fff !important;
}

:deep(.el-table th.el-table__cell) {
  background: rgba(255, 255, 255, 0.05) !important;
  color: #00f2fe !important;
}
</style>
