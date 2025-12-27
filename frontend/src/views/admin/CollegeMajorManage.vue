<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, RefreshRight } from '@element-plus/icons-vue'
import {
  fetchColleges,
  addCollege,
  updateCollege,
  deleteCollege,
  fetchMajors,
  addMajor,
  updateMajor,
  deleteMajor,
  fetchAcademicClasses,
  updateAcademicClass,
  deleteAcademicClass,
  bindClassTeacher,
  fetchAcademicStudents,
  updateAcademicStudent,
  deleteAcademicStudent,
  type AcademicClassItem,
  type AcademicStudentItem,
  type CollegeItem,
  type MajorItem,
} from '@/api/academic'
import axios from 'axios'

const colleges = ref<CollegeItem[]>([])
const majors = ref<MajorItem[]>([])
const classes = ref<AcademicClassItem[]>([])
const students = ref<AcademicStudentItem[]>([])
const loading = reactive({ colleges: false, majors: false })
const selectedCollegeId = ref<number | null>(null)

const classLoading = ref(false)
const studentLoading = ref(false)
const selectedMajorId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)

const teacherOptions = ref<{ teacher_no: string; name: string }[]>([])

const classDialog = reactive({ visible: false })
const classForm = reactive<{ id: number; major_id: number | null; name: string; code: string; status: number }>({
  id: 0,
  major_id: null,
  name: '',
  code: '',
  status: 1,
})
const classFormRef = ref()

const bindDialog = reactive({ visible: false })
const bindForm = reactive<{ class_id: number; teacher_id: string }>({ class_id: 0, teacher_id: '' })

const studentDialog = reactive({ visible: false })
const studentDetailDialog = reactive({ visible: false })
const studentForm = reactive<{ id: number; class_id: number | null; student_code: string; name: string; gender: number | null; mobile: string; status: number }>({
  id: 0,
  class_id: null,
  student_code: '',
  name: '',
  gender: 1,
  mobile: '',
  status: 1,
})
const studentFormRef = ref()
const studentDetail = ref<AcademicStudentItem | null>(null)

const collegeDialog = reactive({ visible: false, isEdit: false })
const collegeForm = reactive({ id: 0, name: '', code: '', status: 1 })
const collegeRules = {
  name: [{ required: true, message: '请输入学院名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入学院编码', trigger: 'blur' }],
}
const collegeFormRef = ref()

const batchDialog = reactive({ visible: false })
const batchMajors = ref<{ name: string; code: string; status: number }[]>([])

const loadColleges = async () => {
  loading.colleges = true
  try {
    const data = await fetchColleges()
    colleges.value = data
    if (!selectedCollegeId.value && data.length) {
      selectedCollegeId.value = data[0].id
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取学院失败')
  } finally {
    loading.colleges = false
  }
}

const loadMajors = async () => {
  loading.majors = true
  try {
    if (!selectedCollegeId.value) {
      majors.value = []
      selectedMajorId.value = null
      return
    }
    majors.value = await fetchMajors(selectedCollegeId.value)
    if (!selectedMajorId.value && majors.value.length) {
      selectedMajorId.value = majors.value[0].id
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取专业失败')
  } finally {
    loading.majors = false
  }
}

const loadClasses = async () => {
  classLoading.value = true
  try {
    if (!selectedMajorId.value) {
      classes.value = []
      selectedClassId.value = null
      return
    }
    classes.value = await fetchAcademicClasses({ major_id: selectedMajorId.value })
    if (!selectedClassId.value && classes.value.length) {
      selectedClassId.value = classes.value[0].id
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取班级失败')
    classes.value = []
  } finally {
    classLoading.value = false
  }
}

const loadStudents = async () => {
  studentLoading.value = true
  try {
    if (!selectedClassId.value) {
      students.value = []
      return
    }
    students.value = await fetchAcademicStudents({ class_id: selectedClassId.value })
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取学生失败')
    students.value = []
  } finally {
    studentLoading.value = false
  }
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const loadTeachers = async () => {
  try {
    const res = await axios.get('admin/teacher/list', { headers: getAuthHeaders() })
    // teacher list is array
    teacherOptions.value = (res.data || []).map((t: any) => ({ teacher_no: t.teacher_no, name: t.name }))
  } catch {
    teacherOptions.value = []
  }
}

const openAddCollege = () => {
  collegeDialog.visible = true
  collegeDialog.isEdit = false
  Object.assign(collegeForm, { id: 0, name: '', code: '', status: 1 })
}

const openEditCollege = (row: CollegeItem) => {
  collegeDialog.visible = true
  collegeDialog.isEdit = true
  Object.assign(collegeForm, { id: row.id, name: row.name, code: row.code, status: row.status })
}

const submitCollege = async () => {
  if (!collegeFormRef.value) return
  await collegeFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    try {
      if (collegeDialog.isEdit) {
        await updateCollege(collegeForm.id, { name: collegeForm.name, code: collegeForm.code, status: collegeForm.status })
        ElMessage.success('学院已更新')
      } else {
        await addCollege({ name: collegeForm.name, code: collegeForm.code, status: collegeForm.status })
        ElMessage.success('学院已新增')
      }
      collegeDialog.visible = false
      await loadColleges()
      await loadMajors()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  })
}

const toggleCollegeStatus = async (row: CollegeItem) => {
  try {
    await updateCollege(row.id, { status: row.status === 1 ? 0 : 1 })
    row.status = row.status === 1 ? 0 : 1
    ElMessage.success(row.status === 1 ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '状态更新失败')
  }
}

const confirmDeleteCollege = async (row: CollegeItem) => {
  try {
    await ElMessageBox.confirm(`确定删除学院「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteCollege(row.id)
    ElMessage.success('学院已删除')

    if (selectedCollegeId.value === row.id) {
      selectedCollegeId.value = null
    }
    await loadColleges()
    await loadMajors()
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

const openBatchMajor = () => {
  batchDialog.visible = true
  batchMajors.value = [
    { name: '', code: '', status: 1 },
  ]
}

const addBatchRow = () => {
  batchMajors.value.push({ name: '', code: '', status: 1 })
}

const removeBatchRow = (idx: number) => {
  batchMajors.value.splice(idx, 1)
}

const submitMajors = async () => {
  if (!selectedCollegeId.value) {
    ElMessage.error('请先选择学院')
    return
  }
  const payloads = batchMajors.value.filter((m) => m.name && m.code)
  if (!payloads.length) {
    ElMessage.error('请填写至少一个专业名称和编码')
    return
  }
  try {
    for (const p of payloads) {
      await addMajor({ ...p, college_id: selectedCollegeId.value })
    }
    ElMessage.success('专业已新增')
    batchDialog.visible = false
    await loadMajors()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '新增专业失败')
  }
}

const toggleMajorStatus = async (row: MajorItem) => {
  try {
    await updateMajor(row.id, { status: row.status === 1 ? 0 : 1 })
    row.status = row.status === 1 ? 0 : 1
    ElMessage.success(row.status === 1 ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '状态更新失败')
  }
}

const onCollegeChange = async () => {
  selectedMajorId.value = null
  selectedClassId.value = null
  await loadMajors()
  await loadClasses()
  await loadStudents()
}

const onMajorChange = async () => {
  selectedClassId.value = null
  await loadClasses()
  await loadStudents()
}

const onClassChange = async () => {
  await loadStudents()
}

const onClassRowClick = async (row: AcademicClassItem) => {
  selectedClassId.value = row.id
  await loadStudents()
}

const openEditClass = (row: AcademicClassItem) => {
  classDialog.visible = true
  Object.assign(classForm, {
    id: row.id,
    major_id: row.major_id,
    name: row.name,
    code: row.code || row.name,
    status: row.status ?? 1,
  })
}

const submitClass = async () => {
  if (!classFormRef.value) return
  await classFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    try {
      await updateAcademicClass(classForm.id, {
        major_id: classForm.major_id || undefined,
        name: classForm.name,
        code: classForm.code,
        status: classForm.status,
      })
      ElMessage.success('班级已更新')
      classDialog.visible = false
      await loadClasses()
      await loadStudents()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '更新失败')
    }
  })
}

const toggleClassStatus = async (row: AcademicClassItem) => {
  try {
    await updateAcademicClass(row.id, { status: row.status === 1 ? 0 : 1 })
    row.status = row.status === 1 ? 0 : 1
    ElMessage.success(row.status === 1 ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '状态更新失败')
  }
}

const confirmDeleteClass = async (row: AcademicClassItem) => {
  try {
    await ElMessageBox.confirm(`确定删除班级「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteAcademicClass(row.id)
    ElMessage.success('班级已删除')
    if (selectedClassId.value === row.id) {
      selectedClassId.value = null
    }
    await loadClasses()
    await loadStudents()
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

const openBindTeacher = (row: AcademicClassItem) => {
  bindDialog.visible = true
  bindForm.class_id = row.id
  bindForm.teacher_id = (row.teacher_id as string) || ''
}

const submitBindTeacher = async () => {
  try {
    if (!bindForm.teacher_id) {
      ElMessage.error('请选择教师')
      return
    }
    await bindClassTeacher(bindForm.class_id, bindForm.teacher_id)
    ElMessage.success('已绑定教师')
    bindDialog.visible = false
    await loadClasses()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '绑定失败')
  }
}

const openEditStudent = (row: AcademicStudentItem) => {
  studentDialog.visible = true
  Object.assign(studentForm, {
    id: row.id,
    class_id: row.class_id,
    student_code: row.student_code,
    name: row.name,
    gender: row.gender,
    mobile: row.mobile || '',
    status: row.status ?? 1,
  })
}

const submitStudent = async () => {
  if (!studentFormRef.value) return
  await studentFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    try {
      await updateAcademicStudent(studentForm.id, {
        class_id: studentForm.class_id || undefined,
        student_code: studentForm.student_code,
        name: studentForm.name,
        gender: studentForm.gender,
        mobile: studentForm.mobile,
        status: studentForm.status,
      })
      ElMessage.success('学生已更新')
      studentDialog.visible = false
      await loadStudents()
      await loadClasses()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '更新失败')
    }
  })
}

const confirmRemoveStudent = async (row: AcademicStudentItem) => {
  try {
    await ElMessageBox.confirm(`确定移除学生「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteAcademicStudent(row.id)
    ElMessage.success('已移除')
    await loadStudents()
    await loadClasses()
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.detail || '移除失败')
  }
}

const openStudentDetail = (row: AcademicStudentItem) => {
  studentDetail.value = row
  studentDetailDialog.visible = true
}

const genderName = (val: number | null) => (val === 1 ? '男' : val === 2 ? '女' : '未知')

const confirmDeleteMajor = async (row: MajorItem) => {
  try {
    await ElMessageBox.confirm(`确定删除专业「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteMajor(row.id)
    ElMessage.success('专业已删除')
    await loadMajors()
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(async () => {
  await loadColleges()
  await loadMajors()
  await loadTeachers()
  await loadClasses()
  await loadStudents()
})
</script>

<template>
  <div class="page-wrap">
    <el-row :gutter="12">
      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <div>学院列表</div>
            <div class="actions">
              <el-button type="primary" :icon="Plus" @click="openAddCollege">新增学院</el-button>
            </div>
          </div>
          <div class="table-area">
            <el-table :data="colleges" v-loading="loading.colleges" style="width: 100%" size="small" height="100%">
              <el-table-column prop="name" label="学院名称" min-width="180" />
              <el-table-column prop="code" label="编码" width="120" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '已启动' : '已停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" :icon="Edit" @click="openEditCollege(row)">编辑</el-button>
                  <el-button link type="warning" :icon="RefreshRight" @click="toggleCollegeStatus(row)">
                    {{ row.status === 1 ? '停用' : '启用' }}
                  </el-button>
                  <el-button link type="danger" @click="confirmDeleteCollege(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <div>
              <span>专业列表</span>
              <el-select v-model="selectedCollegeId" placeholder="选择学院" clearable style="margin-left: 12px; width: 220px" @change="onCollegeChange">
                <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </div>
            <div class="actions">
              <el-button type="primary" :icon="Plus" @click="openBatchMajor">批量新增专业</el-button>
            </div>
          </div>
          <div class="table-area">
            <el-table :data="majors" v-loading="loading.majors" style="width: 100%" size="small" height="100%">
              <el-table-column prop="name" label="专业名称" min-width="180" />
              <el-table-column prop="code" label="编码" width="120" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-switch v-model="row.status" :active-value="1" :inactive-value="0" @change="() => toggleMajorStatus(row)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button link type="warning" :icon="RefreshRight" @click="toggleMajorStatus(row)">
                    {{ row.status === 1 ? '停用' : '启用' }}
                  </el-button>
                  <el-button link type="danger" @click="confirmDeleteMajor(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="12">
      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <div>
              <span>班级</span>
              <el-select v-model="selectedMajorId" placeholder="选择专业" clearable style="margin-left: 12px; width: 220px" @change="onMajorChange">
                <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
              </el-select>
            </div>
          </div>
          <div class="table-area">
            <el-table :data="classes" v-loading="classLoading" style="width: 100%" size="small" height="100%" @row-click="onClassRowClick">
              <el-table-column prop="name" label="班级名称" min-width="140" />
              <el-table-column prop="major_name" label="所属专业" min-width="140" />
              <el-table-column prop="code" label="班级编码" width="120" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '已启用' : '已停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="260" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" :icon="Edit" @click.stop="openEditClass(row)">编辑</el-button>
                  <el-button link type="warning" :icon="RefreshRight" @click.stop="toggleClassStatus(row)">
                    {{ row.status === 1 ? '停用' : '启用' }}
                  </el-button>
                  <el-button link type="primary" @click.stop="openBindTeacher(row)">绑定教师</el-button>
                  <el-button link type="danger" @click.stop="confirmDeleteClass(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <div>
              <span>班级学生</span>
              <el-select v-model="selectedClassId" placeholder="选择班级" clearable style="margin-left: 12px; width: 220px" @change="onClassChange">
                <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </div>
          </div>
          <div class="table-area">
            <el-table :data="students" v-loading="studentLoading" style="width: 100%" size="small" height="100%">
              <el-table-column prop="name" label="学生姓名" min-width="120" />
              <el-table-column prop="student_code" label="学号" width="110" />
              <el-table-column prop="class_name" label="所属班级" min-width="120" />
              <el-table-column label="性别" width="70">
                <template #default="{ row }">{{ genderName(row.gender) }}</template>
              </el-table-column>
              <el-table-column prop="mobile" label="联系方式" min-width="120" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '已启用' : '已停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" :icon="Edit" @click="openEditStudent(row)">编辑</el-button>
                  <el-button link type="warning" @click="openStudentDetail(row)">详情</el-button>
                  <el-button link type="danger" @click="confirmRemoveStudent(row)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="collegeDialog.visible" :title="collegeDialog.isEdit ? '编辑学院' : '新增学院'" width="520px">
      <el-form :model="collegeForm" :rules="collegeRules" ref="collegeFormRef" label-width="100px">
        <el-form-item label="学院名称" prop="name">
          <el-input v-model="collegeForm.name" />
        </el-form-item>
        <el-form-item label="学院编码" prop="code">
          <el-input v-model="collegeForm.code" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="collegeForm.status">
            <el-radio :value="1">已启动</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="collegeDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitCollege">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialog.visible" title="批量新增专业" width="720px">
      <div class="batch-tip">所属学院：
        <strong>{{ colleges.find(c => c.id === selectedCollegeId)?.name || '未选择' }}</strong>
      </div>
      <el-table :data="batchMajors" size="small" style="width: 100%">
        <el-table-column label="#" width="50">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="专业名称" min-width="200">
          <template #default="{ row }">
            <el-input v-model="row.name" placeholder="请输入专业名称" />
          </template>
        </el-table-column>
        <el-table-column label="编码" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.code" placeholder="请输入编码" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeBatchRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="batch-actions">
        <el-button type="primary" :icon="Plus" plain @click="addBatchRow">新增一行</el-button>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="batchDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitMajors">提交</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="classDialog.visible" title="编辑班级" width="520px">
      <el-form :model="classForm" ref="classFormRef" label-width="100px">
        <el-form-item label="所属专业" required>
          <el-select v-model="classForm.major_id" placeholder="选择专业" style="width: 100%">
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级名称" required>
          <el-input v-model="classForm.name" />
        </el-form-item>
        <el-form-item label="班级编码" required>
          <el-input v-model="classForm.code" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="classForm.status">
            <el-radio :value="1">已启用</el-radio>
            <el-radio :value="0">已停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="classDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitClass">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="bindDialog.visible" title="绑定教师" width="520px">
      <el-form :model="bindForm" label-width="100px">
        <el-form-item label="任课教师" required>
          <el-select v-model="bindForm.teacher_id" placeholder="选择教师" style="width: 100%" filterable>
            <el-option v-for="t in teacherOptions" :key="t.teacher_no" :label="`${t.name}（${t.teacher_no}）`" :value="t.teacher_no" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="bindDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitBindTeacher">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="studentDialog.visible" title="编辑学生" width="520px">
      <el-form :model="studentForm" ref="studentFormRef" label-width="100px">
        <el-form-item label="所属班级" required>
          <el-select v-model="studentForm.class_id" placeholder="选择班级" style="width: 100%">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生姓名" required>
          <el-input v-model="studentForm.name" />
        </el-form-item>
        <el-form-item label="学号" required>
          <el-input v-model="studentForm.student_code" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="studentForm.gender">
            <el-radio :value="1">男</el-radio>
            <el-radio :value="2">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="studentForm.mobile" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="studentForm.status">
            <el-radio :value="1">已启用</el-radio>
            <el-radio :value="0">已停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="studentDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitStudent">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="studentDetailDialog.visible" title="学生详情" width="520px">
      <el-descriptions v-if="studentDetail" :column="1" border>
        <el-descriptions-item label="学生姓名">{{ studentDetail.name }}</el-descriptions-item>
        <el-descriptions-item label="学号">{{ studentDetail.student_code }}</el-descriptions-item>
        <el-descriptions-item label="所属班级">{{ studentDetail.class_name }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ genderName(studentDetail.gender) }}</el-descriptions-item>
        <el-descriptions-item label="联系方式">{{ studentDetail.mobile }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ studentDetail.status === 1 ? '已启用' : '已停用' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="studentDetailDialog.visible = false">关闭</el-button>
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
.equal-card {
  height: 360px;
  display: flex;
  flex-direction: column;
}
.equal-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-weight: 600;
}
.table-area {
  flex: 1;
  min-height: 0;
}
.actions {
  display: flex;
  gap: 8px;
}
.batch-actions {
  margin-top: 12px;
}
.batch-tip {
  margin-bottom: 8px;
  color: #666;
}
</style>
